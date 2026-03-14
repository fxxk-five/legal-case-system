# 后端说明

## 当前状态

第 2 天已完成以下基础工作：

- 创建 Python 虚拟环境：`venv/`
- 安装 FastAPI 基础依赖
- 建立后端目录结构
- 完成配置文件 `app/core/config.py`
- 完成应用入口 `app/main.py`
- 添加 CORS 配置
- 提供根路由和健康检查接口

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
├── .env.example
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

## 下一步

第 3 天将继续完成：

- SQLAlchemy 数据库连接
- 基础模型定义
- Alembic 初始化与迁移
