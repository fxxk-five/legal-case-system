# 法律案件管理系统

面向单律所试点、具备多租户扩展能力的法律案件管理系统。

## 技术规划

- 后端：FastAPI + SQLAlchemy + Alembic + PostgreSQL
- Web 端：Vue 3 + Vite + Element Plus
- 小程序端：uni-app
- 基础设施：Docker + Redis + Nginx

## 仓库结构

- `backend/`：FastAPI 后端服务
- `web-frontend/`：Vue 3 Web 前端
- `mini-program/`：uni-app 微信小程序
- `docs/`：规划、环境搭建、部署、接口等文档
- `scripts/`：本地辅助脚本

## 第 1 天已完成内容

- 创建项目基础目录
- 初始化 Git 仓库
- 添加 `.gitignore`
- 添加 `.editorconfig`
- 添加环境检查脚本
- 添加初始化文档

## 第 2 天当前进度

- 已创建 FastAPI 后端骨架
- 已创建 Python 虚拟环境
- 已安装后端依赖
- 已完成配置文件与应用入口
- 已准备 `.env.example` 和 `requirements.txt`

## 第 3 到第 5 天当前进度

- 已接入 SQLAlchemy 与会话管理
- 已建立 `Tenant`、`User`、`Case`、`File` 核心模型
- 已初始化 Alembic 并补写首个迁移
- 已添加数据库初始化脚本
- 已实现注册、登录、当前用户接口

## 第 10 到第 19 天当前进度

- 已实现律师邀请注册与审批接口
- 已实现案件文件上传、列表、下载接口
- 已初始化 Web 前端项目
- 已完成登录页、概览页、案件列表页

## 第 2 天前的本地准备

请先安装并确认以下工具可用：

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis
- Docker
- Git
- VS Code

## 快速开始

Windows 环境下可先运行本地环境检查脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1
```

然后完成以下操作：

1. 在 GitHub 或 Gitee 创建远程仓库
2. 在本地添加远程仓库
3. 推送当前分支

## 相关文档

- `docs/day-01-checklist.md`
- `docs/project-setup.md`
- `docs/day-02-checklist.md`
- `docs/day-03-checklist.md`
- `docs/day-04-checklist.md`
- `docs/day-05-checklist.md`
- `docs/day-13-checklist.md`
- `docs/day-14-checklist.md`
- `docs/day-15-checklist.md`
- `docs/day-16-checklist.md`
- `docs/day-18-checklist.md`
- `docs/day-19-checklist.md`
