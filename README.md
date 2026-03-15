# 法律案件管理系统

面向单律所试点、具备多租户扩展能力的法律案件管理系统。本仓库当前目标不是直接上线，而是先完成一套可以在本地稳定演示的闭环版本。

## 当前完成度

目前已经具备以下能力：

- 后端：FastAPI + PostgreSQL + Alembic，支持用户认证、案件管理、律师邀请审批、文件上传下载、通知、统计
- Web 端：支持管理员和律师登录、案件查看、新建案件、案件详情、文件管理、律师管理、机构设置
- 小程序端：已建立 uni-app 骨架，支持微信 mock 登录、手机号绑定、律师查看案件、当事人进入案件、当事人上传材料
- 部署资产：已提供 Dockerfile、Compose、Nginx 配置和部署文档

## 本地演示主流程

你现在可以按下面的链路做演示：

1. 管理员登录 Web 端
2. 律师创建案件
3. 律师生成当事人邀请路径
4. 当事人在小程序端进入案件并绑定手机号
5. 当事人查看案件并上传文件
6. 律师在 Web 端或小程序端查看材料、下载材料

## 仓库结构

- `backend/`：FastAPI 后端服务
- `web-frontend/`：Vue 3 Web 前端
- `mini-program/`：uni-app 微信小程序
- `docs/`：中文开发、联调、部署文档
- `scripts/`：本地辅助脚本

## 本地启动步骤

### 1. 检查环境

需要本机已安装并可用：

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Git
- VS Code
- HBuilderX
- 微信开发者工具

可先运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1
```

### 2. 初始化后端

```powershell
cd D:\code\law\legal-case-system\backend
Copy-Item .env.example .env
.\venv\Scripts\Activate.ps1
python init_db.py
python -m uvicorn app.main:app --reload
```

默认管理账号：

- 手机号：`13800000000`
- 密码：`admin123456`

默认本地小程序配置：

- `WECHAT_MINIAPP_MOCK_LOGIN=true`
- 不强制填写 `WECHAT_MINIAPP_APP_ID`
- 不强制填写 `WECHAT_MINIAPP_APP_SECRET`

### 3. 启动 Web 端

```powershell
cd D:\code\law\legal-case-system\web-frontend
npm install
npm run dev
```

默认访问地址：

- Web：`http://127.0.0.1:5173`
- API：`http://127.0.0.1:8000/api/v1`
- Swagger：`http://127.0.0.1:8000/docs`

### 4. 启动小程序端

1. 用 HBuilderX 导入 [mini-program](/D:/code/law/legal-case-system/mini-program)
2. 在 `manifest.json` 中填入你自己的微信小程序 `appid`
3. 运行到微信开发者工具
4. 在微信开发者工具中调试登录、跳转、上传和接口请求

### 5. Docker 演示方式

如果你要直接用 Docker 运行整套环境：

```powershell
cd D:\code\law\legal-case-system
docker compose up --build -d
docker compose exec backend python init_db.py
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

Docker 访问地址：

- 统一入口：`http://localhost`
- Web 直连：`http://localhost:8080`
- Swagger：`http://localhost:8000/docs`

## 你需要做的

### 工具与账号

- 安装并打开 `HBuilderX`
- 安装并登录 `微信开发者工具`
- 准备一个微信小程序测试号或正式 `AppID`
- 保证本机 PostgreSQL 可正常连接

### 本地配置

- 在 `backend/.env` 中填好你的 PostgreSQL 用户名和密码
- 本地阶段保持 `WECHAT_MINIAPP_MOCK_LOGIN=true`
- 真机联调时，再填写真实 `AppID/AppSecret` 并关闭 mock

### 调试配合

- 你负责在微信开发者工具里观察授权、跳转、网络请求和上传行为
- 你负责把 `mini-program/manifest.json` 里的 `appid` 改成你自己的
- 你负责在浏览器里测试 Web 端文件预览是否被浏览器拦截弹窗
- 如果微信端报错，把报错截图或接口响应发给我，我继续收口

### 演示数据

- 你需要在 Docker 环境中执行一次演示数据脚本：

```powershell
cd D:\code\law\legal-case-system
docker compose exec backend python -m app.scripts.generate_demo_data
```

- 执行后会自动生成：
  - 2 到 3 个演示案件
  - 演示律师账号
  - 演示当事人账号
  - 演示通知
  - 演示文件记录

## 关键文档

- [项目初始化说明](/D:/code/law/legal-case-system/docs/project-setup.md)
- [第 1 天清单](/D:/code/law/legal-case-system/docs/day-01-checklist.md)
- [第 2 天清单](/D:/code/law/legal-case-system/docs/day-02-checklist.md)
- [第 22 天清单](/D:/code/law/legal-case-system/docs/day-22-checklist.md)
- [第 23 天清单](/D:/code/law/legal-case-system/docs/day-23-checklist.md)
- [第 24 天清单](/D:/code/law/legal-case-system/docs/day-24-checklist.md)
- [第 25 天清单](/D:/code/law/legal-case-system/docs/day-25-checklist.md)
- [第 26 天清单](/D:/code/law/legal-case-system/docs/day-26-checklist.md)
- [第 27 天清单](/D:/code/law/legal-case-system/docs/day-27-checklist.md)
- [第 28 天清单](/D:/code/law/legal-case-system/docs/day-28-checklist.md)
- [本地联调指南](/D:/code/law/legal-case-system/docs/local-demo-guide.md)
- [环境变量清单](/D:/code/law/legal-case-system/docs/environment-checklist.md)
- [部署指南](/D:/code/law/legal-case-system/docs/deployment-guide.md)
- [腾讯云上线操作手册](/D:/code/law/legal-case-system/docs/tencent-cloud-deployment-guide.md)
- [最终验收清单](/D:/code/law/legal-case-system/docs/final-acceptance-checklist.md)
