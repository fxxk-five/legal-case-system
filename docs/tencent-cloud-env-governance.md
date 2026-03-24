# 腾讯云环境与密钥治理映射

> 更新日期：2026-03-23
> 适用范围：当前 `CVM + Docker Compose + COS` 首阶段，以及后续 `staging -> production` 演进

## 1. 治理原则

- `dev` 允许使用仓库内本地 `.env` 进行开发调试。
- `staging` 与 `production` 不再把 `backend/.env` 当成线上真源。
- `deploy/backend.env.tencent.staging` 与 `deploy/backend.env.tencent.prod` 只是当前阶段的受控投递载体，不是长期治理真源。
- 长期真源应收口到腾讯云侧的 `Secrets Manager / KMS / CAM` 与发布系统；`CVM` 上的环境文件只承接分发结果。

## 2. 环境映射

| 环境 | 运行位置 | 配置载体 | 密钥来源 | 允许的文件 | 禁止项 |
| --- | --- | --- | --- | --- | --- |
| `dev` | 开发机 / 本地 Docker | `backend/.env` | 开发者本地 | `backend/.env` | 把生产密钥写入仓库 |
| `staging` | 腾讯云灰度 `CVM` | `deploy/backend.env.tencent.staging` | 受控发放的灰度密钥、后续切到 `Secrets Manager` | `deploy/backend.env.tencent.staging.example` -> `deploy/backend.env.tencent.staging` | 继续使用 `backend/.env` 作为灰度真源 |
| `production` | 腾讯云正式 `CVM` | `deploy/backend.env.tencent.prod` | 正式密钥台账、后续切到 `Secrets Manager / KMS` | `deploy/backend.env.tencent.prod.example` -> `deploy/backend.env.tencent.prod` | 在线手改 `backend/.env`、把密钥写进 compose 文件 |

## 3. 配置分组与责任

| 分组 | 典型变量 | 真源责任人 | 备注 |
| --- | --- | --- | --- |
| 基础应用 | `PROJECT_NAME` `VERSION` `API_V1_STR` | 后端 | 变更频率低，可随发布版本管理 |
| 数据库 | `POSTGRES_*` | 运维 | 生产密码不得出现在仓库 |
| 认证 | `SECRET_KEY` `ALGORITHM` | 运维 + 后端 | `SECRET_KEY` 必须支持轮换 |
| 对象存储 | `STORAGE_*` `TENCENT_COS_*` | 运维 | `SecretId/SecretKey` 优先使用最小权限 `CAM` 子账号 |
| AI 调用 | `OPENAI_API_KEY` `OPENAI_BASE_URL` `AI_MODEL` | 后端 + 运维 | API Key 必须支持失效和更换 |
| 队列/Worker | `QUEUE_DRIVER` `AI_DB_QUEUE_*` `TENCENT_QUEUE_*` | 后端 + 运维 | 生产固定 `AI_DB_QUEUE_EAGER=false`，未接入真实云 consumer 前保持 `QUEUE_DRIVER=db` |
| 报告服务 | `REPORT_SERVICE_*` | 后端 | 与 `docker-compose.prod.yml` 服务名保持一致 |
| 小程序 | `WECHAT_MINIAPP_*` | 前端 + 运维 | `APP_SECRET` 不得出现在前端仓库 |

## 4. 生产投递流程

1. 以 `deploy/backend.env.tencent.prod.example` 为字段模板，不直接在模板中填写真实密钥。
2. 从密钥台账或腾讯云密钥服务中提取正式值，生成 `deploy/backend.env.tencent.prod`。
3. 将真实文件仅放在目标 `CVM` 的 `/srv/legal-case-system/deploy/` 下，并设置最小可读权限。
4. `docker-compose.prod.yml` 只读取 `deploy/backend.env.tencent.prod.example` 与可选的 `deploy/backend.env.tencent.prod`，不再依赖 `backend/.env`。
5. 密钥轮换时，先更新真源，再重新生成 `deploy/backend.env.tencent.prod`，最后执行受控重启。

## 5. 当前阶段的最小合规要求

- `deploy/backend.env.tencent.prod` 必须加入 `.gitignore`，不得提交到仓库。
- 线上不得使用主账号 `SecretKey` 直连 `COS`，至少切到最小权限 `CAM` 子账号。
- `ai-worker` 必须启用心跳文件与容器健康检查，避免“进程卡死但容器仍存活”。
- `AI_DB_QUEUE_EAGER` 在 `staging` 和 `production` 一律设为 `false`。
- 任何线上环境变更都要留下变更记录、回滚版本和执行人。

## 6. 后续演进

- `staging`：先将 `deploy/backend.env.tencent.staging` 纳入统一发布脚本。
- `production`：将 `SECRET_KEY`、`OPENAI_API_KEY`、`TENCENT_COS_SECRET_KEY` 收口到腾讯云 `Secrets Manager / KMS`。
- `multi-CVM / TKE`：环境变量改为发布系统或容器平台注入，逐步移除主机环境文件。
