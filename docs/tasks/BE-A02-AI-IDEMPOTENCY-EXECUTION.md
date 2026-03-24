# BE-A02 执行单：AI 任务幂等键规范落地

## 1. 任务目标
- 为 AI 发起类接口建立统一幂等规范，避免重复提交导致重复任务与重复计费。
- 仅定义并落地“协议与后端行为标准”，不改变现有业务语义。
- 与当前接口契约保持兼容：`POST /ai/cases/{case_id}/parse-document|analyze|falsification`。

## 2. 范围
### 2.1 In Scope
- 幂等头规范：`Idempotency-Key`。
- 幂等作用域与指纹（tenant/case/task_type/request_body_hash）。
- 幂等记录存储设计与状态机。
- 命中行为：返回已存在任务（不重复创建）。
- 冲突行为：同 key 不同 payload 的拒绝策略。
- 最小测试与文档更新。

### 2.2 Out of Scope
- AI 队列化改造（BE-A03）。
- 前端页面改造。
- 计费系统扣费规则重构。

## 3. 默认方案（本任务采用）
- 客户端在 AI 发起请求时可选传入：
  - Header: `Idempotency-Key: <uuid-or-random-string>`
- 后端行为：
  - 未传 `Idempotency-Key`：按现有逻辑执行（向后兼容）。
  - 传入后启用幂等保护。

## 4. 幂等语义规范

## 4.1 覆盖接口
- `POST /api/v1/ai/cases/{case_id}/parse-document`
- `POST /api/v1/ai/cases/{case_id}/analyze`
- `POST /api/v1/ai/cases/{case_id}/falsification`

## 4.2 幂等作用域
- 建议唯一作用域键：
  - `tenant_id + case_id + task_type + idempotency_key`

## 4.3 请求指纹
- 对请求体做稳定化序列化后哈希（`request_body_hash`）。
- 目的：
  - 同 key + 同 payload：复用既有任务。
  - 同 key + 不同 payload：判定冲突。

## 4.4 状态机（幂等记录）
- `created`：首次记录写入，业务任务创建中。
- `completed`：已绑定 `task_id`，可复用返回。
- `conflicted`：同 key 不同 payload。
- `expired`：超过 TTL（默认 24h）。

## 4.5 命中与冲突行为
- 命中（同 key 同 payload）：
  - HTTP `202`，返回首次任务响应体（`task_id/status/...`）。
- 冲突（同 key 不同 payload）：
  - HTTP `409`
  - `code=CONFLICT`
  - `message=幂等键冲突，请更换 Idempotency-Key。`

## 4.6 TTL 默认值
- 默认：24 小时。
- 过期后同 key 可重新使用。

---

## 5. 数据结构建议（后续实现参考）

## 5.1 建议新表：`api_idempotency_records`
- 字段建议：
  - `id`
  - `tenant_id`
  - `case_id`
  - `task_type`
  - `idempotency_key`
  - `request_body_hash`
  - `task_id`
  - `status`（created/completed/conflicted/expired）
  - `created_at`
  - `updated_at`
  - `expires_at`
- 唯一索引建议：
  - `(tenant_id, case_id, task_type, idempotency_key)`

## 5.2 清理策略
- 定时任务每日清理过期幂等记录（可与后续 worker 一并实现）。

---

## 6. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标文件 | 产出 |
|---|---|---|---|
| A02-1 | 定义幂等 header 与校验器 | `backend/app/api/routes_ai.py` | Header 解析与参数校验 |
| A02-2 | 幂等记录模型与迁移设计 | `backend/app/models/`、`alembic/versions/` | 新表与索引 |
| A02-3 | Repository 幂等访问层 | `backend/app/repositories/ai.py` 或新 repo | 查询/写入/冲突判定 |
| A02-4 | Service 幂等编排 | `backend/app/services/ai.py` | 命中复用与冲突返回 |
| A02-5 | 测试覆盖 | `backend/tests/` | 命中/冲突/TTL 基本覆盖 |
| A02-6 | 契约文档更新 | `docs/API-CONTRACTS.md`、`docs/AI-CURRENT-STATUS.md` | 幂等语义可查 |

---

## 7. 验收标准（DoD）

## 7.1 功能验收
- 同一请求（同 key 同 payload）重复提交 3 次，仅创建 1 个任务。
- 命中返回 `task_id` 与首次一致。
- 同 key 不同 payload 返回 `409 CONFLICT`。

## 7.2 一致性验收
- 三个 AI 发起接口行为一致。
- 幂等命中时不得重复写入分析/证伪结果。

## 7.3 兼容性验收
- 不传 `Idempotency-Key` 时，行为与当前版本一致。
- 不影响轮询接口 `GET /ai/tasks/{task_id}` 与 WS 订阅流程。

## 7.4 测试验收
- 最少新增 5 条：
  - parse 命中
  - analyze 命中
  - falsification 命中
  - 冲突（同 key 不同 payload）
  - 未传 key 兼容路径

---

## 8. 联调约束
- Web 与小程序统一通过 API client 注入 `Idempotency-Key`。
- key 生成建议：
  - 前端发起前生成 UUID v4。
  - 一次用户点击对应一个 key。
- 重试策略：
  - 网络超时重试必须复用同一个 key。

---

## 9. 风险与应对
- 风险：作用域过小导致误命中（不同场景被复用）。
  - 应对：绑定 `tenant_id + case_id + task_type`。
- 风险：作用域过大导致幂等失效（重复任务仍产生）。
  - 应对：协议与实现统一，禁止只按 key 全局去重。
- 风险：请求体序列化不稳定导致误冲突。
  - 应对：统一 JSON 规范化（key 排序 + 去空白）后再哈希。

---

## 10. 回滚策略
- 若幂等逻辑导致大面积误判：
  1. 临时降级为“仅记录不拦截”模式；
  2. 保持 `Idempotency-Key` 接口不移除；
  3. 修复指纹与作用域后再恢复强校验。

---

## 11. 预估工作量
- 设计与实现：1 人日
- 测试与联调：0.5 人日
- 合计：1.5 人日

