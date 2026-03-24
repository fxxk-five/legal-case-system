# 生产部署指南（统一版）

## 1. 适用范围
- 适用于当前仓库的单机 Docker Compose 部署。
- 目标系统：`backend` + `web-frontend` + `postgres` + `redis` + `nginx`。
- 本文以仓库现有配置为准：`docker-compose.yml` 与 `deploy/nginx/nginx.conf`。

## 2. 当前架构与真实路由
- 外部入口：`nginx`（80 端口）。
- 路由规则：
  - `/api/` -> `backend:8000`
  - `/` -> `web-frontend:80`
- 后端 OpenAPI 地址：`/api/v1/openapi.json`。
- 健康检查地址：`/api/v1/health`。

## 3. 服务器准备（MVP）
- 建议规格：
  - 演示环境：2C4G / 80G 磁盘
  - 小规模生产：4C8G / 100G 磁盘
- 安全组：仅放行 `22/80/443`（生产建议关闭直出数据库端口）。
- 系统建议：Ubuntu 22.04 LTS。

## 4. 目录规划
建议在服务器采用以下结构：

```text
/srv/legal-case-system/
├── releases/
├── shared/
│   ├── env/
│   ├── storage/
│   ├── logs/
│   └── backups/
└── current -> releases/<release-id>
```

## 5. 环境变量
- 以 `backend/.env.example` 为基线。
- 生产必须替换：
  - `SECRET_KEY`
  - `POSTGRES_PASSWORD`
  - `WECHAT_MINIAPP_APP_ID`
  - `WECHAT_MINIAPP_APP_SECRET`
- 生产建议：
  - `WECHAT_MINIAPP_MOCK_LOGIN=false`
  - `AI_MOCK_MODE=false`（如接入真实模型）

## 6. 部署步骤

### 6.1 获取代码并切换版本
```bash
git clone <repo_url> /srv/legal-case-system/releases/<release-id>
ln -sfn /srv/legal-case-system/releases/<release-id> /srv/legal-case-system/current
cd /srv/legal-case-system/current
```

### 6.2 配置环境文件
```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env，填充生产变量
```

### 6.3 启动服务
```bash
docker compose up -d --build
```

### 6.4 初始化数据库
```bash
docker compose exec backend python init_db.py
```

### 6.5 验证服务
```bash
curl http://<domain-or-ip>/api/v1/health
# 期望: {"status":"ok"}
```

## 7. HTTPS 与域名
- 生产建议在 `nginx` 层开启 `443`。
- 当前仓库 `deploy/nginx/nginx.conf` 仅包含 `80`，上线需补充：
  - `80 -> 443` 跳转
  - 证书挂载与自动续期
  - 安全头与基础缓存策略
- 小程序合法域名需配置为同一 HTTPS 域名。

## 8. 数据备份与恢复

### 8.1 每日备份（示例）
```bash
docker compose exec -T postgres pg_dump -U postgres legal_case > /srv/legal-case-system/shared/backups/legal_case_$(date +%F).sql
```

### 8.2 恢复（示例）
```bash
docker compose exec -T postgres psql -U postgres -d legal_case < /srv/legal-case-system/shared/backups/<backup-file>.sql
```

## 9. 发布与回滚

### 9.1 发布流程
1. 本地通过最小验证（后端测试 / 前端构建）。
2. 拉取新版本到 `releases/<release-id>`。
3. 切换 `current`。
4. `docker compose up -d --build`。
5. 执行 `init_db.py` 与 smoke 验证。

### 9.2 回滚流程
1. 将 `current` 回指旧版本。
2. 执行 `docker compose up -d --build`。
3. 验证 `/api/v1/health`。
4. 如有必要，恢复数据库备份。

## 10. 上线验收清单（最小集）
- [ ] 默认账号/密钥均已替换。
- [ ] 对公网仅开放 `80/443`。
- [ ] `/api/v1/health` 可访问且稳定返回 200。
- [ ] Web 登录、案件详情、律师管理关键链路可用。
- [ ] 日志可定位错误（至少保留容器日志与 request_id）。
- [ ] 备份脚本可执行，至少完成一次恢复演练。

## 11. 已知限制
- 当前 AI 任务为请求内同步执行，非队列异步。
- 当前 compose 默认暴露了 `5432/6379/8000/8080`，生产需改为内网可见或关闭直出。
- 当前 WebSocket AI 进度接口存在鉴权风险，生产应补鉴权或临时关闭。

## 12. Health Probe Strategy (2026-03-19)
- Backward compatibility endpoint: `GET /api/v1/health` (returns `{"status":"ok"}`).
- Liveness probe endpoint: `GET /api/v1/health/live` (expected `200`).
- Readiness probe endpoint: `GET /api/v1/health/ready` (expected `200` when dependencies are ready, `503` otherwise).
- Recommended probe policy:
  - Container liveness: use `/api/v1/health/live`.
  - Container readiness / load-balancer upstream check: use `/api/v1/health/ready`.
  - Keep `/api/v1/health` only for legacy monitoring compatibility.

## 13. Production Port Exposure Baseline (2026-03-19)
- New production compose file: `docker-compose.prod.yml`.
- Purpose: expose only `80/443` on host; keep backend/postgres/redis/web internal-only.
- Production startup command:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
- Production config verification:
```bash
docker compose -f docker-compose.prod.yml config
powershell -ExecutionPolicy Bypass -File scripts/check-exposed-ports.ps1
```
- Expected result from port check:
  - Exposed host ports: `80`, `443`
  - No direct host mapping for `5432`, `6379`, `8000`, `8080`
- TLS file requirement (nginx production config):
  - `deploy/nginx/certs/fullchain.pem`
  - `deploy/nginx/certs/privkey.pem`
- Nginx production config file:
  - `deploy/nginx/nginx.prod.conf`
