# 腾讯云单机生产运行手册（CVM + Docker Compose + COS）

> 更新日期：2026-03-23
> 适用范围：首阶段单台 `CVM` 部署 `nginx`、`web-frontend`、`backend`、`ai-worker`、`report-service`、`postgres`、`redis`
> 当前目标：先完成单机云端稳定运行与 `COS` 真源，再执行灰度和正式切流

## 1. 目标架构

首阶段生产入口定义为：

`DNS / SSL -> Nginx(CVM) -> web / backend`

容器职责如下：

- `nginx`：公网入口，处理 `80/443`、TLS 证书和反向代理。
- `web-frontend`：Web 静态站点。
- `backend`：FastAPI API，处理认证、业务接口、上传授权、下载授权。
- `ai-worker`：异步 AI 任务常驻消费。
- `report-service`：Node + Puppeteer 报告渲染服务。
- `postgres`：首阶段单机数据库。
- `redis`：首阶段单机缓存。
- `COS`：证据文件、报告文件、导出文件的生产真源。

## 2. 公网入口与域名规划

推荐首阶段域名规划如下：

- Web 主域名：`https://law.example.com`
- API 域名：`https://api.example.com`
- 文件域名：`https://files.example.com`，仅在启用 `COS` 自定义域名或 `CDN` 后使用
- 灰度 API 域名：`https://gray-api.example.com`

推荐入口策略：

- `law.example.com` 走 `nginx -> web-frontend`
- `api.example.com` 走 `nginx -> backend`
- 报告和附件下载优先返回签名 `COS` URL
- 如需前端生产直传 `COS`，优先为 `COS/CDN` 准备 `files.example.com`，再打开 `STORAGE_DIRECT_UPLOAD_ENABLED=true`

小程序合法域名建议：

- `request`：`https://api.example.com`
- `uploadFile`：
  - 首阶段保守模式：`https://api.example.com`
  - 直传 `COS` 模式：`https://files.example.com`
- `downloadFile`：
  - 首阶段签名下载跳转模式：`https://api.example.com`
  - `COS/CDN` 自定义下载域名模式：`https://files.example.com`
- `socket`：如未启用 WebSocket 可暂不配置

当前建议：

- 在正式域名、证书、`COS CORS`、小程序合法域名全部确认前，生产保持 `STORAGE_DIRECT_UPLOAD_ENABLED=false`
- 等 `files.example.com` 或等效自定义下载/上传域名就绪后，再切换生产直传

## 3. 主机与安全组前提

`CVM` 要求：

- 系统建议 `Ubuntu 22.04 LTS`
- 规格至少 `2C4G`
- 稳妥建议 `4C8G`
- 系统盘建议 `SSD 100GB+`

安全组要求：

- 仅公网开放 `22`、`80`、`443`
- `22` 仅对运维白名单 IP 开放
- 不对公网开放 `5432`、`6379`、`8000`、`3001`

主机初始化最低要求：

- 创建运维账号，避免长期直接使用 `root`
- 配置 SSH 密钥登录
- 为账号密码登录、短信验证码登录、微信扫码登录分别配置风控与审计策略
- 校准时区与时间同步
- 安装 `curl`、`wget`、`git`、`unzip`

## 4. 目录与配置布局

建议目录：

```text
/srv/legal-case-system
/srv/legal-case-system/deploy
/srv/legal-case-system/deploy/backend.env.tencent.prod
/srv/legal-case-system/deploy/nginx/nginx.prod.conf
/srv/legal-case-system/deploy/nginx/certs/fullchain.pem
/srv/legal-case-system/deploy/nginx/certs/privkey.pem
```

建议将生产环境变量文件放在：

- `deploy/backend.env.tencent.prod`
- `deploy/backend.env.tencent.prod.example`
- `deploy/backend.env.tencent.staging.example`

不要把生产真源继续定义为开发机上的 `.env`。首阶段可以使用 `CVM` 上的受控环境文件，后续再演进到 `Secrets Manager / KMS`。

当前仓库的 `docker-compose.prod.yml` 已调整为优先加载：

- `deploy/backend.env.tencent.prod.example`
- `deploy/backend.env.tencent.prod`（存在时覆盖模板值）

环境与密钥治理口径统一参考：

- [腾讯云环境与密钥治理映射](/D:/code/law/legal-case-system/docs/tencent-cloud-env-governance.md)
- [腾讯云二阶段演进与切流方案](/D:/code/law/legal-case-system/docs/tencent-cloud-wave2-evolution.md)

## 5. 关键环境变量

生产必须确认以下字段：

```env
STORAGE_BACKEND=cos
STORAGE_DELETE_POLICY=archive
STORAGE_PENDING_PREFIX=_pending
STORAGE_RETENTION_PREFIX=_retained
STORAGE_DIRECT_UPLOAD_ENABLED=false

TENCENT_COS_SECRET_ID=...
TENCENT_COS_SECRET_KEY=...
TENCENT_COS_BUCKET=...
TENCENT_COS_REGION=...
STORAGE_PUBLIC_BASE_URL=

POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
POSTGRES_DB=legal_case
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...

QUEUE_DRIVER=db
AI_DB_QUEUE_EAGER=false
AI_DB_QUEUE_POLL_SECONDS=2
AI_DB_QUEUE_MAX_RETRIES=3
AI_DB_QUEUE_RETRY_BACKOFF_SECONDS=30
AI_DB_QUEUE_STALE_TASK_SECONDS=900
AI_DB_QUEUE_HEARTBEAT_FILE=/tmp/legal-ai-worker-heartbeat.json
AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS=90
AI_DB_QUEUE_WORKER_ID=legal-ai-worker

REPORT_SERVICE_BASE_URL=http://report-service:3001
REPORT_SERVICE_TIMEOUT_SECONDS=30
```

说明：

- `STORAGE_DELETE_POLICY=archive`：删除文件记录时，对象优先归档，不直接物理删除。
- `STORAGE_PENDING_PREFIX=_pending`：前端直传 `COS` 时先写入暂存区。
- `STORAGE_RETENTION_PREFIX=_retained`：归档对象保留区。
- `STORAGE_DIRECT_UPLOAD_ENABLED=false`：正式生产默认先关闭，等公网入口、`CORS`、合法域名全部完成后再打开。
- `AI_DB_QUEUE_STALE_TASK_SECONDS`：超过该时长未更新心跳的 `processing` 任务，会被恢复为重试或死信。
- `AI_DB_QUEUE_HEARTBEAT_FILE`：`ai-worker` 心跳文件路径，供容器健康检查使用。
- `AI_DB_QUEUE_HEALTHCHECK_MAX_AGE_SECONDS`：健康检查允许的最大心跳年龄。
- `AI_DB_QUEUE_WORKER_ID`：写入任务声明记录与心跳文件的逻辑 worker 标识。
- `TENCENT_QUEUE_*`：为后续 `TDMQ/CMQ` 预留；在真实腾讯云队列 consumer 未接入前，不要把生产 `QUEUE_DRIVER` 从 `db` 切走。

## 6. COS Bucket 基线配置

`COS Bucket` 生产建议：

- 权限：私有读写
- CORS：仅允许 `law.example.com`、`api.example.com`、`files.example.com` 和必要的小程序上传/下载域名
- 生命周期：
  - `_pending/`：清理未完成上传对象，例如 `1` 到 `3` 天
  - `_retained/`：按保留策略归档，例如 `30` 到 `180` 天
  - `reports/`：按业务要求保留历史版本，可后续做归档或转低频
- `CAM`：为应用配置最小权限账号，不使用主账号密钥直连应用

对象规则约定：

- 文件正式路径：`tenant_{tenant_id}/case_{case_id}/files/...`
- 文件暂存路径：`tenant_{tenant_id}/case_{case_id}/_pending/...`
- 报告路径：`tenant_{tenant_id}/case_{case_id}/reports/...`
- 归档路径：`_retained/deleted_at=<timestamp>/tenant_{tenant_id}/case_{case_id}/...`

## 7. 代码下发与部署前校验

拉代码：

```bash
sudo mkdir -p /srv
cd /srv
git clone <repo-url> legal-case-system
cd /srv/legal-case-system
```

准备配置：

```bash
cp deploy/backend.env.tencent.prod.example deploy/backend.env.tencent.prod
mkdir -p deploy/nginx/certs
```

部署前先校验：

```bash
docker compose -f docker-compose.prod.yml config
```

如果这里不能通过，不要继续启动容器。

前端发布前必须先执行：
```bash
cd web-frontend
npm run check
cd ..
```

`npm run check` 需要同时通过 `lint`、`test`、`build`，否则不进入云端部署。

## 8. 首次部署顺序

### 8.1 安装 Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

### 8.2 启动基础依赖

```bash
docker compose -f docker-compose.prod.yml up -d postgres redis report-service
```

### 8.3 启动 API 与 Web

```bash
docker compose -f docker-compose.prod.yml up -d backend web-frontend
```

### 8.4 执行数据库迁移

```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 8.5 启动入口与 Worker

```bash
docker compose -f docker-compose.prod.yml up -d ai-worker nginx
```

## 9. 上线后健康检查

检查容器状态：

```bash
docker compose -f docker-compose.prod.yml ps
```

检查健康接口：

```bash
curl -k https://law.example.com/
curl -k https://api.example.com/api/v1/health/live
curl -k https://api.example.com/api/v1/health/ready
```

检查日志：

```bash
docker compose -f docker-compose.prod.yml logs backend --tail=200
docker compose -f docker-compose.prod.yml logs ai-worker --tail=200
docker compose -f docker-compose.prod.yml logs report-service --tail=200
docker compose -f docker-compose.prod.yml logs nginx --tail=200
```

关键判断标准：

- `backend` 返回 `health/live` 和 `health/ready` 正常
- `ai-worker` 为 `Up` 且持续轮询
- `report-service` 为 `Up` 且 `/health` 正常
- `nginx` 不报证书、回源、上游连接错误

## 10. 重启与恢复检查

验证容器重启策略：

```bash
docker inspect legal-backend --format '{{.HostConfig.RestartPolicy.Name}}'
docker inspect legal-ai-worker --format '{{.HostConfig.RestartPolicy.Name}}'
docker inspect legal-report-service --format '{{.HostConfig.RestartPolicy.Name}}'
```

应返回：

- `unless-stopped`

验证 Docker 重启后的服务恢复：

```bash
sudo systemctl restart docker
sleep 10
docker compose -f docker-compose.prod.yml ps
```

验证主机重启后的恢复：

```bash
sudo reboot
```

主机恢复后检查：

```bash
docker compose -f docker-compose.prod.yml ps
curl -k https://api.example.com/api/v1/health/ready
```

### 10.1 快照与数据库备份基线

- `CVM`：至少保留每日自动快照，保留周期不低于 `7` 天。
- `PostgreSQL`：至少执行每日一次 `pg_dump`，建议落盘到 `/srv/legal-case-system/backups/postgres/`，保留 `7~14` 天。
- 备份文件命名建议：`legal_case_YYYYMMDD_HHMM.sql.gz`
- 正式发布前，必须确认最近一次快照与最近一次数据库备份均可用。

建议备份命令：

```bash
mkdir -p /srv/legal-case-system/backups/postgres
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres legal_case | gzip > \
  /srv/legal-case-system/backups/postgres/legal_case_$(date +%Y%m%d_%H%M).sql.gz
```

恢复演练命令：

```bash
gunzip -c /srv/legal-case-system/backups/postgres/<backup-file>.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d legal_case
```

### 10.2 日志轮转基线

- 容器标准输出日志先由 Docker 管理，再由主机侧执行文件型日志轮转。
- 推荐模板已提供：`deploy/logrotate/legal-case-system.conf`
- 主机若落地 `/srv/legal-case-system/logs/*.log`，必须启用每日轮转、压缩、保留 `14` 份。

应用模板：

```bash
sudo cp deploy/logrotate/legal-case-system.conf /etc/logrotate.d/legal-case-system
sudo logrotate -f /etc/logrotate.d/legal-case-system
```

### 10.3 `ai-worker` 监督与死任务回收

- `ai-worker` 现在带有容器级 `healthcheck`，依赖 `AI_DB_QUEUE_HEARTBEAT_FILE`。
- 任务进入 `processing` 后会写入 `worker_id`、`claimed_at`、`heartbeat_at`。
- 若超过 `AI_DB_QUEUE_STALE_TASK_SECONDS` 未更新心跳，worker 会在下一轮消费前自动执行恢复：
  - 未超过重试上限：转为 `retrying`，按退避时间重新排队。
  - 已超过重试上限：转为 `dead`。

建议检查命令：

```bash
docker inspect legal-ai-worker --format '{{json .State.Health}}'
docker compose -f docker-compose.prod.yml logs ai-worker --tail=200
```

## 11. 回滚入口

首阶段推荐的回滚入口：

- 代码回滚：回到前一稳定 `git commit` 或发布标签
- 配置回滚：恢复上一版 `deploy/backend.env.tencent.prod`
- 容器回滚：重新 `docker compose up -d --build`
- 数据回滚：依赖 `CVM` 快照与数据库备份，不建议直接手工修改线上数据

推荐回滚流程：

```bash
cd /srv/legal-case-system
git checkout <previous-release-tag-or-commit>
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
```

说明：

- 数据库迁移必须遵循可回滚策略；如果当前版本包含不可逆迁移，回滚前必须先核对备份与快照。
- 文件真源在 `COS`，不要把“把文件复制回主机”当成回滚手段。

## 12. 正式云域名验收清单（5.4）

本仓库已经具备验收脚本与命令，但截至 2026-03-23，尚未在真实云域名执行。只有满足以下前置条件，才进入正式验收：

- 域名解析已指向 `CVM`
- `SSL` 证书已部署
- `COS Bucket`、`CAM`、`CORS` 已完成
- 小程序合法域名已配置
- 测试账号、案件数据、JWT 或手机号密码已准备

### 12.1 报告可见性验收

```bash
python scripts/smoke_report_visibility.py \
  --base-url https://api.example.com/api/v1 \
  --case-id <CASE_ID> \
  --lawyer-token <LAWYER_JWT> \
  --client-token <CLIENT_JWT>
```

通过标准：

- 输出 `[DONE] smoke_report_visibility passed`

### 12.2 主链路 Smoke

```bash
python scripts/smoke_core_chain.py \
  --base-url https://api.example.com/api/v1 \
  --lawyer-token <LAWYER_JWT> \
  --client-token <CLIENT_JWT> \
  --case-id <CASE_ID> \
  --file-path upload-smoke.txt
```

通过标准：

- 上传成功
- 解析成功
- 分析成功
- 报告下载成功
- 输出 `[DONE] smoke_core_chain passed`

### 12.3 QA02 全链路 E2E

```bash
python scripts/qa02_full_e2e.py \
  --base-url https://api.example.com/api/v1 \
  --lawyer-phone <LAWYER_PHONE> \
  --lawyer-password <LAWYER_PASSWORD> \
  --tenant-code <TENANT_CODE> \
  --file-path upload-smoke.txt
```

通过标准：

- 输出 `[DONE] qa02_full_e2e passed`

### 12.4 人工补充检查

- Web 首页、登录页、案件列表页、案件详情页可访问
- 律师端创建案件可用
- 小程序端登录、上传、查看进度、下载报告可用
- 上传对象进入 `COS`
- 删除文件后对象按 `archive` 策略进入 `_retained/`
- 报告对象落在 `reports/` 前缀
- 开发机离线不影响云端服务

## 13. 日常运维命令

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail=200
docker compose -f docker-compose.prod.yml logs ai-worker --tail=200
docker compose -f docker-compose.prod.yml logs report-service --tail=200
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart ai-worker
docker compose -f docker-compose.prod.yml restart report-service
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 14. 当前结论

截至 2026-03-23，本项目已具备进入正式部署前一阶段的条件：

- 后端 `COS` 存储、签名下载、报告对象存储、删除归档逻辑已落地
- 单机 `CVM` 运行手册已产出
- 首阶段公网入口 `DNS / SSL -> Nginx(CVM)` 已定义
- 正式云域名验收清单已准备

2026-03-24 本机补充验证结果：

- 已实际执行 `docker compose -f docker-compose.prod.yml up -d`
- 已执行 `docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head`
- 已确认 `postgres / redis / report-service / backend / web-frontend / nginx / ai-worker` 全部进入 `healthy`
- 已确认 `https://127.0.0.1/api/v1/health/ready` 返回 `database=ok`、`storage=ok`
- 为完成本机 smoke，临时生成了 `deploy/backend.env.tencent.prod` 与自签证书；正式上云前必须替换为真实生产值

尚未完成的事项：

- `COS Bucket`、`CORS`、域名、证书、小程序合法域名的云侧落地
- 已购 `CVM` 的实际初始化与部署执行
- 真实公网域名上的正式验收与灰度切流
