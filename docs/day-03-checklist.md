# 第 3 天检查清单

## 今日目标

- 接入 SQLAlchemy 数据库层
- 定义核心模型
- 初始化 Alembic
- 准备首个迁移

## 已完成

- 已添加数据库基类：
  - `backend/app/db/base_class.py`
- 已添加数据库聚合导入：
  - `backend/app/db/base.py`
- 已添加会话管理：
  - `backend/app/db/session.py`
- 已添加核心模型：
  - `backend/app/models/tenant.py`
  - `backend/app/models/user.py`
  - `backend/app/models/case.py`
  - `backend/app/models/file.py`
- 已初始化 Alembic：
  - `backend/alembic.ini`
  - `backend/alembic/env.py`
  - `backend/alembic/versions/9969606c99a3_init.py`

## 当前状态说明

- 模型和迁移文件已经就位
- 由于本地 PostgreSQL 密码尚未同步到 `.env`，自动生成迁移未能直接连接数据库
- 为了不中断开发，当前已补写首个初始迁移文件

## 你需要完成

1. 在 `backend` 目录下创建 `.env`
2. 把真实数据库密码写入：

```env
POSTGRES_PASSWORD=你的真实密码
```

3. 如果数据库 `legal_case` 还不存在，先创建它
4. 然后执行：

```powershell
cd D:\code\law\legal-case-system\backend
.\venv\Scripts\Activate.ps1
python init_db.py
venv\Scripts\alembic upgrade head
```
