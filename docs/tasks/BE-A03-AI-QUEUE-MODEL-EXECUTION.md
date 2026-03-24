# BE-A03 执行单：AI 执行模型切换设计（同步 -> 队列）

## 1. 任务目标
- 将 AI 三类发起接口从“请求内同步执行”切换为“入队 + worker 异步执行”模型。
- 保持现有接口契约不变：`POST /api/v1/ai/cases/{case_id}/parse-document|analyze|falsification` 继续返回 `202 + task_id`。
- 明确 REST、队列调度、worker、任务状态持久化、WS 推送之间的职责边界，支持独立排期开发。

## 2. 范围
### 2.1 In Scope
- AI 任务执行链路的目标架构与落地步骤。
- 任务状态机与状态转移约束（`pending -> processing -> completed|failed`）。
- 入队消息结构、worker 消费协议、失败重试与超时策略。
- 与现有轮询/WS 通道的协同规则（REST + WS）。
- 兼容切换与回滚方案（特性开关）。

### 2.2 Out of Scope
- 实际后端代码改造（本执行单仅定义可实施规范）。
- 前端 UI/交互改造。
- AI 提示词与模型效果优化。

## 3. 现状基线（代码事实）
- 当前 `backend/app/services/ai.py` 在 `start_parse_document/start_analysis/start_falsification` 中创建任务后直接调用 `_execute_*`，属于同步执行。
- `backend/app/api/routes_ai.py` 已对外声明 `202 Accepted`，但并非真实异步队列语义。
- `backend/app/api/routes_ws_ai.py` 当前通过轮询 `ai_tasks` 推送进度，不依赖独立 worker 事件总线。
- `docker-compose.yml` 已包含 `redis` 服务，但后端依赖与配置中尚未接入队列框架参数。

## 4. 默认方案（本任务建议）
- 队列框架默认值：`Celery + Redis`。
- 运行模式开关：`AI_EXECUTION_MODE=sync|queue`，默认 `sync`（灰度完成后再切 `queue`）。
- 目标行为：
  - `sync`：保持当前行为（兼容兜底）。
  - `queue`：API 仅负责校验、建任务、入队并快速返回；执行由 worker 完成。

> 说明：若后续团队统一选择 RQ/Huey，允许替换实现，但必须保持下文约定的状态机、重试语义与接口输出不变。

## 5. 执行链路规范（REST + Worker + WS）

## 5.1 REST 入队阶段
1. 校验 JWT、租户、案件可见性、角色权限（维持现有规则）。
2. 创建 `ai_tasks` 记录，初始状态：
   - `status=pending`
   - `progress=0`
   - `message="Task queued."`（或统一中文文案）
3. 写入队列消息并返回：
   - HTTP `202`
   - `{ task_id, status }`

## 5.2 Worker 执行阶段
1. 消费消息后将任务置为 `processing`，设置 `started_at`。
2. 按 `task_type` 分发执行器：
   - `parse` -> 文档解析执行器
   - `analyze` -> 法律分析执行器
   - `falsify` -> 证伪执行器
3. 成功：
   - `status=completed`
   - `progress=100`
   - 设置 `result_id/completed_at/message`
4. 失败：
   - 根据重试策略重入队或最终置 `failed`
   - 记录 `error_message`，并写失败日志（带 `request_id/task_id`）

## 5.3 客户端状态获取
- `GET /api/v1/ai/tasks/{task_id}`：作为最终状态真源。
- `WS /ws/ai/tasks/{task_id}`：实时推送优先，轮询为降级兜底。
- WS 事件类型保持不变：`progress|completed|failed`。

## 6. 队列消息与状态字段规范

## 6.1 入队消息建议结构
```json
{
  "task_id": "uuid",
  "tenant_id": 1,
  "case_id": 1001,
  "task_type": "analyze",
  "input_params": {},
  "request_id": "req-xxx",
  "submitted_at": "2026-03-19T12:00:00+00:00"
}
```

## 6.2 `ai_tasks` 扩展字段建议（后续实现参考）
- `queued_at`：入队时间
- `retry_count`：已重试次数
- `max_retries`：最大重试次数
- `next_retry_at`：下一次重试时间
- `worker_id`：执行节点标识
- `last_heartbeat_at`：心跳时间（可选）

## 6.3 状态转移约束
- 允许：`pending -> processing -> completed|failed`
- 重试分支允许：`processing -> pending`（仅系统重试）
- 禁止：`completed -> processing`、`failed -> processing`（除人工补偿流程）

## 7. 失败补偿、幂等与重试约束
- 与 BE-A02 配合：同一 `Idempotency-Key` 命中时不重复创建任务。
- worker 幂等保护：
  - 消费前二次读取任务状态；
  - 若已 `completed/failed`，直接丢弃重复消息。
- 默认重试建议：
  - `max_retries=2`
  - 退避：`5s -> 20s`
  - 超时：按任务类型区分（`parse=120s`, `analyze=180s`, `falsify=180s`）
- 超过重试上限后置 `failed`，并保留完整错误上下文。

## 8. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A03-1 | 抽象执行入口与模式开关（sync/queue） | `backend/app/services/ai.py` | 执行模式路由与统一入口 |
| A03-2 | 拆分执行器（parse/analyze/falsify） | `backend/app/services/ai_executors/`（建议新建） | 可被 API 与 worker 复用的纯执行逻辑 |
| A03-3 | 队列适配层与任务投递器 | `backend/app/services/ai_queue.py`（建议新建） | 入队接口与消息序列化 |
| A03-4 | Worker 进程与消费处理器 | `backend/app/workers/ai_worker.py`（建议新建） | 消费、状态更新、异常重试 |
| A03-5 | 任务仓储扩展（重试/心跳字段） | `backend/app/repositories/ai.py`、`models`、`alembic` | 状态字段与查询能力 |
| A03-6 | 可观测性与日志规范 | `services`、`workers`、`main` | request_id/task_id 全链路日志 |
| A03-7 | 测试清单 | `backend/tests/` | API 入队、worker 成功、失败重试、重复消息幂等 |
| A03-8 | 契约文档同步 | `docs/API-CONTRACTS.md`、`docs/AI-CURRENT-STATUS.md` | “真实异步”语义更新与联调说明 |

## 9. 验收标准（DoD）

## 9.1 契约验收
- 现有 AI 三个 POST 路径、方法、请求体、响应体保持兼容。
- `task_id` 可用于轮询与 WS 订阅，不需要前端改 UI 即可联调。

## 9.2 行为验收
- `queue` 模式下，API 请求返回时间与 AI 执行耗时解耦。
- worker 正常时：任务按状态机流转并落库结果。
- worker 异常时：触发重试，超过阈值后任务进入 `failed`。

## 9.3 一致性验收
- `GET /ai/tasks/{task_id}` 与 WS 终态一致。
- 同一任务不会因重复消费产生重复写入。

## 10. 联调回归约束
1. Web `CaseDetailView` 的 parse/analyze/falsify 三入口无需改调用路径。
2. 小程序 `case-detail.vue` 的 `navToAI(type)` 跳转链路无需改路由。
3. `useAITask` 轮询兜底必须继续可用，WS 失败不阻塞主流程。

## 11. 风险与默认策略
- 风险：当前仓库未集成 Celery/Redis 参数配置，直接切 `queue` 会启动失败。  
  默认策略：先合入 `sync|queue` 开关与空实现，默认保持 `sync`。
- 风险：任务长时间 `processing` 造成“僵尸任务”。  
  默认策略：增加 `last_heartbeat_at` + 超时巡检任务，将超时任务标记 `failed`。
- 风险：重复投递导致重复执行。  
  默认策略：worker 消费前做任务终态检查，配合 BE-A02 幂等键。

## 12. 回滚策略
1. 环境变量回切：`AI_EXECUTION_MODE=sync`。
2. 保留队列相关代码与表结构，不删除历史 `ai_tasks` 数据。
3. 停止 worker 进程后，API 继续同步模型对外服务。

## 13. 预估工作量
- 设计细化与评审：0.5 人日
- 后端实现与迁移：2 人日
- 联调与测试：1 人日
- 合计：3.5 人日
