# BE-A05 执行单：错误码扩展与分层映射规范

## 1. 任务目标
- 建立统一、可扩展、可前后端联调的错误码体系，避免“同类错误返回不同 code/文案”。
- 明确 route/service/repository/dependency 的异常边界，禁止跨层泄漏 HTTP 语义。
- 保持现有错误响应结构稳定：`{ code, message, detail, request_id }`。

## 2. 范围
### 2.1 In Scope
- 错误码字典分层（通用层 + 领域层）。
- HTTP 状态码与业务错误码映射规则。
- 各层异常抛出/转换规范（route/service/repository/dependency）。
- 迁移计划与兼容策略（当前 `HTTPException` 存量治理）。
- 测试与联调验收标准。

### 2.2 Out of Scope
- 前端 UI 提示文案改版。
- 与错误体系无关的业务逻辑重构。
- WebSocket 事件协议重定义（仅要求错误码对齐，不改 WS 事件形态）。

## 3. 现状基线（代码事实）
- 已有基础错误码：`backend/app/core/errors.py` 定义了通用 + AI 相关 code。
- `backend/app/main.py` 已统一异常响应结构，并通过 handler 注入 `request_id`。
- 存量问题：多数 route/service/dependency 仍直接抛 `HTTPException`，导致：
  - 细粒度业务语义丢失（例如多类 404 全映射 `RESOURCE_NOT_FOUND`）；
  - 模块间错误语义不一致（同类问题可能返回不同 message/detail）；
  - 前端映射难以稳定（只能依赖中文文案）。

## 4. 目标规范（错误码体系）

## 4.1 保留的基础通用码
- `AUTH_REQUIRED`
- `FORBIDDEN`
- `RESOURCE_NOT_FOUND`
- `VALIDATION_ERROR`
- `CONFLICT`
- `INTERNAL_ERROR`

## 4.2 领域扩展码（建议默认值）
- 认证与租户：
  - `TENANT_NOT_FOUND`
  - `TENANT_INACTIVE`
  - `TENANT_ACCESS_DENIED`
  - `USER_NOT_FOUND`
  - `USER_ALREADY_EXISTS`
  - `USER_NOT_ACTIVE`
- 案件与文件：
  - `CASE_NOT_FOUND`
  - `CASE_ACCESS_DENIED`
  - `CASE_OPERATION_NOT_ALLOWED`
  - `FILE_NOT_FOUND`
  - `FILE_ACCESS_DENIED`
  - `FILE_TOKEN_INVALID`
  - `FILE_UPLOAD_INVALID`
- 邀请与通知：
  - `INVITE_NOT_FOUND`
  - `INVITE_EXPIRED`
  - `INVITE_INVALID`
  - `NOTIFICATION_NOT_FOUND`
- AI：
  - `AI_TASK_NOT_FOUND`
  - `AI_ANALYSIS_NOT_FOUND`
  - `AI_OPERATION_NOT_ALLOWED`
  - `AI_TASK_CONFLICT`
  - `AI_PROVIDER_ERROR`
- 外部依赖：
  - `EXTERNAL_SERVICE_ERROR`
  - `WECHAT_API_ERROR`
  - `STORAGE_ERROR`
  - `DATABASE_ERROR`

> 说明：若团队希望更小字典，可先实施 P0 集合（保留现有码 + 高频业务码），其余进入 P1 扩展。

## 4.3 HTTP 状态码映射规则
- `400` -> `VALIDATION_ERROR`（参数或业务前置条件不满足）
- `401` -> `AUTH_REQUIRED`
- `403` -> `FORBIDDEN` 或领域拒绝码（如 `CASE_ACCESS_DENIED`）
- `404` -> 领域 NOT_FOUND（如 `CASE_NOT_FOUND`/`FILE_NOT_FOUND`），兜底 `RESOURCE_NOT_FOUND`
- `409` -> `CONFLICT` 或领域冲突码（如 `AI_TASK_CONFLICT`）
- `422` -> `VALIDATION_ERROR`
- `500` -> `INTERNAL_ERROR`
- `502/503/504` -> `EXTERNAL_SERVICE_ERROR`（或更具体外部码）

## 5. 分层职责与抛错边界

## 5.1 route 层（`backend/app/api/routes_*`）
- 仅做协议层处理：参数绑定、权限依赖挂载、调用 service。
- 禁止新增业务语义 `HTTPException`；优先由 service 抛 `AppError`。
- 允许保留框架级参数校验失败（由全局 `RequestValidationError` handler 处理）。

## 5.2 dependency 层（如 `dependencies/auth.py`）
- 身份认证/权限依赖统一抛 `AppError`，携带稳定 code（如 `AUTH_REQUIRED`、`FORBIDDEN`）。
- 不直接返回仅文案的 `HTTPException`。

## 5.3 service 层
- 业务语义唯一归口，必须抛 `AppError(code=..., status_code=...)`。
- message 面向前端展示，detail 保留机器可读上下文（必要时可对象化）。

## 5.4 repository 层
- 不抛 `HTTPException` / `AppError`。
- 仅返回查询结果（对象/None）或抛数据库技术异常，由 service 统一翻译为业务错误。

## 6. 响应结构与字段语义
- 固定结构（不变）：
```json
{
  "code": "CASE_NOT_FOUND",
  "message": "案件不存在。",
  "detail": "案件不存在。",
  "request_id": "uuid"
}
```
- 字段约束：
  - `code`：稳定、可枚举、可前端映射。
  - `message`：可直接展示给用户（简洁中文）。
  - `detail`：调试信息或结构化明细；不可泄漏敏感信息。
  - `request_id`：全链路定位主键。

## 7. 迁移策略（存量 HTTPException 治理）
- 阶段 1（P0）：新增错误码字典与映射文档，保留 `HTTPException -> map_http_status_to_code` 兜底。
- 阶段 2（P1）：按模块迁移为 `AppError`（Auth -> Cases -> Files -> Tenants -> Users -> AI）。
- 阶段 3（P1）：收敛 `HTTPException` 到仅框架层使用，业务层禁用（lint/code-review 规则约束）。
- 阶段 4（P2）：前端以 `code` 为主映射提示，逐步降低文案耦合。

## 8. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A05-1 | 扩展 `ErrorCode` 枚举与注释 | `backend/app/core/errors.py` | 完整错误码字典 |
| A05-2 | 规范化状态码映射函数 | `backend/app/core/errors.py` | HTTP->业务码映射表 |
| A05-3 | 认证依赖迁移为 `AppError` | `backend/app/dependencies/auth.py` | 鉴权错误码稳定化 |
| A05-4 | route/service 存量 `HTTPException` 治理 | `backend/app/api`、`backend/app/services` | 业务错误统一 `AppError` |
| A05-5 | 外部依赖异常翻译 | `services/mini_program.py`、`services/file.py` 等 | 502/5xx 语义化 code |
| A05-6 | 测试覆盖 | `backend/tests/` | 鉴权/404/403/409/422/500 的 code 断言 |
| A05-7 | 契约文档同步 | `docs/API-CONTRACTS.md` | 错误码总表与示例 |
| A05-8 | 前端联调指引 | `docs/AI-CURRENT-STATUS.md` 或任务说明 | code 映射清单（不改 UI） |

## 9. 验收标准（DoD）

## 9.1 契约验收
- 业务异常响应均符合 `{code,message,detail,request_id}`。
- 高频场景具有稳定 code：登录失效、案件越权、文件不存在、AI 任务不存在等。

## 9.2 分层验收
- repository 层不出现 `HTTPException`。
- service 业务错误优先使用 `AppError`。
- route 层不再散落业务语义 `HTTPException`（仅保留必要协议层异常）。

## 9.3 联调验收
- Web/小程序无需修改 UI，即可通过 `code` 做稳定解析。
- 同一错误场景在不同端/不同接口返回同一 code。

## 9.4 测试验收
- 新增至少 10 条错误路径测试：
  - `401 AUTH_REQUIRED`
  - `403 FORBIDDEN` / `CASE_ACCESS_DENIED`
  - `404 CASE_NOT_FOUND` / `FILE_NOT_FOUND` / `AI_TASK_NOT_FOUND`
  - `409 CONFLICT`
  - `422 VALIDATION_ERROR`
  - `500 INTERNAL_ERROR`

## 10. 风险与默认策略
- 风险：一次性迁移全部模块，回归面过大。  
  默认策略：模块分批迁移，先高频链路（Auth/Cases/Files/AI）。
- 风险：前端仍按 `message` 匹配导致兼容不稳。  
  默认策略：文档明确“前端优先按 `code` 映射”并保持 message 兼容窗口。
- 风险：detail 透出敏感栈信息。  
  默认策略：`500` 场景 detail 固定通用文案，细节仅入日志。

## 11. 回滚策略
1. 保留 `HTTPException` 全局映射兜底，不中断现网。
2. 若某模块迁移后异常激增，按模块回退到旧抛错方式（不影响响应结构）。
3. 回滚期间维持 `request_id` 全链路可追踪，便于差异排查。

## 12. 预估工作量
- 设计与字典评审：0.5 人日
- 分模块改造与测试：1.5 人日
- 联调与文档同步：0.5 人日
- 合计：2.5 人日
