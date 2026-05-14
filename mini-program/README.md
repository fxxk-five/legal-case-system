# 小程序端说明

本目录承载微信小程序端，当前范围不是“只有当事人页面”，而是：

- 律师 / 机构管理员：与 Web 端保持同构工作台
- 当事人：小程序独有案件协作链路

技术路线：

- `uni-app + 微信开发者工具 + FastAPI 后端`

当前源码结构：

- 页面放在 `pages/*`
- 通用业务能力收口到 `features / entities / shared`
- 小程序源码里的 `common` 兼容目录已清空，表单与错误提示统一位于 `shared/lib/form.js`

## 当前认证模型

### Web 端

- 手机号 + 密码 + 短信校验

### 小程序端

- 当事人三入口并存：
  - 微信一键登录：`wx.login` + `getPhoneNumber`
  - 手机号 + 短信验证码
  - 手机号 + 账号密码
- 微信相关接口：
  - `/auth/wx-mini-login`
  - `/auth/wx-mini-phone-login`
  - `/auth/wx-mini-bind-existing`

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
- `PATCH /cases/{id}/client-remark`
- `PATCH /cases/{id}/lawyer-remark`
- `GET /cases/{id}/invite-qrcode`
- `GET /files/upload-policy`
- `GET /files/case/{case_id}`
- `GET /files/{id}/access-link`
- `POST /asr/transcribe`

### AI 能力

- `POST /ai/cases/{case_id}/parse-document`
- `POST /ai/cases/{case_id}/analyze`
- `GET /ai/tasks/{task_id}`
- `GET /ai/cases/{case_id}/facts`
- `GET /ai/cases/{case_id}/analysis-results`

## 本地联调

默认请求地址（`local` 环境）：

```text
http://127.0.0.1:8000/api/v1
```

小程序现在会在 `shared/config/index.js` 内按环境自动选择 `apiBaseUrl`，默认读取顺序如下：

1. 显式地址覆盖：`UNI_APP_API_BASE_URL` → `VUE_APP_API_BASE_URL` → `API_BASE_URL`
2. 环境名：`UNI_APP_RUNTIME_ENV` → `VUE_APP_RUNTIME_ENV` → `APP_ENV` → `NODE_ENV`

内置环境映射：

- `local / dev / development` → `http://127.0.0.1:8000/api/v1`
- `staging / test / testing` → `https://staging.your-domain.example/api/v1`
- `production / prod` → `https://your-domain.example/api/v1`

本地开发默认不需要改代码；如果要打测试包或生产包，请在启动 `HBuilderX` 或执行构建前设置环境变量，例如：

```powershell
$env:UNI_APP_RUNTIME_ENV="staging"
```

如果需要临时指向自定义地址，可直接设置：

```powershell
$env:UNI_APP_API_BASE_URL="https://staging.your-domain.example/api/v1"
```

如果当前只是本地开发，后端可使用：

```env
WECHAT_MINIAPP_MOCK_LOGIN=true
```

真实微信配置与真机调试流程见：

- `docs/project-setup.md`

## 推荐开发方式

1. 在 VS Code 中写代码
2. 用 HBuilderX 打开源码目录 `mini-program`
3. 运行到微信开发者工具，生成 `unpackage/dist/dev/mp-weixin`
4. 微信开发者工具导入 `unpackage/dist/dev/mp-weixin`
5. 在微信开发者工具里做预览和真机调试

> 注意：源码目录 `mini-program` 下没有 `project.config.json`，不能直接作为微信开发者工具导入目录。

## remark / ASR 联调

- 当事人备注页：`pages/client/upload-material`
- 律师备注页：`pages/lawyer/case-detail`
- 语音转文字走后端 `/asr/transcribe`，不依赖 `WechatSI` 插件
- 联调与验收清单见：
- `docs/user-manual.md`

## 当前已落地

- 小程序登录页已收口为三入口：微信一键登录 / 短信验证码 / 账号密码
- 案件邀请会显式带 `scene=client-case`
- 小程序工作台与当事人链路都提供显式退出登录入口
- 当事人补充说明与律师内部备注已接入统一 remark 组件
- 语音转文字走后端 ASR 降级链路，不依赖 `WechatSI`
