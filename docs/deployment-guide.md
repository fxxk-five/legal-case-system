# 部署说明

## 目录

- `backend/`：后端服务
- `web-frontend/`：前端服务
- `deploy/nginx/nginx.conf`：统一反向代理配置
- `docker-compose.yml`：本地或服务器编排配置
- `docs/environment-checklist.md`：环境变量清单

## 启动前准备

1. 确认 Docker Desktop 已启动
2. 确认 `backend/.env` 已填写真实数据库配置
3. 如用于 Docker，可直接复制 `backend/.env.docker.example` 为 `backend/.env`
4. 如前端单独部署，请调整 `VITE_API_BASE_URL`
5. 如要接微信真机联调，请准备好真实 `AppID/AppSecret`

## 本地容器启动

```powershell
cd D:\code\law\legal-case-system
docker compose up --build -d
```

说明：

- 当前 `docker-compose.yml` 已强制让后端容器通过 `postgres` 服务名连接数据库
- 当前前端 Docker 构建会自动使用 `VITE_API_BASE_URL=/api/v1`
- 如果容器首次拉取镜像较慢，属于正常现象

## 初始化数据库

后端启动后执行：

```powershell
docker compose exec backend python init_db.py
```

## 访问地址

- 统一入口地址：`http://localhost`
- 后端直连：`http://localhost:8000`
- 前端直连：`http://localhost:8080`

## 推荐验证顺序

1. `docker compose config`
2. `docker compose up --build -d`
3. `docker compose ps`
4. `docker compose logs backend`
5. `docker compose exec backend python init_db.py`
6. 浏览器访问 `http://localhost`

## 常见排障

### 1. 后端容器无法连接 PostgreSQL

优先检查：

- `backend/.env` 是否仍写成 `POSTGRES_SERVER=localhost`
- `docker compose config` 中展开后的 `POSTGRES_SERVER` 是否为 `postgres`

### 2. Web 容器启动失败

优先检查：

- Node 镜像是否成功拉取
- `npm install` 是否完成
- 容器构建阶段是否被代理、权限或网络问题中断

### 3. Docker 提示无法读取 `C:\Users\\你的用户名\\.docker\\config.json`

这通常是本机 Docker Desktop 权限问题，不一定是项目配置错误。

建议你做：

1. 关闭 Docker Desktop
2. 重新以正常用户启动 Docker Desktop
3. 检查 `C:\Users\\你的用户名\\.docker\\config.json` 是否可读

### 4. 前端页面打开但接口 404

优先检查：

- Nginx 是否把 `/api/` 代理到后端
- 前端容器构建时是否使用了 `VITE_API_BASE_URL=/api/v1`
- 后端接口是否正常暴露在 `8000`

## 维护建议

- 每次部署后先运行冒烟测试
- 定期备份 PostgreSQL 数据卷
- 上线后再接入正式对象存储和 HTTPS
- 上线前再次替换所有默认密码和默认密钥
