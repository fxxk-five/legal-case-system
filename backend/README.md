# 后端说明

## 当前状态

目前已推进到第 5 天的基础后端能力，已完成：

- 创建 Python 虚拟环境：`venv/`
- 安装 FastAPI 与数据库相关依赖
- 建立后端目录结构
- 完成配置文件 `app/core/config.py`
- 完成应用入口 `app/main.py`
- 添加 CORS 配置
- 提供根路由和健康检查接口
- 接入 SQLAlchemy 会话与基础模型
- 初始化 Alembic
- 添加默认租户和管理员初始化脚本
- 实现注册、登录、当前用户接口

## 目录结构

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── dependencies/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── main.py
│   └── __init__.py
├── venv/
├── alembic/
├── .env.example
├── alembic.ini
├── init_db.py
├── requirements.txt
└── README.md
```

## 首次使用

1. 进入后端目录：

```powershell
cd D:\code\law\legal-case-system\backend
```

2. 激活虚拟环境：

```powershell
.\venv\Scripts\Activate.ps1
```

3. 如需重新安装依赖，优先使用镜像源：

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --timeout 120 --no-cache-dir
```

4. 如需本地环境变量，复制配置模板：

```powershell
Copy-Item .env.example .env
```

5. 启动开发服务器：

```powershell
python -m uvicorn app.main:app --reload
```

## 访问地址

- 根接口：`http://127.0.0.1:8000/`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`

## 初始化数据库

先确保 `.env` 中的数据库密码与本机 PostgreSQL 一致，然后执行：

```powershell
python init_db.py
venv\Scripts\alembic upgrade head
```

默认初始化数据：

- 租户编码：`test_lawfirm`
- 管理员手机号：`13800000000`
- 管理员密码：`admin123456`

## 下一步

下一步将继续完成：

- 案件创建与列表接口
- 律师管理接口
- 租户信息接口
