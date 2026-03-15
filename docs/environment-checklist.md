# 环境变量清单

本文档用于说明当前项目在本地演示和 Docker 部署时需要关注的环境变量。

## 后端 `backend/.env`

可直接从 [backend/.env.example](/D:/code/law/legal-case-system/backend/.env.example) 复制。

### 必填项

- `POSTGRES_SERVER`
- `POSTGRES_PORT`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `SECRET_KEY`

### 本地演示推荐值

- `POSTGRES_SERVER=localhost`
- `POSTGRES_PORT=5432`
- `WECHAT_MINIAPP_MOCK_LOGIN=true`

### 容器部署推荐值

- `POSTGRES_SERVER=postgres`
- `POSTGRES_PORT=5432`
- `WECHAT_MINIAPP_MOCK_LOGIN=true` 或真实微信配置

### 微信小程序相关

- `WECHAT_MINIAPP_APP_ID`
- `WECHAT_MINIAPP_APP_SECRET`
- `WECHAT_MINIAPP_MOCK_LOGIN`
- `WECHAT_MINIAPP_CLIENT_ENTRY_PAGE`

说明：

- 本地演示阶段可以只保留 `WECHAT_MINIAPP_MOCK_LOGIN=true`
- 真机联调时，再填写真实 `AppID/AppSecret`

## Web 前端

前端本地开发默认读取：

- `VITE_API_BASE_URL`

本地开发建议：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

容器 + Nginx 反向代理场景建议：

```env
VITE_API_BASE_URL=/api/v1
```

## 你需要做的

- 确认 `backend/.env` 中的数据库账号密码是你自己机器可用的
- 本地阶段不要把真实密钥提交到 Git
- 真机调试前再填写微信真实配置
