# 本地开发与联调说明

## 环境要求

- Python `3.11+`
- Node.js `20+`
- Docker / Docker Compose
- PostgreSQL `17`（可直接用仓库 compose）
- 微信小程序开发：`HBuilderX` + 微信开发者工具

## 推荐启动方式

### 方式 A：数据库与依赖走容器，前后端本地跑

1. 启动基础依赖：

```powershell
docker compose up -d postgres redis report-service
```

2. 准备后端环境：

```powershell
Copy-Item backend\.env.example backend\.env
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python init_db.py
python -m uvicorn app.main:app --reload
```

3. 启动 Web：

```powershell
cd web-frontend
npm install
npm run dev
```

### 方式 B：整套容器演示

```powershell
Copy-Item backend\.env.example backend\.env
docker compose up -d --build
```

适用于快速演示，不适合日常细粒度开发。

## 本地默认配置

- 后端配置基线：`backend/.env.example`
- Web API 地址：`web-frontend/.env.example`
- 本地默认建议：
  - `WECHAT_MINIAPP_MOCK_LOGIN=true`
  - `AI_MOCK_MODE=true`
  - `STORAGE_BACKEND=local`
  - `QUEUE_DRIVER=db`
  - `AI_DB_QUEUE_EAGER=true`

## 小程序调试

1. 启动本地后端 `http://127.0.0.1:8000/api/v1`。
2. 用 `HBuilderX` 打开 `mini-program`。
3. 运行到微信开发者工具，生成目录 `mini-program/unpackage/dist/dev/mp-weixin`。
4. 在微信开发者工具做页面预览、登录流与上传流验证。

如需打测试环境或生产环境包，小程序会优先读取 `UNI_APP_RUNTIME_ENV` / `UNI_APP_API_BASE_URL`；未显式指定时，本地运行默认落到 `local -> http://127.0.0.1:8000/api/v1`。

```powershell
$env:UNI_APP_RUNTIME_ENV="staging"
```

```powershell
$env:UNI_APP_API_BASE_URL="https://staging.your-domain.example/api/v1"
```

## 推荐验证命令

### 后端

```powershell
cd backend
pytest tests -q
```

### Web

```powershell
cd web-frontend
npm test -- --run
npm run build
```

### 小程序与登录主链路

```powershell
python scripts\mini_program_static_audit.py
python scripts\smoke_login_matrix.py
```

> `mini_program_static_audit.py` 依赖已生成的 `mini-program/unpackage/dist/dev/mp-weixin`。

## 常见联调入口

- 用户手册与角色限制：`docs/user-manual.md`
- 当前开放任务：`docs/current-project-status.md`
- 接口边界：`docs/API-CONTRACTS.md`
