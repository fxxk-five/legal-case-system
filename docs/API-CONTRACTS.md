# API 契约

> 统一前缀：`/api/v1`
> 当前路由聚合入口：`backend/app/api/api_v1.py`

## 通用约定

- 认证方式：`Authorization: Bearer <token>`
- 全局请求链路会返回 `X-Request-ID`
- WebSocket AI 进度通道：`/ws/ai/tasks/{task_id}`

### 错误响应

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Request validation failed.",
  "detail": [],
  "request_id": "uuid"
}
```

常见错误码：

- 鉴权：`AUTH_REQUIRED`、`FORBIDDEN`
- 租户 / 用户：`TENANT_NOT_FOUND`、`TENANT_INACTIVE`、`USER_NOT_FOUND`、`USER_ALREADY_EXISTS`
- 案件 / 文件：`CASE_NOT_FOUND`、`CASE_ACCESS_DENIED`、`CASE_OPERATION_NOT_ALLOWED`、`FILE_NOT_FOUND`、`FILE_ACCESS_DENIED`
- AI：`AI_TASK_NOT_FOUND`、`AI_ANALYSIS_NOT_FOUND`、`AI_OPERATION_NOT_ALLOWED`、`AI_TASK_CONFLICT`

## 认证与会话：`/auth`

- `POST /auth/login`
- `POST /auth/register`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/password`
- `POST /auth/sms/send`
- `POST /auth/sms/verify`
- `POST /auth/sms-login`
- `POST /auth/login-advice`
- `POST /auth/invite-register`
- `POST /auth/wx-mini-login`
- `POST /auth/wx-mini-phone-login`
- `POST /auth/wx-mini-bind-existing`
- `POST /auth/wx-mini-bind`
- `POST /auth/web-wechat-login`
- `GET /auth/web-wechat-login/{ticket}`
- `GET /auth/web-wechat-login/{ticket}/mini-code`
- `POST /auth/web-wechat-login/{ticket}/confirm`
- `POST /auth/web-wechat-login/{ticket}/exchange`

当前实现特征：

- Web 支持密码 / 短信 / 微信扫码登录。
- 小程序支持一键登录 / 短信 / 密码。
- `POST /auth/login-advice` 用于登录前置判断（是否需 tenant_code、是否待审批、推荐端）。
- 同手机号命中多个租户时需要 `tenant_code`。
- 邀请绑案可在登录时自动完成。

`POST /auth/login-advice` 请求体：

```json
{
  "phone": "13800000000",
  "tenant_code": "tenant_demo",
  "case_invite_token": null
}
```

返回关键字段：

- `requires_tenant_code`: 是否必须输入 `tenant_code`
- `requires_admin_approval`: 当前账号是否处于待审批
- `recommended_entry`: 推荐端（`web` / `mini-program`）
- `login_state`: `ready` / `pending_approval` / `not_found`
- `support_hint`: 支持侧统一排查话术

## 用户与租户：`/users`、`/tenants`

### `users`

- `GET /users/me`
- `GET /users/lawyers`
- `POST /users/lawyers`
- `POST /users/invite-lawyer`
- `GET /users/pending`
- `PATCH /users/{user_id}/approve`
- `DELETE /users/{user_id}/reject`
- `PATCH /users/{user_id}/status`
- `GET /users`

### `tenants`

- `POST /tenants/personal`
- `POST /tenants/organization`
- `POST /tenants/join`
- `GET /tenants/invite/{tenant_code}`
- `GET /tenants/{tenant_id}/preview`
- `GET /tenants/current`
- `GET /tenants`
- `PATCH /tenants/current`
- `PATCH /tenants/{tenant_id}/status`
- `GET /tenants/{tenant_id}/ai-budget`
- `PATCH /tenants/{tenant_id}/ai-budget`
- `GET /tenants/{tenant_id}/cases/{case_id}/ai-budget`
- `PATCH /tenants/{tenant_id}/cases/{case_id}/ai-budget`
- `PATCH /tenants/members/{user_id}/approve`

## 案件与当事人：`/cases`、`/clients`

### `cases`

- `POST /cases`
- `GET /cases`
- `GET /cases/{case_id}`
- `PATCH /cases/{case_id}`
- `PATCH /cases/{case_id}/client-remark`
- `PATCH /cases/{case_id}/lawyer-remark`
- `GET /cases/{case_id}/invite-qrcode`

### `clients`

- `GET /clients`
- `GET /clients/{client_id}`
- `PATCH /clients/{client_id}`

当前接口语义：

- `client-remark` 面向当事人追加补充说明。
- `lawyer-remark` 面向律师 / 机构管理员维护内部备注。
- 案件详情返回字段会按角色裁剪。

## 文件、报告与语音：`/cases/*/files*`、`/files`、`/asr`

### 按案件范围

- `GET /cases/{case_id}/files`
- `POST /cases/{case_id}/files`
- `GET /cases/{case_id}/files/upload-policy`
- `POST /cases/{case_id}/files/complete-upload`
- `GET /cases/{case_id}/reports`
- `GET /cases/{case_id}/report/access-link`
- `GET /cases/{case_id}/reports/{report_name}/access-link`
- `GET /cases/{case_id}/reports/{report_name}`
- `GET /cases/{case_id}/report`

### 通用文件接口

- `POST /files/upload`
- `GET /files/upload-policy`
- `POST /files/complete-upload`
- `GET /files/case/{case_id}`
- `GET /files/{file_id}/access-link`
- `GET /files/{file_id}/download`
- `GET /files/access/{token}`
- `DELETE /files/{file_id}`

### ASR

- `POST /asr/transcribe`

## AI、统计与通知：`/ai`、`/analytics`、`/stats`、`/notifications`

### `ai`

- `POST /ai/cases/{case_id}/parse-document`
- `GET /ai/cases/{case_id}/facts`
- `POST /ai/cases/{case_id}/analyze`
- `GET /ai/cases/{case_id}/analysis-results`
- `POST /ai/cases/{case_id}/falsification`
- `GET /ai/cases/{case_id}/falsification-results`
- `GET /ai/tasks`
- `GET /ai/tasks/{task_id}`
- `POST /ai/tasks/{task_id}/retry`

### `analytics`

- `GET /analytics/ai-usage`
- `GET /analytics/prompts`
- `GET /analytics/provider-settings`

### `stats`

- `GET /stats/dashboard`

### `notifications`

- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`

## 幂等与前端对齐要求

- AI 发起接口支持可选 `Idempotency-Key`。
- Web 当前应把 AI 交互理解为“文档解析为主”，不要依赖已重定向的分析 / 证伪页面作为独立入口。
- 当事人端只允许访问本人案件、本人可见文件与摘要结果。
