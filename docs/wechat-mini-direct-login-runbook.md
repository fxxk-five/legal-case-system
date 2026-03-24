# 微信小程序直登配置与调试手册

> 更新时间：2026-03-23
> 适用范围：当前仓库小程序端 `wx.login + getPhoneNumber + refresh session revoke`

## 1. 当前登录架构

- Web 端：支持三种登录方式
  - 账号密码登录：`POST /api/v1/auth/login`
  - 短信验证码登录：`POST /api/v1/auth/sms/send` + `POST /api/v1/auth/sms-login`
  - 微信扫码登录：`POST /api/v1/auth/web-wechat-login`
  - 二维码状态查询：`GET /api/v1/auth/web-wechat-login/{ticket}`
  - 小程序确认扫码：`POST /api/v1/auth/web-wechat-login/{ticket}/confirm`
  - 浏览器兑换登录态：`POST /api/v1/auth/web-wechat-login/{ticket}/exchange`
- 小程序端：默认使用微信直登
  - `POST /api/v1/auth/wx-mini-login`
  - `POST /api/v1/auth/wx-mini-phone-login`
  - `POST /api/v1/auth/wx-mini-bind-existing`
  - `POST /api/v1/auth/logout`

小程序登录页统一入口：

- 普通登录：`pages/login/index`
- 案件邀请登录：`pages/login/index?scene=client-case&token=...`
- 机构律师邀请注册：`pages/login/index?scene=lawyer-invite&token=...`
- Web 扫码确认：`pages/login/index?scene=web-login&ticket=...`

规则：

- 独户律师：微信登录成功后直接进入 `pages/lawyer/cases`
- 机构律师 / 机构管理员：微信登录成功后进入 `pages/lawyer/home`
- 机构律师：通过邀请进入时可自动创建待审批账号，审批通过后可直接微信登录
- 当事人：带案件邀请 token 时可自动创建或绑定 `client` 账号
- Web 工作台：支持账号密码、短信验证码、微信扫码三种登录；当事人登录后仍会进入 Web 受限说明页

---

## 2. 本地开发模式

### 2.1 纯本地 mock 模式

适用于你还没有正式微信配置，先把前后端链路跑通。

`backend/.env`：

```env
WECHAT_MINIAPP_MOCK_LOGIN=true
WECHAT_MINIAPP_APP_ID=
WECHAT_MINIAPP_APP_SECRET=
WECHAT_MINIAPP_CLIENT_ENTRY_PAGE=pages/login/index
```

说明：

- 后端会 mock `openid / unionid / phone`
- 不需要真实 `AppSecret`
- 仍然建议在微信开发者工具里运行小程序，因为 `uni.login`、`getPhoneNumber` 不是普通 H5 行为

### 2.2 本地 API 地址

`mini-program/common/config.js`：

```js
apiBaseUrl: "http://127.0.0.1:8000/api/v1"
```

注意：

- 微信开发者工具本地调试时，可在“详情 -> 本地设置”里临时关闭合法域名校验
- 真机调试不能依赖 `127.0.0.1`，必须改为公网 HTTPS 域名

---

## 3. 真实微信模式需要你做什么

### 3.1 微信公众平台

进入微信公众平台 -> 你的小程序 -> 开发 -> 开发管理 / 开发设置，完成：

1. 拿到 `AppID`
2. 生成或查看 `AppSecret`
3. 开通手机号能力（`getPhoneNumber`）
4. 配置服务器域名

至少要配：

- `request 合法域名`
- `uploadFile 合法域名`
- `downloadFile 合法域名`

都填同一个 HTTPS 根域名，例如：

```text
https://api.your-domain.com
```

### 3.2 腾讯云 / 服务器

你需要准备：

- 已备案域名
- HTTPS 证书
- 可公网访问的后端域名

后端 `.env`：

```env
WECHAT_MINIAPP_MOCK_LOGIN=false
WECHAT_MINIAPP_APP_ID=你的小程序AppID
WECHAT_MINIAPP_APP_SECRET=你的小程序AppSecret
WECHAT_MINIAPP_CLIENT_ENTRY_PAGE=pages/login/index
```

然后重启后端服务。

---

## 4. 小程序调试流程

### 4.1 HBuilderX

1. 打开项目根目录
2. 进入 `mini-program`
3. 运行 -> 运行到小程序模拟器 -> 微信开发者工具

### 4.2 微信开发者工具

1. 导入项目
2. 选择真实小程序 `AppID`
3. 打开“详情 -> 本地设置”
4. 本地 mock 阶段可勾选：
   - 不校验合法域名、web-view、TLS 版本以及 HTTPS 证书
5. 编译项目
6. 打开登录页，执行：
   - 微信一键登录
   - 授权手机号并继续

### 4.3 真机调试

前提：

- 真实 `AppID`
- 后端公网 HTTPS
- 微信后台已配置合法域名
- `WECHAT_MINIAPP_MOCK_LOGIN=false`

流程：

1. 微信开发者工具点击“预览”
2. 手机微信扫码
3. 在真机上走登录链路
4. 重点验证：
   - 已绑定老账号直登
   - 案件邀请登录自动绑案
   - Web 端生成二维码，小程序扫码后浏览器自动换取 token
   - 待审批律师被拦截
   - 同手机号多租户要求 `tenant_code`
   - 退出登录后不能再 refresh

### 4.4 本地 smoke 脚本

先确认后端已启动，且 `WECHAT_MINIAPP_MOCK_LOGIN=true`，然后执行：

```bash
python scripts/smoke_wechat_direct_login.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --phone <已有账号手机号> \
  --password <账号密码> \
  --tenant-code <可选>
```

通过标准：

- 输出 `[DONE] smoke_wechat_direct_login passed`
- 第二次 `wx-mini-login` 直接返回 token
- `logout` 后原 refresh token 再调用 `/auth/refresh` 返回 `401`

---

## 5. 当前代码位置

- 后端认证接口：`backend/app/api/routes_auth.py`
- 微信服务：`backend/app/services/mini_program.py`
- Web 登录页：`web-frontend/src/views/LoginView.vue`
- 小程序登录页：`mini-program/pages/login/index.vue`
- 小程序退出登录：`mini-program/common/session.js`
- 工作台退出入口：`mini-program/components/WorkspaceTabBar.vue`

---

## 6. 常见问题

### 6.1 登录页点了没反应

先检查：

- 是否在微信开发者工具里运行，而不是 H5
- 后端是否启动
- `mini-program/common/config.js` 的地址是否正确

### 6.2 `getPhoneNumber` 没有返回 code

通常是：

- 当前不是微信小程序上下文
- `AppID` 不正确
- 手机号能力未开通
- 真机未登录对应微信

### 6.3 真机能打开页面但接口失败

通常是：

- 没配合法域名
- 域名不是 HTTPS
- 证书异常
- Nginx 没把 `/api/v1` 反代到后端

### 6.4 案件邀请和机构律师邀请串了

当前约束是：

- 案件邀请必须带 `scene=client-case`
- 机构律师邀请必须带 `scene=lawyer-invite`
- Web 扫码确认必须带 `scene=web-login`
- 登录页按 `scene` 分流

如果链接不符合这个规则，前端会走错入口

---

## 7. 你下一步要做

1. 先确认是否继续用 mock 模式做开发
2. 如果要真机联调，提供真实 `AppID`
3. 在微信后台配置手机号能力和合法域名
4. 在腾讯云部署 HTTPS 后端
5. 先跑一遍 `scripts/smoke_wechat_direct_login.py`
6. 再跑真机登录与退出回归
