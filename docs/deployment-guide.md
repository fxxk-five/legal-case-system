# 部署说明

## 目录

- `backend/`：后端服务
- `web-frontend/`：前端服务
- `deploy/nginx/nginx.conf`：统一反向代理配置
- `docker-compose.yml`：本地或服务器编排配置

## 启动前准备

1. 确认 `backend/.env` 已填写真实数据库配置
2. 如用于 Docker，可直接复制 `backend/.env.docker.example` 为 `backend/.env`
3. 如前端单独部署，请调整 `VITE_API_BASE_URL`

## 本地容器启动

```powershell
cd D:\code\law\legal-case-system
docker compose up --build -d
```

## 初始化数据库

后端启动后执行：

```powershell
docker compose exec backend python init_db.py
```

## 访问地址

- Nginx 统一入口：`http://localhost`
- 后端直连：`http://localhost:8000`
- 前端直连：`http://localhost:8080`

## 维护建议

- 每次部署后先运行冒烟测试
- 定期备份 PostgreSQL 数据卷
- 上线后再接入正式对象存储和 HTTPS
