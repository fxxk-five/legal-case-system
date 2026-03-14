# 项目初始化说明

## 仓库目录说明

- `backend/`：FastAPI 后端服务
- `web-frontend/`：Vue 3 + Vite Web 前端
- `mini-program/`：uni-app 微信小程序
- `docs/`：规划、初始化、部署、接口等文档
- `scripts/`：本地辅助脚本

## 第 1 天目标结果

完成第 1 天后，仓库应具备以下基础能力：

- 干净可用的 Git 仓库
- 清晰稳定的顶层目录结构
- 本地文件与生成文件的忽略规则
- 基础编辑器统一规范
- 本地环境检查脚本

## 开始第 2 天前

1. 运行 `powershell -ExecutionPolicy Bypass -File .\scripts\check-env.ps1`
2. 在 GitHub 或 Gitee 创建远程仓库
3. 添加远程仓库：
   - `git remote add origin <你的仓库地址>`
4. 推送当前分支：
   - `git push -u origin main`

## 说明

- 只有在本地开发工具链确认正常后，才建议开始第 2 天的后端搭建。
- 从项目开始阶段就不要把敏感信息提交到 Git，后续统一使用 `.env` 文件管理。
