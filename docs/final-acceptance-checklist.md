# 最终中文验收清单

本文档用于你在“本地可演示版”阶段做最终验收。  
建议你按 `Web -> 小程序 -> Docker` 的顺序逐项打勾，不要跳着验。

## 一、Web 端验收

### 1. 登录与首页

- [ ] 能打开 `http://localhost` 或 `http://localhost:8080`
- [ ] 能使用管理员账号 `13800000000 / admin123456` 登录
- [ ] 登录后顶部显示的是中文角色，不再出现 `tenant_admin`、`lawyer`、`client`
- [ ] 登录后能看到概览、案件列表、管理面板、律师管理、机构设置
- [ ] 右上角通知按钮可以展开，通知内容能正常显示

### 2. 案件与文件

- [ ] 案件列表页能看到演示案件
- [ ] 案件列表页状态显示为中文，不再出现 `new / processing / done`
- [ ] 能打开案件详情页
- [ ] 案件详情页能显示案件时间线
- [ ] 案件详情页能上传文件
- [ ] 案件详情页能预览文件
- [ ] 案件详情页能下载文件
- [ ] 能生成当事人邀请路径
- [ ] 点击复制后有明确中文提示

### 3. 管理功能

- [ ] 管理面板能显示律师数、案件数、待审批律师数
- [ ] 律师管理页角色显示为中文
- [ ] 律师管理页能生成邀请链接
- [ ] 邀请弹窗说明是中文，普通用户能看懂
- [ ] 机构设置页能正常打开
- [ ] 机构类型和机构状态显示为中文

## 二、小程序端验收

### 1. 运行前准备

- [ ] 已在 `mini-program/manifest.json` 中填入自己的小程序 `appid`
- [ ] 已用 HBuilderX 打开 `mini-program`
- [ ] 已成功运行到微信开发者工具
- [ ] 小程序首页、登录页、案件页不白屏

### 2. 登录与进入案件

- [ ] 登录页所有提示都是中文
- [ ] 登录页不再出现 `openid` 这类技术术语
- [ ] 模拟微信登录后能进入绑定流程
- [ ] 绑定手机号时，手机号、密码、姓名、租户编码都有中文限制提示
- [ ] 当事人通过邀请入口进入后，能看到对应案件

### 3. 律师端小程序

- [ ] 律师首页能看到案件列表
- [ ] 律师首页案件状态显示为中文
- [ ] 律师案件详情页能看到时间线
- [ ] 律师案件详情页能看到文件列表
- [ ] 律师案件详情页能生成邀请路径
- [ ] 邀请路径区域说明是中文，普通用户能看懂
- [ ] 律师案件详情页能预览文件
- [ ] 律师案件详情页能下载文件

### 4. 当事人端小程序

- [ ] 当事人案件详情页能看到案件时间线
- [ ] 当事人案件详情页状态显示为中文
- [ ] 当事人案件详情页能上传材料
- [ ] 当事人案件详情页能预览材料
- [ ] 当事人案件详情页能下载材料
- [ ] 上传失败、下载失败、预览失败时有明确中文提示

## 三、Docker 验收

### 1. 服务状态

- [ ] 执行 `docker compose ps` 后，`backend`、`postgres`、`redis`、`web-frontend`、`nginx` 都是运行状态
- [ ] 后端服务监听 `8000`
- [ ] 前端服务监听 `8080`
- [ ] Nginx 统一入口监听 `80`
- [ ] PostgreSQL 和 Redis 正常运行

### 2. 数据初始化

- [ ] 已执行 `docker compose exec backend python init_db.py`
- [ ] 已执行 `docker compose exec backend python -m app.scripts.generate_demo_data`
- [ ] 初始化后能看到默认管理员账号和演示案件

### 3. 联通验证

- [ ] `http://localhost` 能打开
- [ ] `http://localhost:8000/docs` 能打开
- [ ] 已执行 `powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1`
- [ ] 冒烟脚本执行后无关键报错

## 四、联动最终验收

这一段最重要，必须整条链路都通过，才算真正可演示。

- [ ] Web 端登录管理员账号
- [ ] Web 端进入案件详情并生成当事人邀请路径
- [ ] 小程序端通过邀请路径进入对应案件
- [ ] 当事人在小程序上传一份材料
- [ ] 回到 Web 刷新后能看到同一份材料
- [ ] Web 与小程序看到的是同一案件、同一文件、同一时间线数据

## 五、你自己必须完成的事

- [ ] 在 [backend/.env](/D:/code/law/legal-case-system/backend/.env) 中确认数据库密码、密钥是你自己的配置
- [ ] 在 [mini-program/manifest.json](/D:/code/law/legal-case-system/mini-program/manifest.json) 中填写你自己的小程序 `appid`
- [ ] 在微信开发者工具里手动验证页面跳转、文件预览、文件下载
- [ ] 在浏览器中允许文件预览弹窗
- [ ] 如果 Docker Desktop 重启后服务没起来，重新执行 `docker compose up -d`
- [ ] 如果要清空数据重来，执行 `docker compose down -v`

## 六、推荐验收命令

### 1. 初始化数据库

```powershell
cd D:\code\law\legal-case-system
docker compose exec backend python init_db.py
```

### 2. 初始化演示数据

```powershell
docker compose exec backend python -m app.scripts.generate_demo_data
```

### 3. Docker 冒烟验证

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\docker-smoke-test.ps1
```

### 4. 多租户主链路验证

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\multi-tenant-smoke-test.ps1
```
