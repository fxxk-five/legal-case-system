# 最终验收清单（需求映射版，2026-03）

## 1. 文档目的与判定口径

本文档用于将主任务原始需求映射为可验收结果，统一标记为：
- 已完成
- 部分完成
- 未完成

双端同构与角色/菜单/页面对照请同时参考 `docs/v3-dual-end-parity-matrix.md`。

判定原则：
- 仅以仓库当前代码与测试为依据，不以目标方案代替实现事实。
- 每项均给出后端、Web、小程序证据路径。
- 对“部分完成/未完成”项给出可执行下一步建议。

---

## 2. 需求映射总表

| 原始需求项 | 当前状态 | 后端证据 | Web 证据 | 小程序证据 | 下一步建议 |
|---|---|---|---|---|---|
| 1. 短信验证码能力（发送、登录、注册接入） | 已完成 | `backend/app/api/routes_auth.py`（`/auth/sms/send`、`/auth/sms/verify`、`/auth/sms-login`、`/auth/register`）；`backend/tests/test_auth_sms_and_invite_flow.py` | `web-frontend/src/views/LoginView.vue`（短信验证码登录页签） | 小程序正式入口已切到 `mini-program/pages/login/index.vue` 微信快捷登录 | 已可验收；建议下一步补充生产短信模板、频控与审计字段落库。 |
| 2. 邀请注册 + 审批流（注册后待审批） | 已完成 | `backend/app/api/routes_auth.py`（微信直登待审批返回 `PENDING_APPROVAL`）；`backend/app/api/routes_users.py`（`/users/pending`、`/users/{id}/approve`）；`backend/tests/test_auth_wechat_mini.py` | `web-frontend/src/views/LawyersView.vue`（待审批列表与通过/拒绝） | `mini-program/pages/login/index.vue`（机构邀请直达微信登录并显示待审批结果） | 已可验收；建议下一步增加审批批量操作与审批审计查询页。 |
| 3. super admin 最小能力 | 已完成 | `backend/app/dependencies/auth.py`（`require_super_admin`）；`backend/app/api/routes_tenants.py`（`GET /tenants`）；`backend/app/api/routes_users.py`（`GET /users`）；`backend/tests/test_auth_sms_and_invite_flow.py` | `web-frontend/src/lib/accessControl.js`（Web 主导航仅 `tenant_admin/lawyer`，未开放 super admin 控制台） | `mini-program/common/session.js`（无 super admin 专属端能力） | 后端最小能力已落地；建议下一步补充 super admin 专用管理入口与只读审计视图。 |
| 4. Web 端三类登录 | 已完成 | `backend/app/api/routes_auth.py`（`/auth/login`、`/auth/sms-login`、`/auth/web-wechat-login*`）；`backend/tests/test_auth_sms_and_invite_flow.py`；`backend/tests/test_auth_wechat_mini.py` | `web-frontend/src/views/LoginView.vue`（账号密码、短信验证码、微信扫码三入口） | `mini-program/pages/login/index.vue`（扫码后确认浏览器登录） | 已可验收；建议下一步补真实微信扫码真机回归与过期票据刷新体验。 |
| 5. Web 端机构邀请承接 | 已完成 | `backend/app/api/routes_users.py`（`/users/invite-lawyer` 返回 `scene=lawyer-invite`） | `web-frontend/src/views/LawyersView.vue`（生成邀请链接） | `mini-program/pages/login/index.vue`（支持 `scene=lawyer-invite`） | 已可验收；建议增加面向微信转发的短链或企业微信发送模板。 |
| 6. Web 端角色化菜单与路由收敛 | 已完成 | `backend/app/dependencies/auth.py`（角色鉴权）；`backend/tests/test_role_access_contracts.py`（权限契约） | `web-frontend/src/lib/accessControl.js`；`web-frontend/src/router/index.js`（角色导航、默认落点、路由守卫） | `mini-program/common/session.js`（按角色分流） | 已可验收；建议下一步把“仅前端守卫”的规则再向后端策略统一收敛。 |
| 7. Web 当事人管理骨架页 | 已完成（骨架） | `backend/app/api/routes_cases.py`（`GET /cases` 提供聚合来源） | `web-frontend/src/views/ClientsView.vue`（明确“最小骨架/占位”） | `mini-program/pages/client/case-detail.vue`（当事人端详情与文件流） | 当前满足骨架目标；下一步补全独立当事人查询接口与详情联动页。 |
| 8. AI 深度分析 / 证伪入口隐藏 | 已完成 | 后端 AI 接口保留但不作为正式前台入口 | `web-frontend/src/router/index.js`、`web-frontend/src/views/CaseDetailView.vue`（仅保留 AI 解析入口） | `mini-program/pages/lawyer/case-detail.vue`（仅保留 AI 解析入口） | 当前版本先收口用户入口；下一步重新设计开放策略后再恢复。 |
| 9. Web 受限页（待审批/当事人仅小程序/访问受限） | 已完成 | `backend/app/dependencies/auth.py`（账号状态与权限约束） | `web-frontend/src/views/PendingApprovalView.vue`、`web-frontend/src/views/ClientMiniOnlyView.vue`、`web-frontend/src/views/AccessRestrictedView.vue`、`web-frontend/src/router/index.js` | `mini-program/common/session.js`（当事人进入小程序页） | 已可验收；建议下一步统一错误码到受限页文案映射表。 |
| 10. 小程序当事人邀请登录/绑案 | 已完成 | `backend/app/api/routes_auth.py`（`/auth/wx-mini-login`、`/auth/wx-mini-phone-login`、`/auth/wx-mini-bind-existing`）；`backend/app/api/routes_cases.py`（邀请路径生成） | `web-frontend/src/views/CaseDetailView.vue`（邀请路径入口） | `mini-program/pages/login/index.vue`、`mini-program/pages/client/entry.vue`（微信登录跳转） | 已可验收；建议补充邀请失效后的一键重发与客服引导。 |
| 11. 小程序资料上传闭环 | 已完成 | `backend/app/api/routes_files.py`（`/files/upload-policy`、`/files/upload`、`/files/case/{id}`） | `web-frontend/src/views/CaseDetailView.vue`（同案件文件可见，支持上传/下载） | `mini-program/pages/client/case-detail.vue`（批量上传队列、刷新、预览下载） | 已可验收；建议补充上传批次号与失败重试统计。 |
| 12. 小程序 AI 状态展示 | 已完成 | `backend/app/api/routes_ai.py`（任务状态接口）；`backend/app/api/routes_ws_ai.py`（WS 进度） | `web-frontend/src/views/ai/DocumentParsing.vue`、`web-frontend/src/views/ai/LegalAnalysis.vue`、`web-frontend/src/views/ai/Falsification.vue` | `mini-program/common/aiTask.js`；`mini-program/pages/client/case-detail.vue`（WS+轮询状态展示） | 已可验收；建议补充任务超时、失败分类与重试原因可视化。 |
| 13. 小程序权限收敛 | 已完成 | `backend/app/dependencies/auth.py`（mini 来源判定）；`backend/app/api/routes_files.py`（client 非 mini 来源拒绝）；`backend/tests/test_role_access_contracts.py` | `web-frontend/src/views/ClientMiniOnlyView.vue`（当事人 Web 受限） | `mini-program/common/http.js`（默认发送 mini 来源头）；`mini-program/common/session.js`（角色分流） | 已可验收；建议下一步把更多 client 接口统一纳入后端 mini-only 策略清单。 |
| 14. 概览增量卡片（待办） | 未完成 | `backend/app/api/routes_stats.py`（仅律师数/案件数/待审批律师数） | `web-frontend/src/views/OverviewView.vue`（当前为基础 4 卡片） | `mini-program/pages/client/case-detail.vue`（已有进度摘要，可作为增量卡片数据来源之一） | 新增接口与卡片：AI任务进行中、近7天新增案件、近7天上传量、异常任务数；并补充过滤跳转。 |
| 15. 案件高级排序与自动案号（待办） | 未完成 | `backend/app/schemas/case.py`（`case_number` 为必填，尚无自动生成）；`backend/app/api/routes_cases.py`（排序固定 `created_at desc`） | `web-frontend/src/views/CasesView.vue`（仅状态筛选，无高级排序） | `mini-program/pages/lawyer/home.vue`（列表端未体现高级排序能力） | 增加后端排序参数与白名单字段；新增自动案号生成策略与唯一性约束；前端增加排序控件与持久化。 |
| 16. 分析管理可视化与 AI 配置编辑（待办） | 部分完成 | `backend/app/api/routes_ai.py`（任务/结果接口已具备） | `web-frontend/src/views/AnalysisManageView.vue`（当前仅骨架与入口） | `mini-program/pages/ai/*.vue`（执行页已可用，但无配置管理） | 补充分析管理页：趋势图、任务队列可视化、失败重试面板；新增 AI 配置读取/编辑/发布接口。 |
| 17. 收费闭环（套餐、配额、账单、欠费策略） | 未完成 | `backend/app/models/__init__.py`（暂无 billing 相关模型导出） | `web-frontend/src/router/index.js`（暂无收费管理路由） | `mini-program/pages.json`（暂无订阅/账单页面） | 按 P2 增加 `plans/subscriptions/usage_ledger/billing_events` 数据模型与管理页面，落地欠费能力收敛。 |

---

## 3. 整体结论

- P0 主链路（微信直登、Web 扫码登录、邀请审批、小程序上传与 AI 状态、权限基线）已落地，可进入联合验收。
- 当前重点缺口集中在 P1/P2：
  1. 概览增量卡片
  2. 案件高级排序与自动案号
  3. 分析管理可视化与 AI 配置编辑
  4. 收费闭环
- 建议以本清单作为验收与迭代看板的单一事实来源，并与 `docs/PROJECT-FRAMEWORK.md` 的阶段路线同步维护。
