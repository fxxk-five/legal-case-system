# 后端说明

## 当前状态

后端已经不是初始骨架，而是当前本地演示版的主服务，已完成：

- 用户注册、登录、当前用户查询
- 律师邀请、邀请注册、审批、启用禁用
- 案件创建、列表、详情、状态更新
- 本地文件上传、文件列表、下载
- 通知查询与已读
- 统计面板接口
- 微信小程序直登、手机号授权、会话撤销、案件邀请进入

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
```

默认初始化数据：

- 租户编码：`test_lawfirm`
- 管理员手机号：`13800000000`
- 管理员密码：`admin123456`

## 小程序联调说明

当前为了优先打通本地演示流程，后端默认支持 mock 微信登录：

```env
WECHAT_MINIAPP_MOCK_LOGIN=true
```

相关接口：

- `POST /api/v1/auth/wx-mini-login`
- `POST /api/v1/auth/wx-mini-phone-login`
- `POST /api/v1/auth/wx-mini-bind-existing`
- `POST /api/v1/auth/logout`
- `GET /api/v1/cases/{id}/invite-qrcode`

邀请路径规则：

- 案件邀请：`pages/login/index?scene=client-case&token=...`
- 机构律师邀请注册：`pages/login/index?token=...`

详细步骤见：

- `docs/wechat-mini-direct-login-runbook.md`

## 下一步重点

当前剩余重点已转为：

- 继续补微信真机联调
- 继续补对象存储与上线级配置
- 继续补小程序端交互细节
