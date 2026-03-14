# 第 4 天检查清单

## 今日目标

- 验证迁移是否可执行
- 初始化默认租户和管理员
- 为后续认证与接口联调准备基础数据

## 已完成

- 已添加初始化脚本：
  - `backend/init_db.py`
- 已添加种子数据逻辑：
  - `backend/app/scripts/init_seed.py`
- 初始化后默认数据设计为：
  - 默认租户：`test_lawfirm`
  - 默认管理员手机号：`13800000000`
  - 默认管理员密码：`admin123456`

## 本地执行步骤

```powershell
cd D:\code\law\legal-case-system\backend
.\venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python init_db.py
venv\Scripts\alembic upgrade head
```

## 说明

- 如果 `python init_db.py` 失败，优先检查 `.env` 中的数据库密码
- 如果 `alembic upgrade head` 失败，也通常是数据库连接配置未对齐
