# BE-A07 执行单：租户隔离审计清单

## 1. 任务目标
- 建立“查询必须带 `tenant_id`”的后端审计基线，防止跨租户数据读取与写入。
- 形成可直接用于代码评审的检查清单，覆盖 route/service/repository/dependency/WS。
- 不改变既有业务接口契约，仅强化隔离审计规则与落地流程。

## 2. 范围
### 2.1 In Scope
- `backend/app/api` 全部路由（含 WS）。
- `backend/app/services` 与 `backend/app/repositories` 的租户边界检查。
- 认证依赖与会话租户上下文（`set_current_tenant_context`）使用规范。
- 审计用例与回归检查项。

### 2.2 Out of Scope
- 多数据库拆分或物理分库分表改造。
- 全量 RLS（Row Level Security）上线（本任务只定义方案与审计入口）。

## 3. 现状基线（代码事实）
- 多数 HTTP 路由已在查询条件中显式包含 `tenant_id`（`cases/files/users/notifications/stats/ai` 主链路）。
- `get_current_user` 会校验 JWT 中 `tenant_id` 与用户一致，并执行 `set_current_tenant_context(db, user.tenant_id)`。
- 关键风险点：
  - `WS /ws/ai/tasks/{task_id}` 当前无鉴权，且按 `task_id` 查询任务，未做租户隔离校验。
  - 大量业务仍在 route 层直接写查询，缺少统一“租户过滤必须项”约束。
  - `auth` 部分接口有跨租户查询（属业务允许场景），但未形成“允许跨租户”的显式标注机制。

## 4. 审计原则
- 默认原则：任何业务数据查询必须附带 `tenant_id` 条件。
- 例外原则：注册/登录/租户发现类接口可跨租户，但必须显式标注“跨租户白名单场景”。
- 写入原则：写入记录必须带 `tenant_id` 且来源于当前认证用户上下文，不接受客户端任意传入。
- WS 原则：与 HTTP 同级别租户隔离，不得因通道类型绕过鉴权。

## 5. 审计清单（代码评审可直接使用）

## 5.1 Route 层
- [ ] 每个受保护接口都通过 `get_current_user` 或更高权限依赖进入。
- [ ] 所有 `db.query(...).filter(...)` 包含 `tenant_id == current_user.tenant_id`。
- [ ] 若接口为跨租户白名单，已在注释和文档中明确“为何允许跨租户”。
- [ ] 禁止通过 path 参数直接拼租户边界（必须二次校验与 current_user 一致）。

## 5.2 Service 层
- [ ] `service` 接口签名包含 `current_user` 或显式租户上下文。
- [ ] 任何 `get_xxx_or_raise` 均做租户过滤 + 角色可见性校验。
- [ ] 跨租户调用必须经显式 `allow_cross_tenant` 入口（禁止隐式放开）。

## 5.3 Repository 层
- [ ] 查询方法签名必须带 `tenant_id`（确有例外需命名体现 `cross_tenant`）。
- [ ] `update/delete` 语句必须带 `tenant_id` 条件。
- [ ] 不允许 repository 自行决定租户来源（由上层传入）。

## 5.4 WS 与异步任务
- [ ] WS 握手必须鉴权并解析 `tenant_id`。
- [ ] WS 查询任务状态时必须校验 `task.tenant_id == token.tenant_id`。
- [ ] 队列 worker 更新任务时必须按 `tenant_id + task_id` 双条件定位。

## 5.5 数据库层（建议）
- [ ] PostgreSQL 可选开启 RLS，策略引用 `app.current_tenant`。
- [ ] 所有关键表预留 `tenant_id` 索引并纳入迁移审查。

## 6. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A07-1 | 全路由租户过滤审计 | `backend/app/api` | 接口级审计清单 |
| A07-2 | service/repository 签名审计 | `backend/app/services`、`backend/app/repositories` | 缺失 `tenant_id` 的方法清单 |
| A07-3 | WS 租户隔离补强 | `backend/app/api/routes_ws_ai.py` | 鉴权 + 任务归属校验 |
| A07-4 | 跨租户白名单机制 | `docs` + 代码注释规范 | 白名单接口表 |
| A07-5 | 自动化扫描脚本（可选） | `backend/scripts/` | grep/lint 规则草案 |
| A07-6 | 回归测试补齐 | `backend/tests/` | 越权访问与跨租户访问测试 |

## 7. 验收标准（DoD）
- 所有业务查询具备可追踪的租户边界校验。
- 跨租户访问仅出现在白名单接口，且有文档与测试覆盖。
- WS 与 AI 任务状态链路通过跨租户越权测试。
- 审计清单可用于 PR 审核并落地执行。

## 8. 风险与默认策略
- 风险：一次性全量整改回归面大。  
  默认策略：先高风险链路（WS/AI/Files/Cases）再扩展到边缘接口。
- 风险：历史接口混合写法导致漏审。  
  默认策略：引入“新增查询必须含 tenant_id”review gate。
- 风险：跨租户白名单口径不统一。  
  默认策略：白名单统一在 `docs` 维护，代码必须引用。

## 9. 回滚策略
1. 对新增强校验采用特性开关，出现误拦截可快速降级。
2. 保留请求日志中的 `request_id` 与用户租户信息，便于定位回滚范围。
3. 回滚仅放松新校验，不移除审计日志与文档机制。

## 10. 预估工作量
- 审计与评审：0.5 人日
- 修复与测试：1.5 人日
- 文档与规范固化：0.5 人日
- 合计：2.5 人日
