# 小程序端说明

本目录承载微信小程序端，当前范围不是“只有当事人页面”，而是：

- 律师 / 机构管理员：与 Web 端保持同构工作台
- 当事人：小程序独有案件协作链路

技术路线：

- `uni-app + 微信开发者工具 + FastAPI 后端`

## 当前认证模型

### Web 端

- 手机号 + 密码 + 短信校验

### 小程序端

- 默认：微信直登
  - `wx.login`
  - `getPhoneNumber`
  - `/auth/wx-mini-login`
  - `/auth/wx-mini-phone-login`
- 兼容：`/auth/wx-mini-bind-existing`

### 邀请链路

- 案件邀请：`pages/login/index?scene=client-case&token=...`
- 机构律师邀请注册：`pages/login/index?token=...`

## 关键页面

- `pages/login/index`：统一登录页，承接微信直登、案件邀请、机构律师邀请注册
- `pages/client/entry`：旧入口兼容页，自动跳转到新登录页
- `pages/client/case-list`：当事人案件列表
- `pages/client/case-detail`：当事人案件详情
- `pages/client/upload-material`：当事人补充材料
- `pages/lawyer/home`：律师/管理员工作台概览
- `pages/lawyer/cases`：案件管理
- `pages/lawyer/clients`：当事人管理
- `pages/lawyer/lawyers`：律师管理
- `pages/lawyer/analytics`：分析管理

## 对接后端接口（小程序端）

### 认证与注册

- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/sms/send`
- `POST /auth/sms/verify`
- `POST /auth/invite-register`
- `POST /auth/wx-mini-login`
- `POST /auth/wx-mini-phone-login`
- `POST /auth/wx-mini-bind-existing`
- `GET /users/me`

### 案件与文件

- `GET /cases`
- `GET /cases/{id}`
- `GET /cases/{id}/invite-qrcode`
- `GET /files/upload-policy`
- `GET /files/case/{case_id}`
- `GET /files/{id}/access-link`

### AI 能力

- `POST /ai/cases/{case_id}/parse-document`
- `POST /ai/cases/{case_id}/analyze`
- `GET /ai/tasks/{task_id}`
- `GET /ai/cases/{case_id}/facts`
- `GET /ai/cases/{case_id}/analysis-results`

## 本地联调

默认请求地址：

```text
http://127.0.0.1:8000/api/v1
```

如需修改，请编辑 `common/config.js`。

如果当前只是本地开发，后端可使用：

```env
WECHAT_MINIAPP_MOCK_LOGIN=true
```

真实微信配置与真机调试流程见：

- `docs/wechat-mini-direct-login-runbook.md`

## 推荐开发方式

1. 在 VS Code 中写代码
2. 用 HBuilderX 导入 `mini-program`
3. 运行到微信开发者工具
4. 在微信开发者工具里做预览和真机调试

## 当前已落地

- 小程序登录页已切到微信直登主入口
- 案件邀请会显式带 `scene=client-case`
- 小程序工作台与当事人链路都提供显式退出登录入口
