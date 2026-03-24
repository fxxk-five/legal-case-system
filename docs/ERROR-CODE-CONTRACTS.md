# 错误码契约（联调基线）

## 1. 统一错误响应结构

所有业务错误统一返回：

```json
{
  "code": "CASE_NOT_FOUND",
  "message": "案件不存在。",
  "detail": "案件不存在。",
  "request_id": "9f8f0a15-9f48-4fb2-a385-36d880012345"
}
```

字段说明：
- `code`：前后端联调主键，前端优先按该字段映射提示。
- `message`：可直接展示给用户的简短提示。
- `detail`：调试细节或与 `message` 一致的补充信息。
- `request_id`：链路追踪 ID，用于日志定位。

## 2. 本轮已落地高频错误码

鉴权与权限：
- `AUTH_REQUIRED`
- `FORBIDDEN`

租户与用户：
- `TENANT_NOT_FOUND`
- `TENANT_INACTIVE`
- `USER_NOT_FOUND`
- `USER_ALREADY_EXISTS`
- `USER_NOT_ACTIVE`

案件与文件：
- `CASE_NOT_FOUND`
- `CASE_ACCESS_DENIED`
- `CASE_OPERATION_NOT_ALLOWED`
- `FILE_NOT_FOUND`
- `FILE_ACCESS_DENIED`
- `FILE_TOKEN_INVALID`
- `FILE_UPLOAD_INVALID`

邀请与通知：
- `INVITE_NOT_FOUND`
- `INVITE_INVALID`
- `INVITE_EXPIRED`
- `NOTIFICATION_NOT_FOUND`

AI 与外部服务：
- `AI_TASK_NOT_FOUND`
- `AI_ANALYSIS_NOT_FOUND`
- `AI_OPERATION_NOT_ALLOWED`
- `WECHAT_API_ERROR`

通用兜底：
- `VALIDATION_ERROR`
- `CONFLICT`
- `EXTERNAL_SERVICE_ERROR`
- `INTERNAL_ERROR`

## 3. 状态码映射规则（后端兜底）

- `400/422 -> VALIDATION_ERROR`
- `401 -> AUTH_REQUIRED`
- `403 -> FORBIDDEN`
- `404 -> RESOURCE_NOT_FOUND`
- `409 -> CONFLICT`
- `502/503/504 -> EXTERNAL_SERVICE_ERROR`
- `500 -> INTERNAL_ERROR`

说明：业务接口优先使用领域错误码（例如 `CASE_NOT_FOUND`），只有未显式标注时才走上述兜底映射。

## 4. 前端解析顺序（已对齐）

Web 与小程序统一按以下顺序解析错误：
1. 优先按 `code` 映射友好提示。
2. 若 `detail` 为数组（校验错误）则逐项拼接。
3. 回退到 `message`。
4. 再回退到 `detail`（字符串）或通用提示。

