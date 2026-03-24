# BE-A04 执行单：分页规范统一设计（`skip/limit` -> `page/page_size`）

## 1. 任务目标
- 统一后端分页入参规范为 `page/page_size`，减少联调歧义与参数漂移。
- 保持现有业务可用：历史调用 `skip/limit` 在兼容窗口内继续可用。
- 不破坏现有前端页面行为（Web 与小程序当前 `/cases` 列表调用可直接继续运行）。

## 2. 范围
### 2.1 In Scope
- 统一分页参数规范（后端路由层 + 服务/仓储换算口径）。
- 历史参数兼容策略（`skip/limit` 与 `page/page_size` 共存规则）。
- 契约文档更新要求（`docs/API-CONTRACTS.md`）。
- 联调回归约束（Web、小程序现有列表查询链路）。

### 2.2 Out of Scope
- 前端 UI 改版或交互调整。
- 响应体结构大改（例如将 `/cases` 从数组改为 `items/meta` 包裹）。
- 与分页无关的接口重构。

## 3. 现状基线（代码事实）
- `GET /api/v1/cases`：`backend/app/api/routes_cases.py` 使用 `skip/limit`，返回 `list[CaseListItem]`。
- `GET /api/v1/ai/cases/{case_id}/facts`：`backend/app/api/routes_ai.py` 使用 `page/page_size`，返回 `total + items`。
- Web 端 `CasesView/OverviewView` 与小程序律师首页均直接请求 `/cases`，且默认不传分页参数。

## 4. 统一规范（目标口径）

## 4.1 标准分页参数
- `page`：页码，`>=1`，默认 `1`
- `page_size`：每页条数，`1..100`，默认 `20`

## 4.2 历史参数（兼容）
- `skip`：偏移量，`>=0`
- `limit`：条数，`1..100`

## 4.3 参数优先级与冲突规则
1. 仅传 `page/page_size`：按标准分页执行。
2. 仅传 `skip/limit`：按历史分页执行（兼容模式）。
3. 两组参数同时传入：
   - 若语义一致（`skip == (page-1)*page_size` 且 `limit == page_size`），允许通过。
   - 若不一致，返回 `400 VALIDATION_ERROR`（避免歧义）。

## 4.4 统一换算规则（内部）
- 标准入参转历史查询：
  - `skip = (page - 1) * page_size`
  - `limit = page_size`
- 历史入参转标准展示：
  - `page = floor(skip / limit) + 1`
  - `page_size = limit`

## 5. 接口级落地方案

## 5.1 `GET /api/v1/cases`
- 保持响应体：`list[CaseListItem]`（不改，确保前端无破坏）。
- 扩展支持：新增 `page/page_size` 入参（并保留 `skip/limit` 兼容）。
- 建议追加响应头（可选但推荐）：
  - `X-Page`
  - `X-Page-Size`
  - `X-Total-Count`
  - `X-Has-Next`

## 5.2 `GET /api/v1/ai/cases/{case_id}/facts`
- 继续以 `page/page_size` 为主规范。
- 可选兼容 `skip/limit`（若团队决定双端统一兼容层）；若不兼容，需在契约文档明确“仅支持标准参数”。

> 建议默认值：两端统一兼容，避免前端团队误用导致 400。

## 6. 兼容窗口与下线节奏
- 建议兼容窗口：`2026-03-19` 至 `2026-06-30`。
- 阶段 1（立即）：支持双参数并记录 `skip/limit` 使用日志。
- 阶段 2（窗口中）：前端改为仅发送 `page/page_size`。
- 阶段 3（窗口后）：`skip/limit` 标记废弃，进入下线评估（需发布说明）。

## 7. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A04-1 | 分页参数解析器（双参数兼容） | `backend/app/api/routes_cases.py`（或新建 pagination helper） | 统一解析函数 |
| A04-2 | `/cases` 路由接入 `page/page_size` | `backend/app/api/routes_cases.py` | 标准参数可用且兼容历史参数 |
| A04-3 | `/ai/.../facts` 兼容策略落地（可选） | `backend/app/api/routes_ai.py`、`services/ai.py`、`repositories/ai.py` | 双模式分页或明确拒绝策略 |
| A04-4 | 分页元信息响应头（可选） | `routes_cases.py` | 便于前端后续增量改造 |
| A04-5 | 测试补齐 | `backend/tests/` | 标准参数、历史参数、冲突参数、边界值测试 |
| A04-6 | 契约文档更新 | `docs/API-CONTRACTS.md`、`docs/AI-CURRENT-STATUS.md` | 分页规范与兼容窗口可查 |

## 8. 验收标准（DoD）

## 8.1 功能验收
- `/cases` 同时支持：
  - `?page=1&page_size=20`
  - `?skip=0&limit=20`
- 两组参数冲突时返回 `400 VALIDATION_ERROR`。
- 不传分页参数时行为与当前版本一致（默认取前 20 条）。

## 8.2 联调验收
- Web `CasesView` 不改代码可正常加载列表。
- Web `OverviewView` 不改代码可正常加载案件数（不出现报错）。
- 小程序 `pages/lawyer/home.vue` 不改代码可正常加载案件列表。

## 8.3 一致性验收
- 后端分页边界统一：`page>=1`、`1<=page_size<=100`、`skip>=0`、`1<=limit<=100`。
- 租户过滤、角色过滤逻辑在分页改造后保持不变。

## 9. 风险与默认策略
- 风险：若直接改 `/cases` 响应体为对象，会破坏现有 Web/小程序。  
  默认策略：本任务只统一“入参”，不改 `/cases` 响应体结构。
- 风险：双参数并存引起语义冲突。  
  默认策略：冲突时直接 `400`，避免静默误读。
- 风险：兼容窗口无限延长导致技术债积累。  
  默认策略：固定窗口到 `2026-06-30`，并通过日志追踪遗留调用。

## 10. 回滚策略
1. 保留 `skip/limit` 原实现路径，标准参数解析可通过开关临时关闭。
2. 若上线后出现大面积参数校验失败，先降级为“优先 `page/page_size`，忽略冲突校验”短期兜底。
3. 问题定位完成后恢复严格冲突校验。

## 11. 预估工作量
- 设计与评审：0.5 人日
- 后端实现与测试：1 人日
- 联调与文档同步：0.5 人日
- 合计：2 人日
