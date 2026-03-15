# 小程序端说明

本目录用于承载微信小程序端，技术路线保持为 `uni-app + 微信开发者工具 + 现有 FastAPI 后端`。

## 当前已完成

- 建立 uni-app 基础目录
- 建立律师端页面骨架
- 建立当事人扫码进入页面骨架
- 封装微信登录、手机号绑定、案件接口调用

## 推荐开发方式

1. 在 VS Code 中编写代码。
2. 用 HBuilderX 导入本目录，运行到微信开发者工具。
3. 在微信开发者工具中完成预览、真机调试、上传体验版。

## 后端联调地址

默认请求地址：

```text
http://127.0.0.1:8000/api/v1
```

如需修改，请编辑 [common/config.js](/D:/code/law/legal-case-system/mini-program/common/config.js)。

## 当前联调接口

- `POST /auth/wx-mini-login`
- `POST /auth/wx-mini-bind`
- `GET /cases`
- `POST /cases`
- `GET /cases/{id}`
- `GET /cases/{id}/invite-qrcode`
- `GET /files/case/{case_id}`
- `POST /files/upload`

## 说明

- 当前后端默认开启 `WECHAT_MINIAPP_MOCK_LOGIN=true`，方便本地开发。
- 未配置真实微信 `AppID/AppSecret` 时，后端会用 mock openid 跑通流程。
- 真正上线前，需要把 `backend/.env` 中的微信配置改成真实值，并关闭 mock 登录。
