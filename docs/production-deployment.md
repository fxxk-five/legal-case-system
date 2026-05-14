# 生产部署说明

## 适用范围

- 当前仓库的单机 Docker Compose 部署。
- 目标拓扑：`nginx + web-frontend + backend + ai-worker + report-service + postgres + redis`。
- 生产 compose：`docker-compose.prod.yml`。

## 生产文件与入口

- Compose：`docker-compose.prod.yml`
- Nginx：`deploy/nginx/nginx.prod.conf`
- 生产环境变量模板：`deploy/backend.env.tencent.prod.example`
- 可选生产环境变量文件：`deploy/backend.env.tencent.prod`
- TLS 证书目录：`deploy/nginx/certs`

生产环境变量模板已显式写入 `APP_ENV=production`，且 `docker-compose.prod.yml` 的 `backend` 与 `ai-worker` 服务均通过 `environment` 传递 `APP_ENV: production`，以触发后端生产态校验所依赖的 `SECRET_KEY`、`BACKEND_CORS_ORIGINS` 与 `AI_MOCK_MODE` 等字段。部署时请不要删改这些字段的存在感，后续任何生产拓扑补丁都应在这个基线上进行。

## 必填配置

- `APP_ENV=production`（必须与 `docker-compose.prod.yml` 一致，后端 / worker 在该模式下会强制校验下文中列出的各项）
- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `BACKEND_CORS_ORIGINS`
- `TENCENT_COS_SECRET_ID`
- `TENCENT_COS_SECRET_KEY`
- `TENCENT_COS_BUCKET`
- `TENCENT_COS_REGION`
- `OPENAI_API_KEY`
- `WECHAT_MINIAPP_APP_ID`
- `WECHAT_MINIAPP_APP_SECRET`

## 生产建议值

- `WECHAT_MINIAPP_MOCK_LOGIN=false`
- `AI_MOCK_MODE=false`
- `STORAGE_BACKEND=cos`
- `QUEUE_DRIVER=db`
- `AI_DB_QUEUE_EAGER=false`

## 部署步骤

1. 准备服务器目录并拉取代码。
2. 复制 `deploy/backend.env.tencent.prod.example` 为 `deploy/backend.env.tencent.prod`，确保 `APP_ENV=production` 仍然存在，填入 `SECRET_KEY`、`POSTGRES_PASSWORD` 和 `BACKEND_CORS_ORIGINS`（建议先用正式域名的 https 路径占位），并将 `AI_MOCK_MODE=false` 保持明确。
3. 准备 `deploy/nginx/certs/fullchain.pem` 与 `deploy/nginx/certs/privkey.pem`（真实域名与证书链的申请、续期与平台部署仍属于云资源 / 域名侧任务，状态请同步到 `docs/current-project-status.md`）。
4. 启动服务：

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

5. 执行数据库迁移 / 初始化：

```powershell
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python init_db.py
```

> 仓库层面当前只需确保 `docker-compose.prod.yml` 与 env 模板表达 `APP_ENV=production` 的生产态基线；正式域名、HTTPS、COS 以及微信合法域名的实际部署仍由云平台 / 证书域名团队跟进，状态请和 `docs/current-project-status.md` 保持同步。

## 上线后检查

```powershell
docker compose -f docker-compose.prod.yml ps
curl https://<domain>/api/v1/health
curl https://<domain>/api/v1/health/live
curl https://<domain>/api/v1/health/ready
```

预期：

- 只对外开放 `80/443`
- `backend`、`ai-worker`、`report-service`、`postgres`、`redis` 均为 healthy
- Web 首页、登录页、API 健康检查都可访问

## 业务级 smoke

- Web：密码登录、短信登录、案件列表、案件详情、律师管理
- 小程序：邀请进入、登录、材料上传、补充说明
- AI：上传后能排队、worker 能消费、报告可下载

## 回滚

1. 切回上一个 release 目录。
2. 重新执行：

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

3. 若数据库结构已前移，按备份策略恢复数据库。
4. 重跑健康检查与 smoke。

## 当前未完成的正式上线前置

- 真实域名、HTTPS 与微信合法域名联通。
- 真实 COS 上传 / 下载链路验证。
- 真机页面逐页验收。
- 云端 `Go / No-Go` 与回滚演练。

这些任务的状态统一看 `docs/current-project-status.md`，放行标准看 `docs/final-acceptance-checklist.md`。
