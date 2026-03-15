# 本地联调指南

本文档用于把当前项目以“本地可演示”的方式完整跑起来。

## 一、后端启动

```powershell
cd D:\code\law\legal-case-system\backend
Copy-Item .env.example .env
.\venv\Scripts\Activate.ps1
python init_db.py
python -m uvicorn app.main:app --reload
```

说明：

- `init_db.py` 会负责建库、迁移和默认种子数据
- 如果数据库密码不一致，先修改 `backend/.env`
- 本地默认管理员账号为 `13800000000 / admin123456`

## 二、Web 启动

```powershell
cd D:\code\law\legal-case-system\web-frontend
npm install
npm run dev
```

建议先完成以下验证：

1. 登录后台
2. 查看概览页
3. 新建案件
4. 打开案件详情
5. 上传文件并预览、下载文件
6. 管理员进入律师管理和机构设置

## 三、小程序启动

### 方式

推荐组合：

- VS Code：写代码
- HBuilderX：导入 uni-app 项目
- 微信开发者工具：调试、预览、上传体验版

### 步骤

1. 用 HBuilderX 打开 `mini-program`
2. 修改 `mini-program/manifest.json` 中的 `appid`
3. 运行到微信开发者工具
4. 确保请求地址指向本地后端：

文件位置：

- [common/config.js](/D:/code/law/legal-case-system/mini-program/common/config.js)

默认地址：

```text
http://127.0.0.1:8000/api/v1
```

## 四、模拟微信登录说明

当前后端支持“模拟微信登录”，目的是先把本地业务流程跑通。

后端配置：

```env
WECHAT_MINIAPP_MOCK_LOGIN=true
```

作用：

- 小程序调用 `uni.login()` 拿到 `code`
- 后端不会真实请求微信接口
- 后端会根据 `code` 生成一个模拟的微信身份标识
- 这样可以先完成绑定、进入案件、上传文件等流程

## 五、本地演示推荐顺序

### 律师侧

1. 用默认管理员登录 Web
2. 新建一个案件
3. 进入案件详情页
4. 点击获取当事人邀请路径

### 当事人侧

1. 在小程序中进入登录页或邀请页
2. 走微信模拟登录
3. 输入手机号和姓名完成绑定
4. 查看案件详情
5. 上传一份文件

### 回到律师侧

1. 刷新 Web 案件详情页
2. 查看当事人刚上传的文件
3. 验证预览和下载是否成功

## 六、Docker 演示方式

如果你使用 Docker 跑整套服务，建议按下面顺序验证：

```powershell
cd D:\code\law\legal-case-system
docker compose up -d
docker compose exec backend python init_db.py
docker compose exec backend python -m app.scripts.generate_demo_data
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

访问地址：

- 统一入口：`http://localhost`
- Web：`http://localhost:8080`
- 后端接口文档：`http://localhost:8000/docs`

## 七、你必须自己做的事

- 填写自己的 PostgreSQL 账号密码
- 在微信开发者工具中登录微信账号
- 填写小程序 `appid`
- 在 Docker 环境中手动执行演示数据脚本
- 观察小程序端报错、跳转、上传行为
- 在浏览器中验证文件预览是否被拦截
- 如果 Docker Desktop 重启后容器没起来，重新执行 `docker compose up -d`

## 八、常见问题

### 1. 小程序请求不到本地后端

检查：

- 后端是否启动
- 本机端口是否为 `8000`
- `common/config.js` 是否指向正确地址

### 2. 小程序能登录但无法上传

检查：

- 当前用户是否已绑定到案件
- 当前案件是否属于该当事人
- 后端是否有 `403` 或 `400` 返回

### 3. Web 登录后被退出

通常表示：

- token 已失效
- 后端未启动
- `/users/me` 请求失败

### 4. 微信真机联调失败

当前阶段默认不以真机上线能力为目标，先用模拟微信登录跑通本地演示。真机能力后续再接真实 `AppID/AppSecret`。
