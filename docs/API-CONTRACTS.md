# API 契约（单一真源 / SSOT）

> 基线代码：`backend/app/api`、`backend/app/services`
> 统一前缀：`/api/v1`
> 更新时间：2026-03-19（与当前仓库实现对齐）

## 1. 通用约定

### 1.1 鉴权
- 除明确匿名接口外，统一使用：`Authorization: Bearer <token>`。
- JWT 关键 claim：`sub`、`tenant_id`、`role`、`is_tenant_admin`。

### 1.2 错误响应结构（统一）

```json
{
  "code": "CASE_NOT_FOUND",
  "message": "案件不存在。",
  "detail": "案件不存在。",
  "request_id": "uuid"
}
```

### 1.3 常用错误码
- 鉴权权限：`AUTH_REQUIRED`、`FORBIDDEN`
- 租户用户：`TENANT_NOT_FOUND`、`TENANT_INACTIVE`、`USER_NOT_FOUND`、`USER_ALREADY_EXISTS`、`USER_NOT_ACTIVE`
- 案件文件：`CASE_NOT_FOUND`、`CASE_ACCESS_DENIED`、`CASE_OPERATION_NOT_ALLOWED`、`FILE_NOT_FOUND`、`FILE_ACCESS_DENIED`、`FILE_TOKEN_INVALID`、`FILE_UPLOAD_INVALID`
- 邀请通知：`INVITE_NOT_FOUND`、`INVITE_INVALID`、`INVITE_EXPIRED`、`NOTIFICATION_NOT_FOUND`
- AI：`AI_TASK_NOT_FOUND`、`AI_ANALYSIS_NOT_FOUND`、`AI_OPERATION_NOT_ALLOWED`、`AI_TASK_CONFLICT`
- 通用：`VALIDATION_ERROR`、`CONFLICT`、`EXTERNAL_SERVICE_ERROR`、`INTERNAL_ERROR`

### 1.4 AI 幂等键（已实现）
- 适用接口：
  - `POST /ai/cases/{case_id}/parse-document`
  - `POST /ai/cases/{case_id}/analyze`
  - `POST /ai/cases/{case_id}/falsification`
- Header：`Idempotency-Key: <string>`（可选，最长 128）
- 语义：
  - 同租户、同案件、同任务类型、同发起人、同 key、同 payload：返回同一 `task_id`。
  - 同 key 但 payload 不同：返回 `409 AI_TASK_CONFLICT`。

---

## 2. 认证（Auth）

### 2.1 `POST /auth/login`
- 请求体：`phone`、`password`、可选 `tenant_code`
- 成功：`200`，返回 `{access_token, token_type}`
- 失败：
  - `400 VALIDATION_ERROR`（多租户需显式 `tenant_code`）
  - `401 AUTH_REQUIRED`（账号或密码错误）
  - `404 TENANT_NOT_FOUND`（目标租户不存在或停用）

### 2.2 `POST /auth/register`
- 请求体：`phone`、`password`、`real_name`、可选 `tenant_code`
- 成功：`201`，返回用户
- 失败：
  - `400 VALIDATION_ERROR`
  - `409 USER_ALREADY_EXISTS`

### 2.3 `POST /auth/wx-mini-login`
- 请求体：`code`
- 成功：
  - 已绑定微信：`200`，返回 `{access_token, refresh_token, token_type, wechat_openid, need_bind_phone=false, login_state="LOGGED_IN", user}`
  - 未绑定微信：`200`，返回 `{wechat_openid, need_bind_phone=true, login_state="NEED_PHONE_AUTH", wx_session_ticket}`
- 失败：
  - `400 WECHAT_API_ERROR`
  - `403 USER_NOT_ACTIVE`

### 2.4 `POST /auth/wx-mini-phone-login`
- 请求体：`phone_code`、`wx_session_ticket`、可选 `tenant_code`/`case_invite_token`/`real_name`
- 成功：`200`，返回 token + user，并把当前微信身份绑定到已有账号或当事人邀请案件
- 失败：
  - `400 VALIDATION_ERROR`
  - `400 INVITE_REQUIRED`
  - `401 AUTH_REQUIRED`
  - `403 USER_NOT_ACTIVE`
  - `404 TENANT_NOT_FOUND` / `CASE_NOT_FOUND`
  - `409 CONFLICT`

### 2.5 `POST /auth/wx-mini-bind-existing`
- 请求体：`phone`、`password`、`wx_session_ticket`、可选 `tenant_code`
- 成功：`200`，返回 token + user
- 失败：
  - `400 VALIDATION_ERROR`
  - `401 AUTH_REQUIRED`
  - `403 USER_NOT_ACTIVE`
  - `404 TENANT_NOT_FOUND`
  - `409 CONFLICT`

### 2.6 `POST /auth/wx-mini-bind`
- 兼容旧版小程序显式绑定接口；新版本优先使用 `wx-mini-phone-login` / `wx-mini-bind-existing`
- 请求体：`wechat_openid`、`phone`、可选 `password`/`tenant_id`/`tenant_code`/`case_invite_token`
- 成功：返回 token + user
- 失败：
  - `400 VALIDATION_ERROR`
  - `400 INVITE_REQUIRED`
  - `401 AUTH_REQUIRED`
  - `403 USER_NOT_ACTIVE`
  - `404 TENANT_NOT_FOUND` / `CASE_NOT_FOUND`
  - `409 CONFLICT`

### 2.7 `POST /auth/logout`
- 请求体：可选 `refresh_token`
- 成功：`204`
- 说明：
  - 若携带当前 refresh token，服务端会撤销对应 `auth_sessions`
  - 退出登录只终止当前会话，不解绑已关联的微信身份

### 2.8 `POST /auth/invite-register`
- 请求体：`token`、`phone`、`password`、`real_name`
- 成功：`201`
- 失败：
  - `404 INVITE_NOT_FOUND`
  - `400 INVITE_INVALID` / `INVITE_EXPIRED`
  - `409 USER_ALREADY_EXISTS`

---

## 3. 用户与律师管理（Users）

### 3.1 `GET /users/me`
- 获取当前用户

### 3.2 `GET /users/lawyers`
- 权限：租户管理员
- 失败：`403 FORBIDDEN`

### 3.3 `POST /users/lawyers`
- 权限：租户管理员
- 失败：`409 USER_ALREADY_EXISTS`

### 3.4 `GET /users/pending`
- 权限：租户管理员

### 3.5 `PATCH /users/{user_id}/approve`
- 失败：`404 USER_NOT_FOUND`

### 3.6 `DELETE /users/{user_id}/reject`
- 失败：`404 USER_NOT_FOUND`

### 3.7 `PATCH /users/{user_id}/status`
- 失败：`404 USER_NOT_FOUND`

---

## 4. 案件（Cases）

### 4.1 `POST /cases`
- 权限：`lawyer` / `tenant_admin`
- 失败：`403 CASE_OPERATION_NOT_ALLOWED`

### 4.2 `GET /cases`
- 标准分页参数：`page`、`page_size`（`page>=1`，`1<=page_size<=100`）
- 兼容分页参数：`skip`、`limit`（`skip>=0`，`1<=limit<=100`）
- 同时传两组参数时：若不满足 `skip==(page-1)*page_size` 且 `limit==page_size`，返回 `400 VALIDATION_ERROR`
- 可选筛选：`status`
- 响应头：`X-Page`、`X-Page-Size`

### 4.3 `GET /cases/{case_id}`
- 失败：`404 CASE_NOT_FOUND`、`403 CASE_ACCESS_DENIED`

### 4.4 `PATCH /cases/{case_id}`
- 失败：
  - `404 CASE_NOT_FOUND`
  - `403 CASE_OPERATION_NOT_ALLOWED`
  - `400/404 USER_NOT_FOUND`（指派律师不存在）

### 4.5 `GET /cases/{case_id}/invite-qrcode`
- 失败：`403 CASE_OPERATION_NOT_ALLOWED`、`404 CASE_NOT_FOUND`

---

## 5. 文件（Files）

### 5.1 `POST /files/upload?case_id={id}`
- multipart 字段名：`upload`
- 失败：`CASE_NOT_FOUND`、`FILE_ACCESS_DENIED`、`FILE_UPLOAD_INVALID`

### 5.2 `GET /files/upload-policy`
- 失败：`CASE_NOT_FOUND`、`FILE_ACCESS_DENIED`、`FILE_UPLOAD_INVALID`

### 5.3 `GET /files/case/{case_id}`
- 失败：`CASE_NOT_FOUND`、`FILE_ACCESS_DENIED`

### 5.4 `GET /files/{file_id}/access-link`
- 失败：`FILE_NOT_FOUND`、`FILE_ACCESS_DENIED`

### 5.5 `GET /files/{file_id}/download`
- 失败：`FILE_NOT_FOUND`、`FILE_ACCESS_DENIED`

### 5.6 `GET /files/access/{token}`
- 失败：`400 FILE_TOKEN_INVALID`、`404 FILE_NOT_FOUND`

---

## 6. AI（当前实现态）

> 当前执行模型：请求内同步执行（返回 `202`，但非队列 worker 异步）。

### 6.1 `POST /ai/cases/{case_id}/parse-document`
- 请求体：`file_id`、`parse_options`
- Header（可选）：`Idempotency-Key`
- 成功：`202`，`{task_id, status, message}`
- 失败：`FILE_NOT_FOUND`、`CASE_NOT_FOUND`、`CASE_ACCESS_DENIED`、`AI_OPERATION_NOT_ALLOWED`、`AI_TASK_CONFLICT`

### 6.2 `GET /ai/cases/{case_id}/facts`
- 查询参数：`fact_type`、`min_confidence`、`page`、`page_size`

### 6.3 `POST /ai/cases/{case_id}/analyze`
- Header（可选）：`Idempotency-Key`
- 成功：`202`，`{task_id, status, estimated_time}`
- 失败：`CASE_NOT_FOUND`、`CASE_ACCESS_DENIED`、`AI_OPERATION_NOT_ALLOWED`、`AI_TASK_CONFLICT`

### 6.4 `GET /ai/cases/{case_id}/analysis-results`

### 6.5 `POST /ai/cases/{case_id}/falsification`
- Header（可选）：`Idempotency-Key`
- 请求体：`analysis_id`、`challenge_modes`、`iteration_count`
- 失败：`AI_ANALYSIS_NOT_FOUND`、`AI_OPERATION_NOT_ALLOWED`、`AI_TASK_CONFLICT`

### 6.6 `GET /ai/cases/{case_id}/falsification-results`

### 6.7 `GET /ai/tasks/{task_id}`
- 失败：`AI_TASK_NOT_FOUND`、`AI_OPERATION_NOT_ALLOWED`

### 6.8 `GET /ws/ai/tasks/{task_id}?token=<jwt>`
- WS 鉴权已启用，按 JWT + 租户边界校验。

---

## 7. 租户（Tenants）

### 7.1 `POST /tenants/personal`
- 失败：`409 USER_ALREADY_EXISTS`

### 7.2 `POST /tenants/organization`
- 失败：`409 USER_ALREADY_EXISTS`

### 7.3 `POST /tenants/join`
- 失败：`TENANT_NOT_FOUND`、`TENANT_INACTIVE`、`USER_ALREADY_EXISTS`

### 7.4 `GET /tenants/invite/{tenant_code}`
- 失败：`TENANT_NOT_FOUND`

### 7.5 `GET /tenants/{tenant_id}/preview`
- 失败：`TENANT_NOT_FOUND`

### 7.6 `GET /tenants/current`
- 失败：`TENANT_NOT_FOUND`

### 7.7 `PATCH /tenants/current`
- 失败：`TENANT_NOT_FOUND`

### 7.8 `PATCH /tenants/members/{user_id}/approve`
- 失败：`USER_NOT_FOUND`、`CONFLICT`

---

## 8. 通知与统计

### 8.1 `GET /notifications`

### 8.2 `PATCH /notifications/{notification_id}/read`
- 失败：`NOTIFICATION_NOT_FOUND`

### 8.3 `GET /stats/dashboard`

---

## 9. 健康检查与文档
- `GET /api/v1/health`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`
- `GET /api/v1/openapi.json`

---

## 10. 前端对齐关键点（当前必须遵循）
- Web 案件详情：
  - `GET /files/case/{case_id}`
  - `PATCH /cases/{case_id}`
  - `POST /files/upload?case_id={case_id}`（字段名 `upload`）
  - `GET /cases/{case_id}/invite-qrcode`
- Web 律师管理：
  - `GET /users/lawyers`
  - `POST /users/lawyers`
  - `PATCH /users/{id}/approve`
  - `DELETE /users/{id}/reject`
- AI API：统一基于 `/api/v1` + `/ai/*`，禁止双前缀拼接。
