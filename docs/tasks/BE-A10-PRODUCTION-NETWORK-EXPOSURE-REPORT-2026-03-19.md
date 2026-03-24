# BE-A10 执行记录：生产端口与网络暴露基线（2026-03-19）

- 日期: 2026-03-19
- 执行人: Codex
- 基线文档: `docs/tasks/BE-A10-PRODUCTION-NETWORK-EXPOSURE-BASELINE-EXECUTION.md`

## 1. 本次落地内容

1. 新增生产专用编排文件  
- `docker-compose.prod.yml`
- 策略: 仅 `nginx` 暴露主机端口 `80/443`，其余服务仅 `expose` 到容器网络。

2. 新增生产 Nginx 配置  
- `deploy/nginx/nginx.prod.conf`
- 策略:
  - `80 -> 443` 重定向（保留 ACME challenge 路径）
  - `443` TLS 终止
  - `/api/` 反代 backend
  - `/ws/` 反代 backend（支持 WS 升级）
  - `/` 反代 web-frontend

3. 新增端口暴露审计脚本  
- `scripts/check-exposed-ports.ps1`
- 策略: 解析 `docker compose config --format json`，校验主机暴露端口是否仅在允许列表（默认 `80,443`）。

4. 新增证书目录占位  
- `deploy/nginx/certs/.gitkeep`
- 运行要求:
  - `deploy/nginx/certs/fullchain.pem`
  - `deploy/nginx/certs/privkey.pem`

## 2. 验证记录

1. 编排验证  
- 命令: `docker compose -f docker-compose.prod.yml config`
- 结果: 通过

2. 端口审计验证  
- 命令: `powershell -ExecutionPolicy Bypass -File scripts/check-exposed-ports.ps1`
- 结果: 通过  
- 输出: `nginx: 80:80`, `nginx: 443:443`

## 3. 与目标对照

- [x] backend/postgres/redis/web 前台端口不直出公网  
- [x] 生产入口统一收敛到 nginx  
- [x] 提供可执行端口审计命令  
- [x] 文档同步（`docs/production-deployment.md`）

## 4. 风险与默认策略

- 风险: 未放置证书文件会导致 `nginx` 启动失败。  
  默认策略: 上线前由运维下发证书到 `deploy/nginx/certs/`。

- 风险: 当前为单机 compose 基线，未覆盖跨可用区容灾。  
  默认策略: 先满足最小暴露面，再按容量规划进入中期架构演进。
