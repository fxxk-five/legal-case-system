# 第 1 天检查清单

## 仓库内已完成

- 已创建项目根目录：`legal-case-system`
- 已创建基础目录：
  - `backend/`
  - `web-frontend/`
  - `mini-program/`
  - `docs/`
- 已创建辅助目录：
  - `scripts/`
- 已添加 `README.md`
- 已添加 `.gitignore`
- 已添加 `.editorconfig`
- 已添加本地环境检查脚本
- 已添加项目初始化文档

## 你还需要在本机完成

- 确认以下命令可以正常执行：
  - `python --version`
  - `node --version`
  - `psql --version`
  - `redis-server --version` 或 `redis-cli --version`
  - `docker --version`
  - `git --version`
  - `code --version`
- 或直接运行：
  - `powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1`
- 安装 VS Code 插件：
  - Python
  - Vue - Official
  - Prettier
  - ESLint
- 在 GitHub 或 Gitee 创建远程仓库
- 执行：
  - `git remote add origin <你的仓库地址>`
  - `git push -u origin main`

## 说明

- 没有自动创建远程仓库，因为这一步需要你的账号权限。
- 第 1 天只做环境和仓库初始化，因此没有安装项目依赖包。
