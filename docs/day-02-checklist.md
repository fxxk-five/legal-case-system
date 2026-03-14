# 第 2 天检查清单

## 今日目标

- 创建 FastAPI 后端项目骨架
- 使用虚拟环境隔离依赖
- 安装后端基础依赖
- 通过环境变量管理配置
- 添加 CORS 中间件
- 验证服务可启动

## 已完成

- 已创建 `backend/` 目录结构
- 已创建虚拟环境 `backend/venv`
- 已安装依赖：
  - `fastapi`
  - `uvicorn`
  - `sqlalchemy`
  - `alembic`
  - `psycopg2-binary`
  - `python-jose[cryptography]`
  - `passlib[bcrypt]`
  - `python-multipart`
  - `pydantic-settings`
- 已编写配置文件：
  - `backend/app/core/config.py`
- 已编写应用入口：
  - `backend/app/main.py`
- 已提供配置模板：
  - `backend/.env.example`
- 已提供依赖清单：
  - `backend/requirements.txt`

## 本地验证步骤

1. 进入目录：

```powershell
cd D:\code\law\legal-case-system\backend
```

2. 激活虚拟环境：

```powershell
.\venv\Scripts\Activate.ps1
```

3. 启动服务：

```powershell
python -m uvicorn app.main:app --reload
```

4. 验证接口：

- 打开 `http://127.0.0.1:8000/`
- 打开 `http://127.0.0.1:8000/api/v1/health`
- 打开 `http://127.0.0.1:8000/docs`

## 说明

- `Redis` 不阻塞第 2 天任务，后续可优先通过 Docker 使用。
- 数据库连接能力将在第 3 天正式接入。
- 当前阶段先保证应用骨架稳定，再继续模型和迁移。
