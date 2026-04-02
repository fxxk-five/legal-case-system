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

## 必填配置

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
2. 复制 `deploy/backend.env.tencent.prod.example` 为 `deploy/backend.env.tencent.prod` 并填入真实密钥。
3. 准备 `deploy/nginx/certs/fullchain.pem` 与 `deploy/nginx/certs/privkey.pem`。
4. 启动服务：

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

5. 执行数据库迁移 / 初始化：

```powershell
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
docker compose -f docker-compose.prod.yml exec backend python init_db.py
```

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
