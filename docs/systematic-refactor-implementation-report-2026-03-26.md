# 系统化拆分与拆除实施报告（2026-03-26 持续更新）

## 1. 目标

- 按 `router -> service -> repository` 统一后端分层。
- 系统性拆除历史过渡实现，避免同职责多入口并存。
- 在不改变 API 契约和行为的前提下，持续降低巨型 service 风险。
- 每轮拆分后都保留可追溯验证记录与剩余待拆清单。

## 2. 执行原则

- 保持接口契约稳定，优先做内部收口而非行为改写。
- 优先抽高内聚子职责，避免并行引入新的抽象分叉。
- 能复用既有 service / repository 的地方不重复实现。
- 每一阶段都要求有定向回归，关键阶段补全量回归。

## 3. 当前结构结果

- 路由层显式 `db.query(...)` 已清零。
- 后端核心模块已大体统一到 `router -> service -> repository`。
- AI 模块已形成：
  - `query_service`
  - `budget_service`
  - `runtime_service`
  - `task_command_service`
  - `parse_service`
  - `analysis_service`
  - `falsification_service`
- `backend/app/modules/ai/service.py` 已由最初 `1401` 行收敛至 `102` 行。

## 4. 前置阶段摘要

本轮系统化拆分已先后完成以下主线工作：

- Files / Cases repository 首批落地并接入关键查询路径。
- Cases / Clients / Invites / Auth / Users / Tenants 服务层落地，历史路由收敛为轻入口。
- 微信登录链路已拆分为独立职责服务，短信、登录、刷新、登出已 service 化。
- 小程序原始 `error.message` 漏网点完成统一收口。
- Analytics / Notifications / AI WebSocket 已完成路由层瘦身。
- 路由层改造完成后，拆分重心转向 AI / Cases / Auth 等超大 service。

## 5. 阶段明细

### 5.14 Tenants 创建/加入/预算链路拆分（第八阶段）

处理：

- 新增 `backend/app/modules/tenants/repository.py`，承接：
  - 按 `tenant_code` / `tenant_id` 读取租户
  - 全量租户列表读取
  - 租户编码唯一性检测
  - 按手机号读取用户与租户内成员
  - 按租户读取案件
  - 租户/案件保存
- 新增 `backend/app/modules/tenants/service.py`，统一承接：
  - `/tenants/personal`
  - `/tenants/organization`
  - `/tenants/join`
  - `/tenants/invite/{tenant_code}`
  - `/tenants/{tenant_id}/preview`
  - `/tenants/current`
  - `/tenants`
  - `/tenants/current` 更新
  - `/tenants/{tenant_id}/status`
  - `/tenants/{tenant_id}/ai-budget`
  - `/tenants/{tenant_id}/cases/{case_id}/ai-budget`
- `backend/app/api/routes_tenants.py` 改为轻量入口层，仅负责依赖注入和委托 `TenantsService`。
- `/tenants/members/{id}/approve` 保持复用 `UsersService`，避免成员审批规则分叉。

收益：

- `tenants` 入口完成第一轮 `router -> service -> repository` 收口。
- AI 预算与租户状态流转的读写逻辑集中，后续补单测与调优更容易。

### 5.15 Analytics / Notifications / AI WebSocket 路由瘦身（第九阶段）

处理：

- 新增 `backend/app/modules/analytics/repository.py` 与 `service.py`，承接：
  - `/analytics/ai-usage`
  - `/analytics/prompts`
  - `/analytics/provider-settings`
  - `/stats/dashboard`
- 新增 `backend/app/modules/notifications/repository.py` 与 `service.py`，承接：
  - 通知列表
  - 未读过滤
  - 标记已读
- 新增 `backend/app/modules/ai/ws_service.py`，承接：
  - access token 会话校验
  - WebSocket viewer 身份解析
  - AI task 可见性校验
  - client 对案件归属校验
- `analytics/router.py`、`analytics/stats_router.py`、`notifications/router.py` 与 `ai/ws_router.py` 已改为轻量入口层。

收益：

- 路由层显式 `db.query(...)` 已清零。
- HTTP 与 WebSocket 入口都完成第一轮瘦身。
- 拆分焦点从“路由直查数据库”转入“超大 service 继续细分”。

### 5.16 AI Query Service 拆分（第十阶段）

问题：`backend/app/modules/ai/service.py` 在完成解析/分析/证伪第一次拆分后，仍混合保留了 5 类只读查询职责：

- `/ai/cases/{case_id}/facts`
- `/ai/cases/{case_id}/analysis-results`
- `/ai/cases/{case_id}/falsification-results`
- `/ai/tasks`
- `/ai/tasks/{task_id}`

处理：

- 新增 `backend/app/modules/ai/services/query_service.py`，统一承接：
  - 案件事实列表查询
  - 分析结果列表查询
  - 证伪结果列表查询
  - AI 任务列表查询
  - AI 任务状态查询
- `backend/app/modules/ai/service.py` 对上述 5 个只读方法全部改为委托 `query_service`。
- 读模型映射统一复用已有拆分模块：
  - `parse_service.to_case_fact_read`
  - `analysis_service.to_analysis_result_read`
  - `falsification_service.to_falsification_read`

收益：

- AI 主 service 收敛到“写路径 + 编排 + worker/runtime”职责。
- 查询权限、分页、摘要聚合与 read model 映射集中，后续更容易补 mock repository 单测。
- `backend/app/modules/ai/service.py` 从 `1401` 行下降到 `1174` 行。

### 5.17 AI Budget / Runtime / Task Command Service 拆分（第十一阶段）

问题：完成 query service 下沉后，`backend/app/modules/ai/service.py` 仍同时承担了 3 类偏底层职责：

- 预算与独户律师 AI 可用性判断
- 任务运行时状态机（processing / failed / retrying / dead-letter / stale recovery）
- 任务命令侧逻辑（retry / idempotency / create-or-reuse）

处理：

- 新增 `backend/app/modules/ai/services/budget_service.py`，统一承接：
  - 个人租户 AI 可用性校验
  - analyze 预算熔断 / 降级模型策略
  - 金额解析与月窗口辅助函数
- 新增 `backend/app/modules/ai/services/runtime_service.py`，统一承接：
  - processing / failed 状态推进
  - queue attempt 与 worker id 解析
  - stale processing task 恢复
  - retry / dead-letter 运行时收口
- 新增 `backend/app/modules/ai/services/task_command_service.py`，统一承接：
  - `retry_task`
  - `_create_or_reuse_task`
  - `Idempotency-Key` 规范化与冲突校验
- `backend/app/modules/ai/repository.py` 新增 `get_tenant(...)`，避免预算逻辑继续直接访问 `Tenant` 查询。
- `backend/app/modules/ai/service.py` 对以下方法已改为薄委托：
  - `retry_task`
  - `_create_or_reuse_task`
  - `_normalize_idempotency_key`
  - `_recover_stale_processing_tasks`
  - `_apply_retry_or_dead_letter`
  - `_mark_processing`
  - `_mark_failed`
  - `_get_queue_attempt`
  - `_effective_worker_id`
  - `_resolve_budget_policy_for_analysis`
  - `_to_decimal_or_none`
  - `_month_window`
  - `_ensure_personal_tenant_ai_access`

收益：

- `AIService` 已明显收敛为“入口写路径 + queue driver 决策 + worker task 编排”主体。
- 预算规则、状态机、重试与幂等规范都有了独立落点。
- `backend/app/modules/ai/service.py` 从 `1174` 行继续下降到 `796` 行；相较最初 `1401` 行，累计净减少 `605` 行。

### 5.18 AI Worker Dispatch / Task Processor 拆分（第十二阶段）

问题：在第十一阶段后，`backend/app/modules/ai/service.py` 剩余最大的两块高耦合逻辑变成了：

- queue dispatch / background dispatch / db queue consume
- `_process_task_by_id` 及 task-type 分发

这两块职责本质上已经偏向 worker runtime，而不应继续和主 service 的入口编排混在一起。

处理：

- 新增 `backend/app/modules/ai/services/worker_dispatch_service.py`，统一承接：
  - queue driver 判断
  - inline / eager background 策略判断
  - background thread 启动
  - task enqueue / dispatch
  - `consume_queued_tasks_once`
  - `consume_one_queued_task`
- 新增 `backend/app/modules/ai/services/task_processor_service.py`，统一承接：
  - worker session 生命周期
  - `task_id -> task/case/user` 解析
  - `parse / analyze / falsify` 三类任务分发
  - worker 侧失败分支收口
- `backend/app/modules/ai/service.py` 对以下方法已改为薄委托：
  - `_is_db_queue_driver`
  - `_should_run_inline`
  - `_should_run_eager_in_background`
  - `_start_background_task`
  - `_schedule_task_execution`
  - `_run_task_in_background`
  - `consume_queued_tasks_once`
  - `consume_one_queued_task`
  - `_process_task_by_id`
- 本轮修正了 worker 拆分过程中的一个回归：`worker_dispatch_service` 误调用不存在的 `_now_utc()`，已改回显式 UTC 时间，回归已通过。

收益：

- `AIService` 已从“主入口 + worker dispatch + task processor + budget/runtime/query”进一步收敛为“薄门面 + 编排协调层”。
- worker 调度与任务处理路径有了稳定落点，便于后续单独补测试或继续抽公共 worker 上下文。
- `backend/app/modules/ai/service.py` 从 `796` 行进一步下降到 `634` 行；相较最初 `1401` 行，累计净减少 `767` 行。

### 5.19 AI Submission Service 拆分（第十三阶段）

问题：完成 worker dispatch / task processor 拆分后，`backend/app/modules/ai/service.py` 入口侧仍保留了 3 个较长的提交编排方法：

- `start_parse_document`
- `start_analysis`
- `start_falsification`

这些方法本质上属于“提交命令入口编排”，和主 service 里剩余的 access / flow helper / context helper 已经不是同一层职责。

处理：

- 新增 `backend/app/modules/ai/services/submission_service.py`，统一承接：
  - 文档解析任务创建
  - 法律分析任务创建
  - 证伪任务创建
- `backend/app/modules/ai/service.py` 的三个 `start_*` 方法已全部改为薄委托。
- `submission_service.py` 继续复用既有下沉能力：
  - `task_command_service`
  - `budget_service`
  - `query/runtime/worker` 相关主 service 门面
- 顺手清理了主 service 中已失效的 `_AUTO_REANALYZE_IDEMPOTENCY_PREFIX` 常量残留。

收益：

- `AIService` 进一步收敛为真正的协调门面层。
- “提交入口编排” 与 “worker/runtime” 分离后，AI 模块内部边界更清晰：
  - `submission_service`
  - `query_service`
  - `task_command_service`
  - `budget_service`
  - `runtime_service`
  - `worker_dispatch_service`
  - `task_processor_service`
  - `parse/analysis/falsification_service`
- `backend/app/modules/ai/service.py` 从 `634` 行进一步下降到 `528` 行；相较最初 `1401` 行，累计净减少 `873` 行。

### 5.20 AI Access / Flow / Context Helper 拆分（第十四阶段）

问题：第十三阶段后，`backend/app/modules/ai/service.py` 虽然已经降到 `528` 行，但仍混合保留了三类 helper：

- access / role / visibility gate
- case flow / analysis state 更新
- case context / masking 辅助

这些 helper 被多个 AI 子服务复用，但继续堆在主 service 中，会让 `AIService` 难以进一步稳定在轻量门面形态。

处理：

- 新增 `backend/app/modules/ai/services/access_service.py`，统一承接：
  - `get_case_or_raise`
  - `ensure_role_for_action`
- 新增 `backend/app/modules/ai/services/flow_service.py`，统一承接：
  - `sync_case_analysis_state`
  - `append_case_flow`
- 新增 `backend/app/modules/ai/services/context_service.py`，统一承接：
  - `build_case_context`
  - `build_case_context_notes`
  - `sanitize_case_context_text`
  - `mask_sensitive`
- `backend/app/modules/ai/service.py` 对以上 helper 已全部改为薄委托。

阶段回顾：

- 编译检查通过。
- AI 定向回归 `34 passed`。
- helper 下沉后，`AIService` 从 `528` 行继续下降到 `450` 行。

收益：

- `AIService` 已基本达到“协调门面层”目标，剩余大多是对已拆服务的委托方法。
- access / flow / context 三类 helper 有了明确落点，后续可独立补测试。
- 相较最初 `1401` 行，AI 主 service 累计净减少 `951` 行。

### 5.21 Cases Report / Helper 拆分（第十五阶段）

问题：

- `backend/app/modules/cases/service.py` 在进入 Cases 模块拆分前仍承担了两类高耦合职责：
  - 报告版本枚举、生成、下载、访问链接拼装
  - 案件访问/编辑/备注/状态流转等通用 helper
- 报告逻辑同时依赖 `storage`、`report`、`files`、`timeline`、`analysis` 聚合查询，继续堆在 `CaseService` 中会让后续按业务切片拆分非常困难。

处理：

- 新增 `backend/app/modules/cases/helpers.py`，统一收口通用 helper：
  - `get_case_or_404`
  - `ensure_case_client_owner`
  - `ensure_case_editor`
  - `append_client_remark`
  - `serialize_case_for_viewer`
  - `validate_status_transition`
- 新增 `backend/app/modules/cases/report_service.py`，承接：
  - 报告版本列表
  - 最新/历史报告访问链接
  - 最新/历史报告下载
  - 报告 payload 构建与持久化
- `backend/app/modules/cases/service.py` 已完成两类收口：
  - 原报告相关 public 方法全部改为委托 `CaseReportService`
  - 原 service 内对通用 helper 的直接私有调用全部改为调用 `helpers.py`
- 同步补上 `CaseService.__init__` 的 `self.report_service = CaseReportService(db)`，修复上一个半拆分状态留下的委托缺口。

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/cases/service.py` 已降到 `353` 行，报告相关聚合复杂度从主 service 中移出。
- `backend/app/modules/cases/report_service.py` 成为报告域稳定落点，后续可继续围绕 report/version/download 方向独立补测试。
- Cases 模块已经形成更清晰的三层结构：
  - `service.py`：案件主编排入口
  - `helpers.py`：访问控制与展示辅助
  - `report_service.py`：报告子域
- 这一步完成后，Cases 模块下一轮可优先继续拆：
  - 案件更新/指派
  - 备注与案件时间线写入
  - 邀请码/邀请链路

### 5.22 Cases Remark Service 拆分（第十六阶段）

问题：

- 在完成报告域拆分后，`backend/app/modules/cases/service.py` 中仍有两段明显的“备注写入 + flow 记录”逻辑：
  - `update_client_remark`
  - `update_lawyer_remark`
- 这两段逻辑共享同一类职责边界：鉴权、备注更新、写入案件流转记录、刷新返回 DTO，继续留在主 service 中会妨碍 Cases 第二轮收口。

处理：

- 新增 `backend/app/modules/cases/remark_service.py`，统一承接：
  - 当事人补充说明更新
  - 律师内部备注更新
- `backend/app/modules/cases/service.py`：
  - 新增 `self.remark_service = CaseRemarkService(db)`
  - `update_client_remark`
  - `update_lawyer_remark`
  均已改为薄委托
- 顺手清理了 `CaseService` 中已不再需要的 import，保持主 service 只保留仍直接参与的入口依赖。

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/cases/service.py` 进一步从 `353` 行下降到 `325` 行。
- `remark_service.py` 为备注写入域提供了稳定落点，后续若继续抽 `flow append` 或补 mock 测试，边界更清晰。
- Cases 主 service 现在剩余的主要写入职责已进一步集中为：
  - create
  - update / assignment
  - invite / qrcode

### 5.23 Cases Command Service 拆分（第十七阶段）

问题：

- 在报告域与备注域拆分完成后，`backend/app/modules/cases/service.py` 里剩余最大的一块仍是写命令入口：
  - `create_case`
  - `update_case`
  - `get_case_invite_qrcode`
- 这三类逻辑都属于“命令执行 / 管理操作”边界，继续留在主 service 中会让 `CaseService` 无法真正收敛成查询+委托门面。

处理：

- 新增 `backend/app/modules/cases/command_service.py`，统一承接：
  - 案件创建
  - 案件更新 / 指派
  - 邀请二维码生成
- `backend/app/modules/cases/service.py`：
  - 新增 `self.command_service = CaseCommandService(db)`
  - `create_case`
  - `update_case`
  - `get_case_invite_qrcode`
  均已改为薄委托
- 顺手回补了 `Case` 类型 import，避免后续类型反射或静态检查阶段出现隐性缺口。

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/cases/service.py` 从 `325` 行进一步下降到 `195` 行，已经完成从“巨石 service”向“门面 service”的收口。
- Cases 模块当前的职责落点已经比较清晰：
  - `service.py`：查询 + 子服务委托入口
  - `command_service.py`：命令写操作
  - `remark_service.py`：备注写操作
  - `report_service.py`：报告子域
  - `helpers.py`：共享 helper
- Cases 模块主 service 已不再是当前系统化拆分的最高优先级，后续更值得转向 `auth / files / ai / tenants / analytics` 等仍高于 `300` 行的 service。

### 5.24 Auth Account Primitive 拆分（第十八阶段）

问题：

- `backend/app/modules/auth/service.py` 在 `AuthService` 类定义之前，仍堆积了一整批账户原语函数：
  - `authenticate_user`
  - `create_user`
  - `issue_session_bound_access_token`
  - `generate_system_password`
  - `mark_user_logged_in`
  - `set_user_password`
  - `change_user_password`
  - `register_user_from_invite`
  - `resolve_tenant_for_registration`
- 这些函数虽然职责清晰，但继续与 `AuthService` 混放，会让 `auth/service.py` 文件体积虚高，并增加后续继续拆 `AuthService` 本体时的阅读负担。

处理：

- 新增 `backend/app/modules/auth/account_service.py`，统一承接上述账户原语函数。
- `backend/app/modules/auth/service.py` 保留同名导出：
  - 通过 `_account_service` 重新绑定，保持外部 import 路径兼容
  - `AuthService` 内部原有调用点不需要改动
- 这样既完成物理拆分，又不影响现有测试、模块依赖和调用方代码。

阶段回顾：

- `python -m compileall backend/app/modules/auth` 通过。
- Auth 定向回归：
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
  - `backend/tests/test_auth_wechat_mini.py` → `14 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/auth/service.py` 从 `639` 行下降到 `427` 行。
- `backend/app/modules/auth/account_service.py` 成为账户创建、密码变更、邀请注册、会话绑定 token 等基础原语的稳定落点。
- `AuthService` 后续可更聚焦于：
  - login context
  - sms / login 编排
  - tenant / invite 绑定

### 5.25 Auth Login Service 拆分（第十九阶段）

问题：

- 在账户原语拆分完成后，`backend/app/modules/auth/service.py` 中剩余最重的一簇是登录上下文与登录编排逻辑：
  - `resolve_login_context`
  - `apply_case_invite_binding`
  - `_resolve_sms_login_user`
  - `login_by_sms_code`
  - `login`
- 这批逻辑同时涉及：
  - tenant / invite 解析
  - case invite 绑定
  - SMS 登录编排
  - 密码登录编排
  与 `AuthService` 中剩余的 SMS request-context、注册、密码变更等职责边界已经明显不同。

处理：

- 新增 `backend/app/modules/auth/services/login_service.py`，统一承接：
  - 登录上下文解析
  - 案件邀请绑定
  - SMS 登录用户解析
  - SMS / 密码登录编排
- `backend/app/modules/auth/service.py`：
  - 新增 `self.login_service = AuthLoginService(...)`
  - 对 `_resolve_login_tenant`
  - `_resolve_case_invite_context_for_login`
  - `resolve_login_context`
  - `apply_case_invite_binding`
  - `_resolve_sms_login_user`
  - `login_by_sms_code`
  - `login`
  均已改为薄委托
- `backend/app/modules/auth/services/__init__.py` 已同步导出 `AuthLoginService`。

阶段回顾：

- `python -m compileall backend/app/modules/auth` 通过。
- Auth 定向回归：
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
  - `backend/tests/test_auth_wechat_mini.py` → `14 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/auth/service.py` 从 `427` 行继续下降到 `309` 行。
- `backend/app/modules/auth/services/login_service.py` 成为登录上下文与登录编排的稳定落点。
- `AuthService` 已经接近“门面 + 少量注册/SMS helper”的状态，下一刀若继续做，可优先考虑：
  - SMS request context / send / verify
  - register_user
  - `ensure_user_can_login` 等共享 helper 的独立落点

### 5.26 Auth SMS Service 拆分（第二十阶段）

问题：

- 在登录编排拆分完成后，`backend/app/modules/auth/service.py` 里剩余最明显的一簇是 SMS 请求上下文和发码/验码逻辑：
  - `_resolve_client_ip`
  - `_build_sms_request_context`
  - `send_phone_sms`
  - `verify_phone_sms`
- 这部分逻辑与 `AuthService` 中其余注册/密码变更职责边界已经分离，同时它还服务于 `login_service` 的 SMS 登录链路，适合独立成公共子服务。

处理：

- 新增 `backend/app/modules/auth/services/sms_auth_service.py`，统一承接：
  - client IP 解析
  - SMS request context 构建
  - SMS 发送
  - SMS 验证
- `backend/app/modules/auth/service.py`：
  - 新增 `self.sms_auth_service = AuthSmsService(db)`
  - `_resolve_client_ip`
  - `_build_sms_request_context`
  - `send_phone_sms`
  - `verify_phone_sms`
  均已改为薄委托
- `backend/app/modules/auth/services/__init__.py` 已同步导出 `AuthSmsService`。

阶段回顾：

- `python -m compileall backend/app/modules/auth` 通过。
- Auth 定向回归：
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
  - `backend/tests/test_auth_wechat_mini.py` → `14 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/auth/service.py` 从 `309` 行进一步下降到 `229` 行，已经完全脱离“大 service”名单。
- `backend/app/modules/auth/services/sms_auth_service.py` 成为 SMS request-context 与验证码链路的稳定落点。
- Auth 模块当前职责分布已明显清晰：
  - `service.py`：门面 + 少量注册/密码变更入口
  - `account_service.py`：账户原语
  - `services/login_service.py`：登录上下文与登录编排
  - `services/sms_auth_service.py`：SMS 子域

### 5.27 Files Access Token Service 拆分（第二十一阶段）

问题：

- `backend/app/modules/files/service.py` 里混合了三类职责：
  - 上传校验与落盘
  - 存储对象操作
  - 访问授权 token（文件访问 grant + 直传 completion token）
- 其中访问授权 token 子域与上传/存储逻辑耦合较低，优先拆出风险最小。

处理：

- 新增 `backend/app/modules/files/access_service.py`，承接：
  - `create_file_access_grant`
  - `consume_file_access_grant`
  - `create_direct_upload_completion_token`
  - `decode_direct_upload_completion_token`
- `backend/app/modules/files/service.py` 保留同名导出，通过模块别名转发，保持 router / tests 调用路径不变。

阶段回顾：

- `python -m compileall backend/app/modules/files` 通过。
- Files 定向回归：
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
- 后端全量回归：`218 passed`。

收益：

- Files 访问授权链路有了稳定落点，便于后续补粒度更细的授权测试。
- 为下一步继续拆上传子域清理了 `files/service.py` 的混合职责边界。

### 5.28 Files Upload Service 拆分（第二十二阶段）

问题：

- 第二十一阶段后，`backend/app/modules/files/service.py` 仍保留大块上传逻辑：
  - 文件名/MIME 校验
  - 上传流写入与临时文件处理
  - 上传后对象落盘与 `File` 记录写入
- 继续留在主 service 会让 Files 模块主入口难以收敛为“门面 + 存储操作”。

处理：

- 新增 `backend/app/modules/files/upload_service.py`，整体承接上传链路：
  - `prepare_upload_file_metadata`
  - `validate_upload_policy_request`
  - `validate_upload_size_bytes`
  - `save_upload_file`
  - `create_stored_file_record`
  以及必要的内部 helper
- `backend/app/modules/files/service.py` 改为门面导出，上述方法通过别名转发，保持外部调用路径兼容。

阶段回顾：

- `python -m compileall backend/app/modules/files` 通过。
- Files 定向回归：
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/files/service.py` 从 `356` 行降到 `50` 行，完成门面化收口。
- 上传链路成为可独立演进的子服务，为后续细分“校验策略”与“上传执行”打下结构基础。

### 5.29 Files Upload Policy Service 拆分（第二十三阶段）

问题：

- 在第二十二阶段后，`backend/app/modules/files/upload_service.py` 仍含大量“上传策略校验”逻辑（文件名规则、扩展名白名单、MIME 黑白名单、扩展名与 MIME 交叉校验）。
- 这部分策略逻辑和上传执行（写流/临时文件/存储写入）是两个不同职责，继续混放会影响后续维护。

处理：

- 新增 `backend/app/modules/files/upload_policy_service.py`，承接：
  - 文件名校验
  - 文件类型与 MIME 校验
  - 上传策略校验
  - 上传大小校验
- `backend/app/modules/files/upload_service.py` 改为复用该策略模块并保留兼容导出。

阶段回顾：

- `python -m compileall backend/app/modules/files` 通过。
- Files 定向回归：
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/files/upload_service.py` 从 `319` 行降到 `169` 行。
- Files 上传链路已经形成清晰分层：
  - `service.py`：门面导出
  - `access_service.py`：访问授权 token
  - `upload_service.py`：上传执行
  - `upload_policy_service.py`：上传策略
- Files 模块已完全脱离“>300 行大 service”名单。

### 5.30 Cases Report Payload Service 拆分（第二十四阶段）

问题：

- `backend/app/modules/cases/report_service.py` 仍混合“报告对象管理”与“报告 payload 构建”两类职责。
- 其中 payload 构建涉及跨模块聚合：
  - timeline
  - files
  - analysis results
  继续放在 `report_service.py` 中会让报告子域难以继续细分。

处理：

- 新增 `backend/app/modules/cases/report_payload_service.py`，承接：
  - `build_case_report_payload`
- `backend/app/modules/cases/report_service.py`：
  - 报告生成链路改为调用 `build_case_report_payload(...)`
  - 删除原内联 payload 构建实现
  - 清理不再使用的 import

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/cases/report_service.py` 从 `399` 行下降到 `339` 行。
- 报告 payload 聚合逻辑有了明确落点，后续可独立补测试或继续拆分报告下载/版本管理逻辑。

### 5.31 Cases Report Access Service 拆分（第二十五阶段）

问题：

- 第二十四阶段后，`backend/app/modules/cases/report_service.py` 仍保留“报告访问 URL 组装 + 下载响应构建”子域逻辑。
- 这部分与报告版本管理/持久化职责不同，适合进一步独立，降低 `report_service.py` 的混合复杂度。

处理：

- 新增 `backend/app/modules/cases/report_access_service.py`，承接：
  - `build_case_report_access_url`
  - `render_case_report_response`
- `backend/app/modules/cases/report_service.py`：
  - 报告访问链接返回改为调用 `build_case_report_access_url(...)`
  - 报告下载返回改为调用 `render_case_report_response(...)`
  - 删除原内联实现

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/cases/report_service.py` 从 `339` 行继续下降到 `300` 行。
- Cases 报告子域分层进一步明确：
  - `report_service.py`：主编排
  - `report_payload_service.py`：payload 聚合
  - `report_access_service.py`：访问/下载
- `report_service.py` 已降到临界体积，后续拆分优先级可下调。

### 5.32 Auth WeChat Binding Service 拆分（第二十六阶段）

问题：

- `backend/app/modules/auth/wechat_service.py` 在上一轮仅完成 `wx_mini_phone_login` 委托，`wx_mini_bind_existing` 与 `wx_mini_bind` 仍保留在主 service 中。
- 这会导致 Auth WeChat 子域“拆分结构已建立但职责尚未彻底迁移”，影响后续继续细分与维护定位。

处理：

- `backend/app/modules/auth/wechat_service.py`：
  - `wx_mini_bind_existing(...)` 改为委托 `self.binding_service.wx_mini_bind_existing(...)`
  - `wx_mini_bind(...)` 改为委托 `self.binding_service.wx_mini_bind(...)`
  - 清理不再使用的 `UserStatus` import
- `backend/app/modules/auth/services/wechat_binding_service.py`：
  - 为避免 `auth.service` ↔ `wechat_binding_service` 循环依赖，将 `authenticate_user / create_user / generate_system_password` 改为方法内延迟导入。

阶段回顾：

- `python -m compileall backend/app/modules/auth` 通过。
- Auth 定向回归：
  - `backend/tests/test_auth_wechat_mini.py` → `14 passed`
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/auth/wechat_service.py` 从 `449` 行下降到 `204` 行。
- WeChat 绑定逻辑已集中到 `backend/app/modules/auth/services/wechat_binding_service.py`，主 service 回归门面编排角色。
- Auth WeChat 子域拆分从“半完成”收口为“职责完成迁移”状态。

### 5.33 Auth WeChat Account Binding 子服务拆分（第二十七阶段）

问题：

- 第二十六阶段后，`backend/app/modules/auth/services/wechat_binding_service.py` 仍承载“手机登录绑定 + 已有账号绑定 + 旧版绑定”三类流程，文件体量达到 `359` 行。
- 其中“已有账号绑定/旧版绑定”与“手机登录绑定”属于不同子域，继续堆叠会增加后续维护与回归成本。

处理：

- 新增 `backend/app/modules/auth/services/wechat_account_binding_service.py`，承接：
  - `wx_mini_bind_existing(...)`
  - `wx_mini_bind(...)`
- `backend/app/modules/auth/services/wechat_binding_service.py`：
  - 保留 `wx_mini_phone_login(...)` 主流程
  - 新增 `self.account_binding_service`
  - `wx_mini_bind_existing(...)` / `wx_mini_bind(...)` 改为委托子服务
- `backend/app/modules/auth/services/__init__.py`：
  - 新增 `WechatAccountBindingService` 导出，保持 services 出口一致。

阶段回顾：

- `python -m compileall backend/app/modules/auth` 通过。
- Auth 定向回归：
  - `backend/tests/test_auth_wechat_mini.py` → `14 passed`
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/auth/services/wechat_binding_service.py` 从 `359` 行下降到 `227` 行。
- 新增 `backend/app/modules/auth/services/wechat_account_binding_service.py`（`215` 行）承接账号绑定子域。
- Auth WeChat 绑定链路形成更清晰分层：
  - `wechat_binding_service.py`：手机登录绑定编排
  - `wechat_account_binding_service.py`：已有账号绑定 / 旧版绑定

### 5.34 Analytics Dashboard Service 拆分（第二十八阶段）

问题：

- `backend/app/modules/analytics/service.py` 在汇总 AI 用量、Provider 配置之外，还内嵌了 Dashboard 指标统计与登录增量计算逻辑，职责混合且文件体量为 `347` 行。
- Dashboard 统计涉及可见案件/文件查询与增量规则，独立性较高，适合下沉为子服务。

处理：

- 新增 `backend/app/modules/analytics/dashboard_service.py`，承接：
  - `_count_dashboard_deltas(...)`
  - `get_dashboard_stats(...)`
- `backend/app/modules/analytics/service.py`：
  - 构造函数新增 `self.dashboard_service = AnalyticsDashboardService(self.repository)`
  - `get_dashboard_stats(...)` 改为委托 `self.dashboard_service.get_dashboard_stats(...)`
  - 清理不再需要的 dashboard 相关 import

阶段回顾：

- `python -m compileall backend/app/modules/analytics` 通过。
- Analytics 定向回归：
  - `backend/tests/test_analytics_api.py` → `2 passed`
  - `backend/tests/test_dashboard_stats.py` → `2 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/analytics/service.py` 从 `347` 行下降到 `266` 行。
- Analytics 形成更清晰分层：
  - `service.py`：AI 用量与配置管理
  - `dashboard_service.py`：Dashboard 指标与登录增量统计
- 模块层 `>300` 大 service 数量继续下降。

### 5.35 Tenants Budget Service 拆分（第二十九阶段）

问题：

- `backend/app/modules/tenants/service.py` 同时承载租户创建/加入、租户状态管理、租户与案件 AI 预算管理，文件体量为 `335` 行。
- 其中预算读写逻辑可独立下沉，减少主 service 的职责耦合。

处理：

- 新增 `backend/app/modules/tenants/tenants_budget_service.py`，承接：
  - `get_tenant_ai_budget(...)`
  - `update_tenant_ai_budget(...)`
  - `get_case_ai_budget(...)`
  - `update_case_ai_budget(...)`
- `backend/app/modules/tenants/service.py`：
  - 构造函数新增 `self.budget_service = TenantsBudgetService(...)`
  - 上述四个预算方法改为委托 `budget_service`
  - 主 service 保留租户生命周期与状态管理主编排

阶段回顾：

- `python -m compileall backend/app/modules/tenants` 通过。
- Tenants 定向回归：
  - `backend/tests/test_tenants_api.py` → `3 passed`
  - `backend/tests/test_ai_queue_and_budget.py` → `7 passed`
  - `backend/tests/test_personal_tenant_lawyer_access.py` → `2 passed`
  - `backend/tests/test_status_and_role_transitions.py` → `3 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/tenants/service.py` 从 `335` 行下降到 `295` 行。
- Tenants 预算子域有了独立落点：`tenants_budget_service.py`（`108` 行）。
- 模块层 `>300` 大 service 数量继续收敛。

### 5.36 AI Analysis Result Mapper 拆分（第三十阶段）

问题：

- `backend/app/modules/ai/services/analysis_service.py` 仍混合“分析执行逻辑”与“结果 DTO 映射逻辑”，文件体量为 `311` 行。
- `to_analysis_result_read(...)` 属于输出映射职责，适合独立，降低分析执行模块体积。

处理：

- 新增 `backend/app/modules/ai/services/analysis_result_mapper.py`，承接：
  - `to_analysis_result_read(...)`
- `backend/app/modules/ai/services/query_service.py`：
  - 结果映射 import 改为 `analysis_result_mapper`
- `backend/app/modules/ai/services/analysis_service.py`：
  - 移除内联 `to_analysis_result_read(...)` 实现与对应 schema import

阶段回顾：

- `python -m compileall backend/app/modules/ai` 通过。
- AI 定向回归：
  - `backend/tests/test_ai_api.py` → `13 passed`
  - `backend/tests/test_ai_queue_and_budget.py` → `7 passed`
  - `backend/tests/test_ai_idempotency.py` → `4 passed`
  - `backend/tests/test_ai_remark_context.py` → `2 passed`
  - `backend/tests/test_ai_ws.py` → `8 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/ai/services/analysis_service.py` 从 `311` 行下降到 `282` 行。
- AI 分析子域职责更清晰：
  - `analysis_service.py`：分析执行与结果持久化
  - `analysis_result_mapper.py`：分析结果 DTO 映射
- 模块层 `>300` 大 service / subservice 进一步减少。

### 5.37 AIService 门面别名化收敛（第三十一阶段）

问题：

- `backend/app/modules/ai/service.py` 仍有大量“单行转发方法”，职责上已是门面，但代码体量仍达 `510` 行，维护噪声较高。
- 这些方法主要是将调用透传到 `services/*`，可通过类级别函数别名收敛，保留行为与调用契约。

处理：

- `backend/app/modules/ai/service.py`：
  - 保留构造函数（持有 `db/repo/provider/request_id/session_factory/worker_id`）
  - 将 `start_* / list_* / retry_*` 与全部 `_...` helper 转为类级别函数别名（`module.func` / `staticmethod(...)` / `classmethod(...)`）
  - 去除重复的转发方法定义，保持对外 API 不变
- 此次未改动业务逻辑路径，仅做门面层结构压缩。

阶段回顾：

- `python -m compileall backend/app/modules/ai` 通过。
- AI 定向回归：
  - `backend/tests/test_ai_api.py` → `13 passed`
  - `backend/tests/test_ai_queue_and_budget.py` → `7 passed`
  - `backend/tests/test_ai_idempotency.py` → `4 passed`
  - `backend/tests/test_ai_remark_context.py` → `2 passed`
  - `backend/tests/test_ai_ws.py` → `8 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/modules/ai/service.py` 从 `510` 行下降到 `102` 行。
- AIService 彻底回归“门面 + 依赖持有者”角色，转发样板显著减少。
- 模块层 `>300` 大 service / subservice 清零。

### 5.38 Storage Integration 分层拆分（第三十二阶段）

问题：

- `backend/app/integrations/storage/service.py` 同时承载通用模型、本地后端、COS SDK client、COS 后端逻辑，体量为 `599` 行。
- 该结构将“存储模型定义”和“后端实现细节”耦合在同一文件中，不利于继续演进或单独测试。

处理：

- 新增 `backend/app/integrations/storage/base.py`，下沉：
  - `storage_error(...)`
  - `UploadPolicy`
  - `StorageObjectInfo`
  - `BaseStorageBackend`
- 新增 `backend/app/integrations/storage/local_backend.py`，下沉：
  - `LocalStorageBackend`
- 新增 `backend/app/integrations/storage/cos_client.py`，下沉：
  - `TencentCOSClient`
  - `create_cos_client(...)`
- `backend/app/integrations/storage/service.py`：
  - 保留 `COSStorageBackend` 与 `get_storage_backend(...)`
  - 通过 import 复用并保持历史导出名（含 `_create_cos_client`）可用，兼容现有调用与测试 monkeypatch。

阶段回顾：

- `python -m compileall backend/app/integrations/storage` 通过。
- Storage 定向回归：
  - `backend/tests/test_storage_backends.py` → `11 passed`
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
  - `backend/tests/test_case_flow_and_file_visibility.py` → `11 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/integrations/storage/service.py` 从 `599` 行下降到 `239` 行。
- Storage 集成形成清晰分层：
  - `base.py`：通用模型与基类
  - `local_backend.py`：本地后端
  - `cos_client.py`：COS SDK 适配
  - `service.py`：COS 后端与统一入口
- integrations 大文件清单进一步收敛。

### 5.39 SMS Integration 限流子域拆分（第三十三阶段）

问题：

- `backend/app/integrations/sms/service.py` 同时承载发送/校验主流程与限流/审计细节，文件体量为 `471` 行。
- 限流窗口、审计记录和错误构建逻辑可独立为子域，主流程应聚焦 send/verify/assert 业务路径。

处理：

- 新增 `backend/app/integrations/sms/guard_service.py`，下沉：
  - `SmsRequestContext`
  - 限流常量与窗口配置
  - `utc_now / as_utc`
  - `build_rate_limit_error / build_verify_locked_error`
  - `record_sms_audit / enforce_request_rate_limits`
- 重写 `backend/app/integrations/sms/service.py`：
  - 保留 `send_sms_code(...)`、`verify_sms_code(...)`、`assert_phone_verified(...)`
  - 通过 import 复用 `guard_service` 逻辑并保持对外导出兼容（含 `SmsRequestContext` 与常量）

阶段回顾：

- `python -m compileall backend/app/integrations/sms backend/app/modules/auth` 通过。
- SMS/Auth 定向回归：
  - `backend/tests/test_auth_sms_and_invite_flow.py` → `26 passed`
  - `backend/tests/test_auth_refresh_logout.py` → `10 passed`
  - `backend/tests/test_error_codes.py` → `10 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/integrations/sms/service.py` 从 `471` 行下降到 `262` 行。
- SMS 集成形成分层：
  - `guard_service.py`：限流与审计子域
  - `service.py`：发送/校验主流程
- integrations 层 `>300` 大 service 候选进一步减少。

### 5.40 LLM Integration Payload/Config Helper 拆分（第三十四阶段）

问题：

- `backend/app/integrations/llm/service.py` 在 provider 主流程之外，仍混合了 payload 解析、错误摘要与配置校验细节，体量为 `356` 行。
- 这些 helper 逻辑具有独立性，适合下沉以降低主 provider 类复杂度。

处理：

- 新增 `backend/app/integrations/llm/payload_utils.py`，下沉：
  - `parse_json_payload(...)`
  - `extract_provider_error(...)`
  - `summarize_provider_error(...)`
  - `summarize_provider_payload(...)`
  - `ensure_provider_configured(...)`
- `backend/app/integrations/llm/service.py`：
  - `_chat_json(...)` 改为调用 `payload_utils` helper
  - `generate_parse_facts / generate_analysis / generate_falsification` 改为调用 `ensure_provider_configured(...)`
  - 移除类内重复 helper 实现

阶段回顾：

- `python -m compileall backend/app/integrations/llm backend/app/modules/ai` 通过。
- LLM/AI 定向回归：
  - `backend/tests/test_openai_compatible_logging.py` → `2 passed`
  - `backend/tests/test_runtime_config_guards.py` → `10 passed`
  - `backend/tests/test_ai_api.py` + `backend/tests/test_ai_remark_context.py` → `15 passed`
- 后端全量回归：`218 passed`。

收益：

- `backend/app/integrations/llm/service.py` 从 `356` 行下降到 `283` 行。
- LLM 集成形成清晰分层：
  - `service.py`：provider 请求编排
  - `payload_utils.py`：payload/错误处理与配置校验 helper
- 代码库内 `>300` 大 service（模块层 + integrations 层）清零。

### 5.41 Cases Report Version Service 拆分（第三十五阶段）

问题：

- `backend/app/modules/cases/report_service.py` 虽已降到临界体积，但仍混合“接口编排”与“报告版本解析/筛选/持久化”细节。
- 版本筛选逻辑可独立为子域，便于补充单测并降低主 service 维护复杂度。

处理：

- 新增 `backend/app/modules/cases/report_version_service.py`，下沉：
  - `CaseReportObject`
  - 报告 scope/前缀/文件名解析
  - 报告列表与 latest/version 选择
  - 报告按名称解析与生成后持久化
- `backend/app/modules/cases/report_service.py`：
  - 保留“权限校验 + 编排”职责
  - 版本相关逻辑改为委托 `report_version_service`
- 新增单测 `backend/tests/test_case_report_version_service.py`：
  - 律师视角版本列表 latest 标记
  - 当事人视角仅返回最新 client 报告
  - 报告名路径穿越防护

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_report_version_service.py` → `3 passed`
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`221 passed`。

收益：

- `backend/app/modules/cases/report_service.py` 从 `300` 行下降到 `165` 行。
- 新增 `backend/app/modules/cases/report_version_service.py`（`148` 行）承接报告版本子域。
- Cases 报告链路分层进一步明确：
  - `report_service.py`：权限与入口编排
  - `report_payload_service.py`：payload 聚合
  - `report_access_service.py`：访问/下载响应
  - `report_version_service.py`：版本解析/筛选/持久化

### 5.42 Tenants Budget Service 单测补齐（第三十六阶段）

问题：

- `backend/app/modules/tenants/tenants_budget_service.py` 已完成拆分，但缺少直接面向 service 的 mock repository 单测。
- 预算读写逻辑（clear/set/not-found）需要独立单测，避免仅依赖 API 级测试。

处理：

- 新增 `backend/tests/test_tenants_budget_service_unit.py`，覆盖：
  - `get_tenant_ai_budget` 返回映射
  - `update_tenant_ai_budget` clear 分支持久化
  - `get_case_ai_budget` not-found 异常分支
  - `update_case_ai_budget` set 分支持久化
- 使用 fake db + fake repository 进行 service 级单测，不依赖真实数据库。

阶段回顾：

- `python -m compileall backend/app/modules/tenants` 通过。
- Tenants 定向回归：
  - `backend/tests/test_tenants_budget_service_unit.py` → `4 passed`
  - `backend/tests/test_tenants_api.py` → `3 passed`
  - `backend/tests/test_ai_queue_and_budget.py` → `7 passed`
- 后端全量回归：`225 passed`。

收益：

- Tenants 预算子域具备独立回归保障，后续改动可更快定位问题。
- 服务拆分与单测覆盖闭环进一步完善。

### 5.43 Cases Report Payload 去路由依赖 + 单测补齐（第三十七阶段）

问题：

- `backend/app/modules/cases/report_payload_service.py` 仍通过 `files/router.py` 的 `list_case_files` 取数据，存在 `service -> router` 反向依赖。
- 报告 payload 子域应直接依赖 repository，避免被 HTTP 入口细节耦合。

处理：

- `backend/app/modules/cases/report_payload_service.py`：
  - 移除对 `app.modules.files.router.list_case_files` 的依赖。
  - 改为直接使用 `FilesRepository.list_case_files(...)` 拉取文件清单。
  - 在 payload 层统一处理描述字段可见性：`client` 视角返回 `description=None`，`lawyer` 视角保留原值。
- 新增 `backend/tests/test_case_report_payload_service_unit.py`，覆盖：
  - 当事人视角文件描述脱敏；
  - 律师视角文件描述保留与分析结果映射。

阶段回顾：

- `python -m compileall backend/app/modules/cases` 通过。
- Cases 定向回归：
  - `backend/tests/test_case_report_version_service.py` → `3 passed`
  - `backend/tests/test_case_report_payload_service_unit.py` → `2 passed`
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`227 passed`。

收益：

- Cases 报告 payload 子域已从“跨层调用 router”收口为“直接依赖 repository”，分层关系更稳定。
- 报告文件描述可见性规则在 payload 层显式化，行为更可测。
- `cases/report` 子域 mock 风格单测继续补齐，后续回归定位成本更低。

### 5.44 Cases Report Access Service 单测补齐（第三十八阶段）

问题：

- `backend/app/modules/cases/report_access_service.py` 已独立承接报告访问/下载响应，但缺少直接面向子服务的单元测试。
- 访问链接与下载响应分支（直链跳转 / 本地文件回退 / 文件不存在）需要独立回归保障。

处理：

- 新增 `backend/tests/test_case_report_access_service_unit.py`，覆盖：
  - `build_case_report_access_url` 优先返回存储后端私有直链；
  - 无直链时 fallback 到 `/cases/{id}/report` 与历史版本 URL（含文件名 URL 编码）；
  - `render_case_report_response` 在直链存在时返回 `307 RedirectResponse`；
  - 对象缺失时返回 `FILE_NOT_FOUND`；
  - 本地对象存在时返回 `FileResponse`。

阶段回顾：

- Cases 定向回归：
  - `backend/tests/test_case_report_access_service_unit.py` → `5 passed`
  - `backend/tests/test_case_report_version_service.py` → `3 passed`
  - `backend/tests/test_case_report_payload_service_unit.py` → `2 passed`
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
  - `backend/tests/test_case_remarks_and_asr.py` → `6 passed`
- 后端全量回归：`232 passed`。

收益：

- Cases 报告访问子域具备独立回归保障，下载链路改动风险进一步降低。
- `cases/report` 三个核心子域（`version/payload/access`）都已进入可单独回归状态。

### 5.45 Cases Router 去 `files/router` 依赖（第三十九阶段）

问题：

- `backend/app/modules/cases/router.py` 仍直接导入 `backend/app/modules/files/router.py` 的函数，存在 router-to-router 反向依赖。
- 该依赖会扩大耦合面，后续维护容易误把 HTTP 入口实现当作可复用业务层。

处理：

- 新增 `backend/app/modules/files/case_file_service.py`，集中承接案件文件四类共享能力：
  - 列表查询：`list_case_files`
  - 文件上传：`upload_case_file`
  - 上传策略：`get_file_upload_policy`
  - 直传完成：`complete_file_upload`
- `backend/app/modules/cases/router.py`：
  - 移除对 `files/router.py` 的导入；
  - 统一改为调用 `CaseFileService`。
- `backend/app/modules/files/router.py`：
  - 对上述四个入口改为委托 `CaseFileService`，确保 `/files/*` 与 `/cases/*` 走同一业务实现。

阶段回顾：

- `python -m compileall backend/app/modules/files backend/app/modules/cases` 通过。
- 定向回归：
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
  - `backend/tests/test_case_flow_and_file_visibility.py` → `11 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
- 后端全量回归：`232 passed`。

收益：

- `cases` 与 `files` 两个模块边界更清晰，`router -> service` 约束进一步落实。
- canonical 路由和 legacy 路由共享同一文件业务实现，后续变更一致性更高。

### 5.46 Files Router 死代码清理 + 分层守卫脚本（第四十阶段）

问题：

- 第三十九阶段完成委托后，`backend/app/modules/files/router.py` 中仍保留历史实现块，存在不可达代码与维护噪音。
- 项目尚缺少可自动执行的“router 边界守卫”，难以及时阻断 router-to-router 依赖回流。

处理：

- 重写 `backend/app/modules/files/router.py` 为精简入口：
  - 上传/上传策略/直传完成/案件文件列表仅保留对 `CaseFileService` 的委托；
  - 下载/访问链接/删除保留必要路由层鉴权与响应封装。
- `backend/app/modules/files/case_file_service.py` 补齐 `ensure_delete_access(...)`，避免 delete 路径回归。
- 新增脚本 `scripts/check-router-boundaries.py`，检查：
  - 禁止 `from app.modules.*.router import ...`；
  - 禁止 router 内 `db.query(...)`。

阶段回顾：

- `python -m compileall backend/app/modules/files backend/app/modules/cases scripts/check-router-boundaries.py` 通过。
- `python scripts/check-router-boundaries.py` 通过（扫描 `8` 个 router 文件）。
- 定向回归：
  - `backend/tests/test_case_flow_and_file_visibility.py` → `11 passed`
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
- 后端全量回归：`232 passed`。

收益：

- `files/router.py` 仅保留当前真实行为，路由层可读性与可维护性明显提升。
- 分层守卫脚本可直接接入 CI，持续防止边界退化。

### 5.47 Files CaseFileService 再拆分 + 全量体检（第四十一阶段）

问题：

- 在第四十阶段后，`backend/app/modules/files/case_file_service.py` 体量回升到 `565` 行，成为新的大 service 风险点。
- 需要把“文件域校验/映射”和“自动重分析流程”从主 service 中再下沉，并对既有拆分结果做一次系统性体检。

处理：

- 新增 `backend/app/modules/files/case_file_domain_service.py`，承接：
  - 案件读取与访问校验；
  - 上传前置限制；
  - 删除权限校验；
  - `FileRead` / `FileUploadPolicyRead` 映射；
  - 上传对象大小校验。
- 新增 `backend/app/modules/files/case_file_reanalysis_service.py`，承接：
  - 客户端补充材料后的自动重分析编排；
  - 幂等键窗口计算与已存在任务复用；
  - 重分析失败分支统一收口。
- `backend/app/modules/files/case_file_service.py` 改为编排门面：
  - 组合 `domain_service + reanalysis_service`；
  - 保持外部接口不变（`list/upload/policy/complete/delete-access`）。
- 执行全量体检：
  - 分层守卫脚本通过；
  - `modules + integrations` 的 service-like 文件再次检查，`>300` 已清零。

阶段回顾：

- `python -m compileall backend/app/modules/files backend/app/modules/cases` 通过。
- `python scripts/check-router-boundaries.py` 通过（扫描 `8` 个 router 文件）。
- 定向回归：
  - `backend/tests/test_case_flow_and_file_visibility.py` → `11 passed`
  - `backend/tests/test_file_upload_security.py` → `5 passed`
  - `backend/tests/test_file_upload_race_condition.py` → `2 passed`
  - `backend/tests/test_case_canonical_endpoints.py` → `16 passed`
  - `backend/tests/test_role_access_contracts.py` → `8 passed`
- 后端全量回归：`232 passed`。

收益：

- `case_file_service.py` 从 `565` 行收敛到 `235` 行，Files 子域恢复“多子服务协作 + 门面编排”结构。
- 拆分后无新增回归，且大 service 风险再次清零。
- 形成“拆分后立即全量体检”的闭环流程，可复用于后续阶段。

## 6. 验证记录

第八阶段增量验证：

```powershell
python -m compileall backend/app/modules/tenants backend/app/api/routes_tenants.py
python -m pytest backend/tests/test_tenants_api.py backend/tests/test_ai_queue_and_budget.py backend/tests/test_auth_refresh_logout.py backend/tests/test_auth_sms_and_invite_flow.py backend/tests/test_error_codes.py backend/tests/test_role_access_contracts.py backend/tests/test_status_and_role_transitions.py -q
python -m pytest backend/tests -q
```

结果：`67 passed` + `216 passed`（本地执行，2026-03-27）。

第九阶段增量验证：

```powershell
python -m compileall backend/app/modules/analytics backend/app/modules/notifications backend/app/modules/ai/repository.py backend/app/modules/ai/ws_service.py backend/app/modules/ai/ws_router.py
python -m pytest backend/tests/test_analytics_api.py backend/tests/test_dashboard_stats.py backend/tests/test_notifications_api.py backend/tests/test_error_codes.py backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests/test_ai_ws.py -q
python -m pytest backend/tests -q
```

结果：`24 passed` + `8 passed` + `218 passed`（本地执行，2026-03-27）。

第十阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_idempotency.py backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_remark_context.py backend/tests/test_ai_ws.py -q
python -m pytest backend/tests -q
```

结果：`34 passed` + `218 passed`（本地执行，2026-03-27）。

第十一阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_idempotency.py backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_remark_context.py -q
python -m pytest backend/tests -q
```

结果：`26 passed` + `218 passed`（本地执行，2026-03-27）。

第十二阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_api.py backend/tests/test_ai_idempotency.py -q
python -m pytest backend/tests -q
```

结果：`24 passed` + `218 passed`（本地执行，2026-03-27）。

第十三阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_idempotency.py backend/tests/test_ai_remark_context.py -q
python -m pytest backend/tests -q
```

结果：`26 passed` + `218 passed`（本地执行，2026-03-27）。

第十四阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_idempotency.py backend/tests/test_ai_remark_context.py backend/tests/test_ai_ws.py -q
python -m pytest backend/tests -q
```

结果：`34 passed` + `218 passed`（本地执行，2026-03-27）。

第十五阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_canonical_endpoints.py backend/tests/test_role_access_contracts.py backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`30 passed` + `218 passed`（本地执行，2026-03-27）。

第十六阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_remarks_and_asr.py backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests -q
```

结果：`14 passed` + `218 passed`（本地执行，2026-03-27）。

第十七阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_canonical_endpoints.py backend/tests/test_role_access_contracts.py backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`30 passed` + `218 passed`（本地执行，2026-03-27）。

第十八阶段增量验证：

```powershell
python -m compileall backend/app/modules/auth
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py backend/tests/test_auth_refresh_logout.py backend/tests/test_auth_wechat_mini.py -q
python -m pytest backend/tests -q
```

结果：`50 passed` + `218 passed`（本地执行，2026-03-27）。

第十九阶段增量验证：

```powershell
python -m compileall backend/app/modules/auth
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py backend/tests/test_auth_refresh_logout.py backend/tests/test_auth_wechat_mini.py -q
python -m pytest backend/tests -q
```

结果：`50 passed` + `218 passed`（本地执行，2026-03-27）。

第二十阶段增量验证：

```powershell
python -m compileall backend/app/modules/auth
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py backend/tests/test_auth_refresh_logout.py backend/tests/test_auth_wechat_mini.py -q
python -m pytest backend/tests -q
```

结果：`50 passed` + `218 passed`（本地执行，2026-03-27）。

第二十一阶段增量验证：

```powershell
python -m compileall backend/app/modules/files
python -m pytest backend/tests/test_file_upload_security.py backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests -q
```

结果：`7 passed` + `218 passed`（本地执行，2026-03-27）。

第二十二阶段增量验证：

```powershell
python -m compileall backend/app/modules/files
python -m pytest backend/tests/test_file_upload_security.py backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests -q
```

结果：`7 passed` + `218 passed`（本地执行，2026-03-27）。

第二十三阶段增量验证：

```powershell
python -m compileall backend/app/modules/files
python -m pytest backend/tests/test_file_upload_security.py backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests -q
```

结果：`7 passed` + `218 passed`（本地执行，2026-03-27）。

第二十四阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_canonical_endpoints.py backend/tests/test_role_access_contracts.py backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`30 passed` + `218 passed`（本地执行，2026-03-27）。

第二十五阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_canonical_endpoints.py backend/tests/test_role_access_contracts.py backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`30 passed` + `218 passed`（本地执行，2026-03-27）。

第二十六阶段增量验证：

```powershell
python -m compileall backend/app/modules/auth
python -m pytest backend/tests/test_auth_wechat_mini.py -q
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py -q
python -m pytest backend/tests/test_auth_refresh_logout.py -q
python -m pytest backend/tests -q
```

结果：`14 passed` + `26 passed` + `10 passed` + `218 passed`（本地执行，2026-03-27）。

第二十七阶段增量验证：

```powershell
python -m compileall backend/app/modules/auth
python -m pytest backend/tests/test_auth_wechat_mini.py -q
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py -q
python -m pytest backend/tests/test_auth_refresh_logout.py -q
python -m pytest backend/tests -q
```

结果：`14 passed` + `26 passed` + `10 passed` + `218 passed`（本地执行，2026-03-27）。

第二十八阶段增量验证：

```powershell
python -m compileall backend/app/modules/analytics
python -m pytest backend/tests/test_analytics_api.py -q
python -m pytest backend/tests/test_dashboard_stats.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests -q
```

结果：`2 passed` + `2 passed` + `8 passed` + `218 passed`（本地执行，2026-03-27）。

第二十九阶段增量验证：

```powershell
python -m compileall backend/app/modules/tenants
python -m pytest backend/tests/test_tenants_api.py -q
python -m pytest backend/tests/test_ai_queue_and_budget.py -q
python -m pytest backend/tests/test_personal_tenant_lawyer_access.py -q
python -m pytest backend/tests/test_status_and_role_transitions.py -q
python -m pytest backend/tests -q
```

结果：`3 passed` + `7 passed` + `2 passed` + `3 passed` + `218 passed`（本地执行，2026-03-27）。

第三十阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py -q
python -m pytest backend/tests/test_ai_queue_and_budget.py -q
python -m pytest backend/tests/test_ai_idempotency.py -q
python -m pytest backend/tests/test_ai_remark_context.py -q
python -m pytest backend/tests/test_ai_ws.py -q
python -m pytest backend/tests -q
```

结果：`13 passed` + `7 passed` + `4 passed` + `2 passed` + `8 passed` + `218 passed`（本地执行，2026-03-27）。

第三十一阶段增量验证：

```powershell
python -m compileall backend/app/modules/ai
python -m pytest backend/tests/test_ai_api.py -q
python -m pytest backend/tests/test_ai_queue_and_budget.py -q
python -m pytest backend/tests/test_ai_idempotency.py -q
python -m pytest backend/tests/test_ai_remark_context.py -q
python -m pytest backend/tests/test_ai_ws.py -q
python -m pytest backend/tests -q
```

结果：`13 passed` + `7 passed` + `4 passed` + `2 passed` + `8 passed` + `218 passed`（本地执行，2026-03-27）。

第三十二阶段增量验证：

```powershell
python -m compileall backend/app/integrations/storage
python -m pytest backend/tests/test_storage_backends.py -q
python -m pytest backend/tests/test_file_upload_security.py -q
python -m pytest backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests/test_case_flow_and_file_visibility.py -q
python -m pytest backend/tests -q
```

结果：`11 passed` + `5 passed` + `2 passed` + `11 passed` + `218 passed`（本地执行，2026-03-27）。

第三十三阶段增量验证：

```powershell
python -m compileall backend/app/integrations/sms backend/app/modules/auth
python -m pytest backend/tests/test_auth_sms_and_invite_flow.py -q
python -m pytest backend/tests/test_auth_refresh_logout.py -q
python -m pytest backend/tests/test_error_codes.py -q
python -m pytest backend/tests -q
```

结果：`26 passed` + `10 passed` + `10 passed` + `218 passed`（本地执行，2026-03-27）。

第三十四阶段增量验证：

```powershell
python -m compileall backend/app/integrations/llm backend/app/modules/ai
python -m pytest backend/tests/test_openai_compatible_logging.py -q
python -m pytest backend/tests/test_runtime_config_guards.py -q
python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_remark_context.py -q
python -m pytest backend/tests -q
```

结果：`2 passed` + `10 passed` + `15 passed` + `218 passed`（本地执行，2026-03-27）。

第三十五阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_report_version_service.py -q
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`3 passed` + `16 passed` + `8 passed` + `6 passed` + `221 passed`（本地执行，2026-03-27）。

第三十六阶段增量验证：

```powershell
python -m compileall backend/app/modules/tenants
python -m pytest backend/tests/test_tenants_budget_service_unit.py -q
python -m pytest backend/tests/test_tenants_api.py -q
python -m pytest backend/tests/test_ai_queue_and_budget.py -q
python -m pytest backend/tests -q
```

结果：`4 passed` + `3 passed` + `7 passed` + `225 passed`（本地执行，2026-03-27）。

第三十七阶段增量验证：

```powershell
python -m compileall backend/app/modules/cases
python -m pytest backend/tests/test_case_report_version_service.py -q
python -m pytest backend/tests/test_case_report_payload_service_unit.py -q
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`3 passed` + `2 passed` + `16 passed` + `8 passed` + `6 passed` + `227 passed`（本地执行，2026-03-27）。

第三十八阶段增量验证：

```powershell
python -m pytest backend/tests/test_case_report_access_service_unit.py -q
python -m pytest backend/tests/test_case_report_version_service.py -q
python -m pytest backend/tests/test_case_report_payload_service_unit.py -q
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests/test_case_remarks_and_asr.py -q
python -m pytest backend/tests -q
```

结果：`5 passed` + `3 passed` + `2 passed` + `16 passed` + `8 passed` + `6 passed` + `232 passed`（本地执行，2026-03-27）。

第三十九阶段增量验证：

```powershell
python -m compileall backend/app/modules/files backend/app/modules/cases
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_file_upload_security.py -q
python -m pytest backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests/test_case_flow_and_file_visibility.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests -q
```

结果：`16 passed` + `5 passed` + `2 passed` + `11 passed` + `8 passed` + `232 passed`（本地执行，2026-03-27）。

第四十阶段增量验证：

```powershell
python -m compileall backend/app/modules/files backend/app/modules/cases scripts/check-router-boundaries.py
python scripts/check-router-boundaries.py
python -m pytest backend/tests/test_case_flow_and_file_visibility.py -q
python -m pytest backend/tests/test_file_upload_security.py -q
python -m pytest backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests -q
```

结果：`11 passed` + `5 passed` + `2 passed` + `16 passed` + `8 passed` + `232 passed`（本地执行，2026-03-27）。

第四十一阶段增量验证：

```powershell
python -m compileall backend/app/modules/files backend/app/modules/cases
python scripts/check-router-boundaries.py
python -m pytest backend/tests/test_case_flow_and_file_visibility.py -q
python -m pytest backend/tests/test_file_upload_security.py -q
python -m pytest backend/tests/test_file_upload_race_condition.py -q
python -m pytest backend/tests/test_case_canonical_endpoints.py -q
python -m pytest backend/tests/test_role_access_contracts.py -q
python -m pytest backend/tests -q
```

结果：`11 passed` + `5 passed` + `2 passed` + `16 passed` + `8 passed` + `232 passed`（本地执行，2026-03-28）。

## 7. 已完成项与未完成项

### 7.1 已完成

- AI / Cases / Clients / Invites / Auth / Users / Tenants 的主干 service / repository 分层已建立。
- 小程序错误处理漏网点完成收口。
- Analytics / Notifications / AI WebSocket 路由瘦身完成，路由层显式 `db.query(...)` 为 `0`。
- `backend/app/modules/ai/services/query_service.py` 已落地，AI 只读查询已从主编排 service 下沉。
- `backend/app/modules/ai/services/budget_service.py`、`runtime_service.py`、`task_command_service.py` 已落地，预算控制、运行时状态机、retry / 幂等命令已从主编排 service 下沉。
- `backend/app/modules/ai/services/worker_dispatch_service.py` 与 `task_processor_service.py` 已落地，worker 调度与任务类型分发已从主编排 service 下沉。
- `backend/app/modules/ai/services/submission_service.py` 已落地，`start_parse_document / start_analysis / start_falsification` 三类提交入口已从主编排 service 下沉。
- `backend/app/modules/ai/services/access_service.py`、`flow_service.py`、`context_service.py` 已落地，access / flow / context helper 已从主编排 service 下沉。
- `backend/app/modules/cases/helpers.py`、`report_service.py`、`remark_service.py`、`command_service.py` 已落地，Cases 通用 helper、报告域、备注域、命令域已完成三轮拆分。
- `backend/app/modules/cases/report_payload_service.py` 已落地，Cases 报告 payload 聚合已从 `report_service.py` 分离。
- `backend/app/modules/cases/report_access_service.py` 已落地，Cases 报告访问/下载逻辑已从 `report_service.py` 分离。
- `backend/app/modules/cases/report_payload_service.py` 已移除对 `files/router.py` 的反向依赖，改为直接使用 `FilesRepository`。
- `backend/app/modules/files/case_file_service.py` 已落地，Cases canonical 文件接口与 Files legacy 文件接口已共享同一业务实现。
- `backend/app/modules/files/case_file_domain_service.py` 与 `case_file_reanalysis_service.py` 已落地，Files 案件文件域校验/映射与自动重分析链路已从 `case_file_service.py` 下沉。
- `backend/app/modules/cases/router.py` 已移除对 `backend/app/modules/files/router.py` 的直接导入。
- `backend/app/modules/files/router.py` 已完成死代码清理，上传链路仅保留委托入口与下载/删除必要处理。
- `backend/app/modules/auth/account_service.py` 已落地，Auth 账户原语已从 `auth/service.py` 分离。
- `backend/app/modules/auth/services/login_service.py` 已落地，Auth 登录上下文与登录编排已从 `auth/service.py` 分离。
- `backend/app/modules/auth/services/sms_auth_service.py` 已落地，Auth SMS request-context 与发码/验码逻辑已从 `auth/service.py` 分离。
- `backend/app/modules/auth/services/wechat_binding_service.py` 已落地，Auth WeChat 绑定链路（手机登录绑定、绑定已有账号、旧版绑定）已从 `wechat_service.py` 分离。
- `backend/app/modules/auth/services/wechat_account_binding_service.py` 已落地，Auth WeChat 账号绑定子域（绑定已有账号、旧版绑定）已从 `wechat_binding_service.py` 分离。
- `backend/app/modules/analytics/dashboard_service.py` 已落地，Dashboard 指标统计与登录增量计算已从 `analytics/service.py` 分离。
- `backend/app/modules/tenants/tenants_budget_service.py` 已落地，租户/案件 AI 预算读写逻辑已从 `tenants/service.py` 分离。
- `backend/app/modules/ai/services/analysis_result_mapper.py` 已落地，分析结果 DTO 映射逻辑已从 `analysis_service.py` 分离。
- `backend/app/modules/ai/service.py` 已完成门面别名化收敛，单行转发方法已统一替换为类级别函数别名。
- `backend/app/modules/files/access_service.py`、`upload_service.py`、`upload_policy_service.py` 已落地，Files 访问授权、上传执行、上传策略已完成三轮拆分。
- `backend/app/integrations/storage/base.py`、`local_backend.py`、`cos_client.py` 已落地，Storage 通用模型、本地后端、COS SDK 适配已从 `integrations/storage/service.py` 分离。
- `backend/app/integrations/sms/guard_service.py` 已落地，SMS 限流与审计逻辑已从 `integrations/sms/service.py` 分离。
- `backend/app/integrations/llm/payload_utils.py` 已落地，LLM payload 解析、错误摘要与配置校验 helper 已从 `integrations/llm/service.py` 分离。
- `backend/app/modules/cases/report_version_service.py` 已落地，报告版本解析/筛选/持久化逻辑已从 `report_service.py` 分离。
- `backend/tests/test_tenants_budget_service_unit.py` 已落地，Tenants Budget Service mock repository 单元测试已补齐。
- `backend/tests/test_case_report_payload_service_unit.py` 已落地，Cases Report Payload Service 单元测试已补齐。
- `backend/tests/test_case_report_access_service_unit.py` 已落地，Cases Report Access Service 单元测试已补齐。
- `scripts/check-router-boundaries.py` 已落地，可自动检查 router-to-router 导入与 router 层 `db.query(...)` 违规。
- `backend/app/modules/ai/service.py` 当前为 `102` 行。
- `backend/app/modules/ai/services/analysis_service.py` 当前为 `282` 行。
- `backend/app/modules/cases/service.py` 当前为 `195` 行。
- `backend/app/modules/cases/report_service.py` 当前为 `165` 行。
- `backend/app/modules/auth/service.py` 当前为 `229` 行。
- `backend/app/modules/auth/wechat_service.py` 当前为 `204` 行。
- `backend/app/modules/auth/services/wechat_binding_service.py` 当前为 `227` 行。
- `backend/app/modules/analytics/service.py` 当前为 `266` 行。
- `backend/app/modules/tenants/service.py` 当前为 `295` 行。
- `backend/app/modules/files/service.py` 当前为 `50` 行。
- `backend/app/modules/files/case_file_service.py` 当前为 `235` 行。
- `backend/app/modules/files/case_file_domain_service.py` 当前为 `161` 行。
- `backend/app/modules/files/case_file_reanalysis_service.py` 当前为 `176` 行。
- `backend/app/integrations/storage/service.py` 当前为 `239` 行。
- `backend/app/integrations/sms/service.py` 当前为 `262` 行。
- `backend/app/integrations/llm/service.py` 当前为 `283` 行。
- 当前后端全量测试维持 `232 passed`。

### 7.2 待继续

- 路由层剩余待做项：`0` 个显式 `db.query(...)` 路由入口。
- 模块层核心大 service / subservice 现有 `0` 个（`>300` 行）。
- `backend/app/modules/cases/report_service.py` 已收敛到 `165` 行，主编排职责清晰，后续以补测试为主。
- 若把 `integrations/*` 一并纳入，当前 `>300` 大体量适配层 service 候选为 `0` 个。
- `backend/app/modules/ai/service.py` 已完成门面收敛，继续深拆收益较低。
- Cases 模块剩余可继续优化的点已从“主 service 拆分”转为：
  - `report_service.py` 内部再分层（若后续要继续做报告子域细化）
  - `command / remark` 的 mock repository 单元测试补齐
  - `report_service` 编排分支单元测试补齐（含 regenerate 失败回退）
  - DTO / helper 共享逻辑进一步统一
- 在 CI 接入 `scripts/check-router-boundaries.py`，将分层约束检查自动化。

## 8. 后续实施建议（顺序）

1. 代码模块层与 integrations 层 `>300` 大 service 已清零；后续建议继续补 `cases/report` 与 `ai/*` 子服务单元测试。
2. 若继续做结构演进，建议在 CI 增加分层约束检查（例如 router 不允许直写复杂查询），提升回归效率。
3. Cases 模块后续以“补测试 / 细化 report 子域”为主，不再需要优先拆 `service.py` 主体。
4. 为 `AI submission / query / budget / runtime / task_command / worker_dispatch / task_processor / access / flow / context service` 以及 `cases/auth/analytics/tenants` 补 mock repository 单元测试，降低后续回归成本。

---

维护说明：

- 本文件是当前系统化拆分的连续实施记录。
- 后续每次结构调整都应同步更新本文件与 `docs/documentation-map.md`。
