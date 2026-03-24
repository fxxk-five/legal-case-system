# BE-A01 执行单：AI WebSocket 鉴权落地

## 1. 任务目标
- 为 `GET /ws/ai/tasks/{task_id}` 增加生产可用的鉴权与租户隔离能力。
- 保持与现有 REST 鉴权口径一致（JWT + `tenant_id` + `role`）。
- 不改业务功能语义，只补安全边界与可观测性。

## 2. 范围
### 2.1 In Scope
- WebSocket 握手鉴权（JWT 校验）。
- 任务归属校验（`task_id` 必须属于当前 `tenant_id`）。
- 角色权限校验（与 `GET /api/v1/ai/tasks/{task_id}` 一致）。
- 鉴权失败/越权失败的关闭码与错误事件规范。
- 最小测试与文档更新。

### 2.2 Out of Scope
- AI 执行模型改造（同步 -> 队列）。
- 任务重试与幂等机制。
- 前端页面重构。

## 3. 默认方案（本任务采用）
- Token 传输：`/ws/ai/tasks/{task_id}?token=<jwt>`
  - 原因：浏览器原生 `WebSocket` 不便携带 `Authorization` header。
- 鉴权来源：复用现有 JWT 解析规则（`SECRET_KEY`、`ALGORITHM`）。
- 鉴权失败行为：发送结构化错误消息后关闭连接。

## 4. 协议与行为规范

## 4.1 握手参数
- 路径参数：`task_id`
- Query 参数：`token`（必填）

## 4.2 鉴权校验顺序
1. 校验 `token` 是否存在。
2. JWT 解码与签名校验。
3. 载荷最小字段校验：`sub`、`tenant_id`、`role`。
4. 任务归属校验：`task.tenant_id == token.tenant_id`。
5. 角色权限校验：`client` 不允许订阅 AI 任务进度。

## 4.3 失败语义（建议）
- 未提供 token / token 无效：`4401`
- 无权限（角色或租户不匹配）：`4403`
- 任务不存在：`4404`

> 关闭前必须先发送一次错误事件，格式与当前 `failed` 事件兼容：
```json
{
  "type": "failed",
  "task_id": "xxx",
  "progress": 0,
  "error": "鉴权失败或无权限。",
  "timestamp": "2026-03-19T12:00:00+00:00"
}
```

## 5. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标文件 | 产出 |
|---|---|---|---|
| A01-1 | 新增 WS 鉴权 helper（JWT 解析与用户载荷） | `backend/app/dependencies/auth.py` 或新增 `backend/app/dependencies/ws_auth.py` | 可复用鉴权函数 |
| A01-2 | 在 WS 路由接入 token 参数与鉴权流程 | `backend/app/api/routes_ws_ai.py` | 握手鉴权与关闭码 |
| A01-3 | 增加任务归属和角色权限校验 | `backend/app/api/routes_ws_ai.py` | tenant/role 双校验 |
| A01-4 | 日志脱敏与 request_id 关联 | `backend/app/api/routes_ws_ai.py`、`backend/app/main.py` | 无 token 明文日志 |
| A01-5 | 增加测试用例 | `backend/tests/` | 鉴权成功/失败/越权覆盖 |
| A01-6 | 更新契约文档 | `docs/API-CONTRACTS.md`、`docs/AI-CURRENT-STATUS.md` | WS 鉴权说明 |

## 6. 验收标准（DoD）

## 6.1 功能验收
- 有效 token + 正确租户 + 非 client 角色：可接收进度事件。
- 无 token：连接被拒绝并返回标准错误事件。
- 非法 token：连接被拒绝并返回标准错误事件。
- 跨租户 task_id：连接被拒绝。
- `client` 角色订阅：连接被拒绝。

## 6.2 安全验收
- 服务日志中不出现 JWT 明文。
- 不能通过构造 `task_id` 读取其他租户任务状态。

## 6.3 兼容性验收
- 现有轮询接口 `GET /api/v1/ai/tasks/{task_id}` 行为不变。
- 前端未改动时，WS 失败仍可走轮询降级（不阻断主流程）。

## 6.4 测试验收
- 新增至少 4 条测试：
  - 无 token
  - 无效 token
  - 跨租户 token
  - 正常订阅

## 7. 联调回归清单
1. 律师发起 AI 任务后，WS 正常接收 `progress/completed`。
2. 当事人账号订阅同 task，收到权限拒绝并断开。
3. 关闭 WS 后轮询仍可获取最终状态。

## 8. 风险与应对
- 风险：query token 可能被代理日志记录。
  - 应对：Nginx/应用日志脱敏，禁止记录原始 query。
- 风险：前端未及时传 token 导致进度面板不可用。
  - 应对：保持轮询兜底，并在前端显示“实时通道不可用，已降级轮询”。

## 9. 回滚策略
- 若 WS 鉴权上线后出现广泛订阅失败：
  1. 保留鉴权 helper；
  2. 临时回退为“仅任务存在校验 + 轮询兜底”；
  3. 通过发布开关控制是否启用严格鉴权。

## 10. 预估工作量
- 设计与开发：0.5 人日
- 测试与联调：0.5 人日
- 合计：1 人日

