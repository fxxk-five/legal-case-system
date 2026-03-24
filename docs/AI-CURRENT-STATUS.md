# AI 当前实现状态（以代码为准）

## 1. 状态总览
- 当前 AI 能力已接入后端 API 与数据表。
- 任务接口语义为“202 Accepted”，但执行模型是**请求内同步执行**。
- 尚未接入 Celery/Redis worker 队列，不具备异步任务解耦能力。

## 2. 已实现能力

### 2.1 文档解析
- 接口：`POST /api/v1/ai/cases/{case_id}/parse-document`
- 输出：结构化事实，支持后续案件事实查看。

### 2.2 法律分析
- 接口：`POST /api/v1/ai/cases/{case_id}/analyze`
- 结果查询：`GET /api/v1/ai/cases/{case_id}/analysis-results`

### 2.3 证据证伪
- 接口：`POST /api/v1/ai/cases/{case_id}/falsification`
- 结果查询：`GET /api/v1/ai/cases/{case_id}/falsification-results`

### 2.4 任务状态查询
- 接口：`GET /api/v1/ai/tasks/{task_id}`

### 2.5 AI 发起接口幂等键（已实现）
- 接口：`parse-document` / `analyze` / `falsification`
- 方式：可选请求头 `Idempotency-Key`
- 行为：
  - 同作用域同 payload 复用同一 `task_id`
  - 同 key 不同 payload 返回 `409 AI_TASK_CONFLICT`

## 3. 未实现能力（与旧文档假设差异）
- 未实现 Celery 任务队列。
- 未实现 Redis 任务调度/重试策略。
- 未实现真正后台异步执行与 worker 扩缩容。
- 未实现完整的失败重试与幂等补偿机制。

## 4. 关键限制与风险
- 高并发下，AI 请求会占用 API worker，存在超时与阻塞风险。
- “接口异步语义”与“同步执行现实”可能导致容量评估失真。
- AI WebSocket 进度通道存在鉴权风险，生产不可直接放开。

## 5. 配置与运行前提
- 关键配置来源：`backend/.env`。
- 当前默认：`AI_ENABLED=true`、`AI_MOCK_MODE=true`。
- 若切到真实模型：需提供 `OPENAI_API_KEY`，并评估成本与限额参数。

## 6. 与前端协作口径
- 前端必须按 `docs/API-CONTRACTS.md` 调用接口。
- 页面文案应避免宣称“已接入异步队列/可重试任务”。
- 任务状态展示需提示“当前为同步执行模型”。

## 7. 近期优化优先级
1. P0：补齐 AI WebSocket 鉴权或临时下线。
2. P1：落地 worker 队列（Celery/RQ 任选其一）。
3. P1：补任务重试、超时与失败恢复。
4. P2：引入 AI 任务指标与告警。

---

## 8. 2026-03-19 Runtime Update
- Added OpenAI-compatible provider integration in backend:
  - `backend/app/services/openai_compatible.py`
  - `backend/app/services/ai.py` (parse/analyze/falsify runtime branch)
- Runtime mode:
  - `AI_MOCK_MODE=true` -> keep deterministic mock behavior
  - `AI_MOCK_MODE=false` -> call `${OPENAI_API_BASE}/chat/completions`
- Current project remains synchronous task execution model (not queue worker yet).
