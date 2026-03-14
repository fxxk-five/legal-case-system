# Web 前端说明

## 当前状态

Web 端已完成基础骨架：

- Vue 3 + Vite 初始化
- Element Plus 接入
- Vue Router 接入
- Pinia 接入
- Axios 请求封装
- 登录页
- 基础后台布局
- 案件列表页
- 概览页

## 当前页面

- `/login`：登录页
- `/`：概览页
- `/cases`：案件列表页

## 默认联调地址

前端默认请求：

```text
http://127.0.0.1:8000/api/v1
```

如果后端地址变化，可修改：

- `src/lib/http.js`
- 或复制 `.env.example` 为 `.env` 后修改 `VITE_API_BASE_URL`

## 默认测试账号

```text
13800000000 / admin123456
```

## 启动方式

```powershell
cd D:\code\law\legal-case-system\web-frontend
npm install
npm run dev
```

如果需要自定义接口地址：

```powershell
Copy-Item .env.example .env
```

## 说明

- 当前环境下 `vite build` 可能因为 Windows 终端对子进程的权限限制报 `spawn EPERM`
- 这不代表页面代码本身一定有问题，更像是当前终端环境限制
- 如果你在本机终端中运行正常，可继续以本机结果为准
