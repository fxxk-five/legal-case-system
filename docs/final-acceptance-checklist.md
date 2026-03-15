# 最终验收清单

本文档用于你在本地演示阶段逐项确认系统是否达到可交付演示状态。

## 一、Web 端验收

### 登录与基础信息

- [ ] 能打开 `http://localhost` 或本地 Web 开发地址
- [ ] 能使用管理员账号 `13800000000 / admin123456` 登录
- [ ] 登录后能看到概览页、案件列表、律师管理、机构设置
- [ ] 右上角通知按钮可以展开并显示通知内容

### 案件与文件

- [ ] 能在案件列表中看到演示案件
- [ ] 能打开案件详情页
- [ ] 案件详情页能显示案件时间线
- [ ] 能上传文件
- [ ] 能下载文件
- [ ] 能点击“预览”并在浏览器中打开文件
- [ ] 能生成当事人邀请路径并复制

### 管理功能

- [ ] 管理面板能显示律师数、案件数、待审批律师数
- [ ] 律师管理页能看到演示律师
- [ ] 机构设置页能正常打开且不报错

## 二、小程序端验收

### 登录与进入案件

- [ ] 已在 `manifest.json` 中填入自己的小程序 `appid`
- [ ] 已用 HBuilderX 打开 `mini-program`
- [ ] 已在微信开发者工具中成功运行项目
- [ ] 小程序能正常进入登录页
- [ ] mock 微信登录后能完成手机号绑定
- [ ] 当事人通过邀请页进入后能看到自己的案件

### 案件与文件

- [ ] 律师端能看到案件列表
- [ ] 律师端能打开案件详情页
- [ ] 律师端能看到案件时间线
- [ ] 律师端能看到文件列表
- [ ] 律师端能预览文件
- [ ] 律师端能下载文件
- [ ] 当事人端能看到案件时间线
- [ ] 当事人端能上传文件
- [ ] 当事人端能预览文件
- [ ] 当事人端能下载文件

## 三、Docker 验收

### 服务状态

- [ ] `docker compose ps` 能看到 5 个服务都处于 `Up`
- [ ] `backend` 正常运行在 `8000`
- [ ] `web-frontend` 正常运行在 `8080`
- [ ] `nginx` 正常运行在 `80`
- [ ] `postgres` 和 `redis` 正常运行

### 数据与接口

- [ ] 已执行 `docker compose exec backend python init_db.py`
- [ ] 已执行演示数据脚本
- [ ] 已执行 Docker 冒烟脚本
- [ ] `http://localhost:8000/docs` 可以打开
- [ ] `http://localhost` 可以打开

## 四、推荐验证命令

### 初始化基础数据

```powershell
cd D:\code\law\legal-case-system
docker compose exec backend python init_db.py
```

### 初始化演示数据

```powershell
docker compose exec backend python -m app.scripts.generate_demo_data
```

### Docker 冒烟验证

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

## 五、你需要自己做的事

- [ ] 在 [backend/.env](/D:/code/law/legal-case-system/backend/.env) 中确认数据库密码是你自己的
- [ ] 在 [mini-program/manifest.json](/D:/code/law/legal-case-system/mini-program/manifest.json) 中填写自己的小程序 `appid`
- [ ] 在微信开发者工具里手动验证文件预览、文件下载、授权和页面跳转
- [ ] 在浏览器中允许 Web 文件预览弹窗
- [ ] 如果 Docker Desktop 重启后服务消失，重新执行 `docker compose up -d`
- [ ] 如果你要清空数据重来，执行 `docker compose down -v`
