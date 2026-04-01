# 当前项目状态真源

> 本文档是当前仓库的**单一状态真源**。  
> 以后每次发生**优化、更新、修复、结构调整、验收结论变化**，都必须同步维护本文档。

更新时间：`2026-04-01`（Asia/Shanghai）

## 1. 文档定位与维护规则

### 1.1 这份文档负责什么

- 记录**当前真实项目结构**，避免只写目标态。
- 记录**当前已完成、部分完成、未完成**的能力状态。
- 记录**最近一次可复验的质量基线**。
- 记录**当前正式上线阻塞项**与推荐执行顺序。

### 1.2 以后每次变更都要更新什么

只要发生以下任一情况，就必须同步更新本文档：

- 新功能落地
- Bug 修复
- 架构或目录调整
- 权限与角色边界变化
- 测试结果变化
- 上线阻塞项关闭或新增
- 部署方式、联调方式、验收口径变化

### 1.3 最低维护要求

每次维护至少同步以下 6 项：

1. `更新时间`
2. `本轮变更摘要`
3. `受影响模块 / 目录`
4. `验证结果`
5. `状态结论是否变化`
6. 执行 `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`

## 2. 一页结论

| 维度 | 当前状态 | 结论 |
| --- | --- | --- |
| 项目结构 | 已形成新主线，但仍有存量目录并存 | 处于“新结构已建立、旧结构仍在收口”的阶段 |
| 功能主链路 | 已打通 | Web、微信小程序、后端主业务链路可本地联调 |
| 本地质量 | 已刷新 2026-04-01 基线 | Web / 小程序 / 登录 smoke 通过，但后端全量回归发现 1 个 dashboard 统计失败 |
| 文档治理 | 已收口并建立门禁 | `docs` 与 `plans` 已压缩为少量常驻文档，状态文档更新门禁已建立，并已提供本地 Git hook |
| 正式上线 readiness | 未完成 | 仍受云资源、微信平台、真机与云端 E2E 阻塞 |

## 3. 当前项目结构快照

## 3.1 顶层目录

当前仓库核心目录如下：

- `backend`
- `web-frontend`
- `mini-program`
- `report-service`
- `deploy`
- `scripts`
- `docs`
- `plans`

## 3.2 后端现状

### 当前主结构

- 入口：`backend/app/main.py`
- API 聚合：`backend/app/api/api_v1.py`
- 领域目录：`backend/app/modules/*`
- 外部集成：`backend/app/integrations/*`

### 当前已存在的模块目录

- `auth`
- `cases`
- `clients`
- `files`
- `ai`
- `analytics`
- `notifications`
- `asr`
- `audit`
- `tenants`
- `users`
- `invites`

### 当前已存在的集成目录

- `llm`
- `wechat`
- `storage`
- `sms`
- `report`
- `asr`

### 结构现状判断

- **主线已经转向** `modules + integrations`
- 但 `api / services / models / schemas / repositories / dependencies` 等目录仍然存在
- 因此当前后端状态应定义为：**新结构主线已建立，存量目录尚未完全移除**

## 3.3 Web 端现状

### 当前主结构方向

- `web-frontend/src/app`
- `web-frontend/src/pages`
- `web-frontend/src/features`
- `web-frontend/src/entities`
- `web-frontend/src/shared`

### 当前页面快照

- 登录与受限页：`auth/LoginPage`、`system/*`
- 管理页：`OverviewPage`、`ClientsPage`、`LawyersPage`
- 案件页：`cases/CasesPage`、`cases/CaseDetailPage`
- AI 页：`ai/DocumentParsingPage`、`ai/LegalAnalysisPage`、`ai/FalsificationPage`
- 平台页：`AdminDashboardPage`、`SuperAdminTenantsPage`、`SuperAdminUsersPage`

### 结构现状判断

- 新的 `app / pages / features / entities / shared` 主线已存在
- 但 `components / composables / lib / modules / router / stores / utils` 等存量目录仍然保留
- 因此 Web 当前也属于：**新旧结构并存，主线已明确**

## 3.4 微信小程序现状

### 当前主结构方向

- `mini-program/pages`
- `mini-program/features`
- `mini-program/entities`
- `mini-program/shared`

### 当前页面快照

- 登录：`pages/login/index`
- 通用：`pages/common/my`、`pages/common/force-reset-password`
- 律师端：`pages/lawyer/home`、`cases`、`case-detail`、`create-case`、`clients`、`lawyers`、`analytics`
- 当事人端：`pages/client/entry`、`case-list`、`case-detail`、`upload-material`
- AI 页：`pages/ai/document-parsing`、`legal-analysis`、`falsification`

### 结构现状判断

- 小程序的 `features / entities / shared` 已建立
- `mini-program/common` 兼容目录中的通用共享逻辑与 re-export 壳已清空；页面分组仍使用 `pages/common/*`
- 当前状态为：**模块化主线已稳定，通用能力已收口到 `features / entities / shared`**

## 3.5 部署结构现状

- 本地 / 演示：`docker-compose.yml`
- 生产基线：`docker-compose.prod.yml`
- 生产拓扑目标：`nginx + web-frontend + backend + ai-worker + report-service + postgres + redis`
- 文件真源目标：腾讯云 `COS`

## 4. 当前功能状态

| 领域 | 当前状态 | 说明 |
| --- | --- | --- |
| 认证登录 | 已完成主链路 | Web 支持密码/短信/微信扫码；小程序支持微信/短信/密码 |
| 角色权限 | 已完成主链路 | 超级管理员、机构管理员、律师、个人工作区律师、当事人边界已基本落地 |
| 案件管理 | 已完成主链路 | 创建、筛选、详情、状态变更、备注维护已可用 |
| 当事人协作 | 已完成主链路 | 邀请、绑案、补材、补充说明可用 |
| 文件管理 | 已完成主链路 | 上传、下载授权、删除、报告访问链路已存在 |
| AI 任务 | 已完成主链路 | 文档解析、任务状态、结果查询、自动重分析已存在 |
| 分析管理 | 部分完成 | 小程序律师端可用，Web `/analysis` 仍未正式开放 |
| 平台治理 | 已完成首版 | 超级管理员控制台、租户预算基线可用 |
| 收费闭环 | 部分完成 | 只有预算控制，未形成订阅/账单/欠费闭环 |

## 5. 最近一次已记录质量基线

> 以下是目前文档中最近一次已记录、且可用于回溯的通过结果。

- 后端回归：`264 passed, 1 failed`（`2026-04-01`，失败项：`backend/tests/test_dashboard_stats.py::test_dashboard_stats_include_delta_since_previous_login`）
- Web lint：`PASS`
- Web 测试：`58 passed`
- Web 构建：通过
- 小程序静态审查：`17/17 passed`
- 登录主链路 smoke：`PASS`
- 文档完整性检查：最近一次记录为 `PASS`

### 当前已记录的关键验证命令

- `python scripts\mini_program_static_audit.py`
- `python scripts\smoke_login_matrix.py`
- `python scripts\check-router-boundaries.py`
- `python -m pytest backend/tests -q`
- `powershell -ExecutionPolicy Bypass -File scripts\check-docs-integrity.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts\check-status-doc-update.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts\install-git-hooks.ps1`

## 6. 当前已完成事项

### 6.1 已落地主链路

- Web 登录、角色化路由、案件管理、案件详情、当事人管理、律师管理。
- 超级管理员平台总览、租户管理、用户总览。
- 小程序登录、当事人案件协作、律师端案件处理与分析管理页。
- 后端认证、案件、文件、AI、通知、统计、ASR、预算基础能力。

### 6.2 已落地关键辅助能力

- 首登强制改密
- 微信扫码登录票据交换
- 当事人邀请后自动绑案
- 上传后自动进入重新分析流程
- 文档与手册已按当前能力同步
- 状态文档强制维护门禁已建立：`scripts/check-status-doc-update.ps1` + `.github/workflows/docs-guard.yml`
- 本地 `pre-commit` / `pre-push` hook 已提供：`.githooks/pre-commit`、`.githooks/pre-push`

### 6.3 2026-03-28 变更记录

- 变更类型：重构 + CI 门禁增强
- 变更摘要：`tenants/users` 路由从 `backend/app/api` 迁移到 `backend/app/modules/*/router.py`，`api_v1.py` 改为仅聚合 `modules` 路由；`backend-ci` 新增路由边界检查与后端全量测试步骤。
- 影响范围：`backend`、`.github/workflows`、`docs`
- 受影响目录：
  - `backend/app/api/api_v1.py`
  - `backend/app/modules/tenants/router.py`
  - `backend/app/modules/users/router.py`
  - `.github/workflows/backend-ci.yml`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-router-boundaries.py`：`PASS`
  - `python -m pytest backend/tests -q`：`232 passed`
- 状态结论：后端路由分层一致性与 CI 发布门禁进一步收口，正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.4 2026-03-28 变更记录（P1）

- 变更类型：重构 + 双端错误处理收口
- 变更摘要：`auth` 模块将 `deps` 与微信相关服务中的数据库查询下沉到 `AuthRepository`；Web 与小程序 HTTP 客户端统一复用表单错误文案中的状态码消息映射，减少重复维护。
- 影响范围：`backend`、`web-frontend`、`mini-program`、`docs`
- 受影响目录：
  - `backend/app/modules/auth/repository.py`
  - `backend/app/modules/auth/deps.py`
  - `backend/app/modules/auth/services/wechat_account_binding_service.py`
  - `backend/app/modules/auth/services/wechat_binding_service.py`
  - `backend/app/modules/auth/services/wechat_context_service.py`
  - `backend/app/modules/auth/services/wechat_identity_service.py`
  - `backend/app/modules/auth/web_wechat_service.py`
  - `web-frontend/src/lib/formMessages.js`
  - `web-frontend/src/lib/http.js`
  - `mini-program/shared/lib/form.js`
  - `mini-program/shared/api/http.js`
- 验证结果：
  - `python -m pytest backend/tests/test_auth_wechat_mini.py -q`：`14 passed`
  - `python -m pytest backend/tests/test_auth_refresh_logout.py -q`：`10 passed`
  - `python scripts/check-router-boundaries.py`：`PASS`
  - `python -m pytest backend/tests -q`：`232 passed`
  - `npm --prefix web-frontend run test`：`58 passed`
- 状态结论：`auth` 数据访问边界更清晰，双端错误文案映射一致性进一步提升；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.5 2026-03-28 变更记录（P1 收口）

- 变更类型：修复 + 前端收口
- 变更摘要：修复小程序 `common/file.js` 对已删除 `common/auth.js` 的坏引用；Web 与小程序 `http` 客户端改为复用表单消息模块导出的统一回退文案常量，不再在客户端散落默认英文提示。
- 影响范围：`web-frontend`、`mini-program`、`docs`
- 受影响目录：
  - `web-frontend/src/lib/formMessages.js`
  - `web-frontend/src/lib/http.js`
  - `mini-program/shared/lib/form.js`
  - `mini-program/common/file.js`
  - `mini-program/shared/api/http.js`
- 验证结果：
  - `npm --prefix web-frontend run test`：`58 passed`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：前端错误提示收口继续推进，小程序兼容层的显式坏引用已清除；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.6 2026-03-28 变更记录（小程序 common 收口）

- 变更类型：重构
- 变更摘要：将小程序文件访问能力从 `mini-program/common/file.js` 迁移到 `mini-program/shared/lib/file.js`，页面改为直接依赖 `shared/lib`，删除旧 `common/file.js` 入口。
- 影响范围：`mini-program`、`web-frontend`、`docs`
- 受影响目录：
  - `mini-program/shared/lib/file.js`
  - `mini-program/pages/client/case-detail.vue`
  - `mini-program/pages/client/upload-material.vue`
  - `mini-program/pages/lawyer/case-detail.vue`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
  - `common/file` 源码引用扫描：`0`
- 状态结论：小程序 `common` 兼容层继续收缩，文件能力已并入 `shared/lib` 主线；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.7 2026-03-28 变更记录（小程序 common 壳文件清理）

- 变更类型：重构
- 变更摘要：删除无源码引用的 `mini-program/common/aiTask.js`、`mini-program/common/domain-api.js`、`mini-program/common/http.js`、`mini-program/common/role-routing.js` 四个纯 re-export 壳文件；同步修正 Web 跨端一致性测试的引用路径。
- 影响范围：`mini-program`、`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/modules/cases/dualEndStatusParity.test.js`
  - `web-frontend/src/modules/cases/miniProgramAiTask.test.js`
  - `web-frontend/src/modules/cases/miniProgramRoleRouting.test.js`
  - `docs/current-project-status.md`
- 验证结果：
  - 旧 `common` 壳文件全仓引用扫描：`0`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：小程序 `common` 兼容层中的纯壳入口进一步清空，跨端一致性测试已对齐到新主线；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.8 2026-03-28 变更记录（小程序 common 真实逻辑迁移）

- 变更类型：重构
- 变更摘要：将小程序 `common/cases.js` 迁入 `features/cases/api.js`，`common/display.js` 迁入 `shared/lib/display.js`，`common/config.js` 迁入 `shared/config/index.js`；同步删除旧入口并修正文档引用。
- 影响范围：`mini-program`、`docs`
- 受影响目录：
  - `mini-program/features/cases/api.js`
  - `mini-program/shared/lib/display.js`
  - `mini-program/shared/config/index.js`
  - `mini-program/README.md`
  - `docs/current-project-status.md`
- 验证结果：
  - `common/cases` / `common/display` / `common/config` 全仓引用扫描：`0`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：小程序 `common` 目录已收缩到最后一处 `form.js`，结构收口进入尾声；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.9 2026-03-28 变更记录（小程序 common 清空）

- 变更类型：重构
- 变更摘要：将小程序原表单模块迁入 `shared/lib/form.js`，全量改写现有导入；同步删除无源码引用的 `common/case-domain/*` re-export 壳文件并移除空 `common` 目录。
- 影响范围：`mini-program`、`docs`
- 受影响目录：
  - `mini-program/shared/lib/form.js`
  - `mini-program/shared/api/http.js`
  - `mini-program/components/CaseRemarkInput.vue`
  - `mini-program/features/auth/session.js`
  - `mini-program/features/workspace/workspace.js`
  - `mini-program/pages/**/*`
  - `web-frontend/src/modules/cases/*.test.js`
  - `mini-program/README.md`
  - `docs/current-project-status.md`
- 验证结果：
  - 原表单模块旧路径全仓源码引用扫描：`0`
  - `mini-program/common` 目录源码残留扫描：`0`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`：`PASS`
- 状态结论：小程序源码公共兼容层已清空，后续收口可转向配置环境化与其余前后端结构治理；正式上线阻塞仍主要在云端基础设施与真机联调。

### 6.10 2026-03-28 变更记录（小程序配置环境化）

- 变更类型：重构 + 配置治理
- 变更摘要：将小程序 `shared/config/index.js` 从单一本地硬编码地址改为按环境自动解析 `apiBaseUrl`；新增显式地址覆盖入口，并去除 AI 任务 WebSocket 构建中的本地回退常量。
- 影响范围：`mini-program`、`docs`
- 受影响目录：
  - `mini-program/shared/config/index.js`
  - `mini-program/features/ai/aiTask.js`
  - `mini-program/README.md`
  - `docs/project-setup.md`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
  - `npm --prefix web-frontend run test`：`58 passed`
  - 小程序配置环境解析脚本：`local / staging / production / override -> PASS`
  - 小程序源码残余本地硬编码地址扫描（排除配置映射与 README）：`0`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`：`PASS`
- 状态结论：小程序 API 地址已从手改源码切换为环境驱动，后续联调可直接按 `local / staging / production` 切换；非上线阻塞的工程收口可继续转向后端 repository 下沉。

### 6.11 2026-03-28 变更记录（后端 repository 下沉）

- 变更类型：重构
- 变更摘要：将 `cases/flow.py`、`cases/numbering.py`、`cases/policy.py` 与 `files/access_service.py` 中残留的直接查询下沉到 `CasesRepository` / `FilesRepository`，保留原有服务函数与路由接口不变。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/modules/cases/repository.py`
  - `backend/app/modules/cases/flow.py`
  - `backend/app/modules/cases/numbering.py`
  - `backend/app/modules/cases/policy.py`
  - `backend/app/modules/files/repository.py`
  - `backend/app/modules/files/access_service.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python -m pytest backend/tests/test_case_number_and_file_fields.py -q`：`5 passed`
  - `python -m pytest backend/tests/test_case_flow_and_file_visibility.py -q`：`11 passed`
  - `python -m pytest backend/tests/test_file_upload_security.py -q`：`5 passed`
  - `python -m pytest backend/tests/test_cases_pagination.py -q`：`6 passed`
  - `python -m pytest backend/tests/test_personal_tenant_lawyer_access.py -q`：`2 passed`
  - `python -m pytest backend/tests -q`：`232 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`：`PASS`
- 状态结论：后端 `cases/files` 的查询边界进一步集中到 repository，后续工程收口可转向 Web CI 与 schema 边界统一。

### 6.12 2026-03-28 变更记录（Web CI 门禁）

- 变更类型：工程治理
- 变更摘要：新增独立 `web-ci.yml`，将 Web 侧 `lint / test / build` 从后端流水线中解耦，单独作为 GitHub Actions 门禁执行。
- 影响范围：`.github/workflows`、`docs`
- 受影响目录：
  - `.github/workflows/web-ci.yml`
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`：`PASS`
- 状态结论：Web 已具备独立 CI 门禁，后续工程收口可转向后端 schema 边界统一与 Web 存量目录清理。

### 6.13 2026-03-28 变更记录（后端 schema 边界统一）

- 变更类型：重构
- 变更摘要：新增模块级 `schemas.py`（`analytics / notifications / users / tenants / asr`），将模块内 DTO 引用从 `app.schemas.*` 切换到 `app.modules.*.schemas`；`app.schemas.*` 在运行路径中仅保留共享 `validators` 依赖。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/modules/analytics/schemas.py`
  - `backend/app/modules/notifications/schemas.py`
  - `backend/app/modules/users/schemas.py`
  - `backend/app/modules/tenants/schemas.py`
  - `backend/app/modules/asr/schemas.py`
  - `backend/app/modules/*/{router,service,schemas}.py`
  - `backend/tests/test_tenants_budget_service_unit.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `git grep --untracked -n "app.schemas." -- backend/app backend/tests`：仅剩 `validators` 共享依赖
  - `python -m compileall backend/app -q`：`PASS`
  - `python -m pytest backend/tests/test_analytics_api.py backend/tests/test_notifications_api.py backend/tests/test_tenants_api.py backend/tests/test_users_api.py backend/tests/test_tenants_budget_service_unit.py backend/tests/test_case_number_and_file_fields.py backend/tests/test_case_flow_and_file_visibility.py backend/tests/test_case_remarks_and_asr.py -q`：`36 passed`
  - `python -m pytest backend/tests -q`：`232 passed`
  - `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`：`PASS`
- 状态结论：后端 schema 依赖边界已完成一轮模块化收敛，后续工程收口剩余主项为 Web 存量目录清理。

### 6.14 2026-03-28 变更记录（Web 语法修复与构建恢复）

- 变更类型：修复 + 重构回滚兜底
- 变更摘要：对上一轮 `REF-FE-01` 导致的前端语法破坏进行系统修复；恢复受损页面 SFC 内容、修复 `cases` 领域策略文案契约、修正 `useCaseDetail` 语法缺陷、清理 `store.test.js` BOM 导致的 Vitest 解析异常，并修复 `DashboardLayout` 标签闭合与 `SuperAdminTenantsPage` 的 `el-radio-group` 构建兼容问题。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/pages/*`
  - `web-frontend/src/pages/ai/*`
  - `web-frontend/src/pages/auth/LoginPage.vue`
  - `web-frontend/src/pages/cases/*`
  - `web-frontend/src/pages/system/ForceResetPasswordPage.vue`
  - `web-frontend/src/app/layouts/DashboardLayout.vue`
  - `web-frontend/src/entities/case/model/policy.js`
  - `web-frontend/src/features/cases/model/useCaseDetail.js`
  - `web-frontend/src/features/auth/model/store.test.js`
  - `web-frontend/src/shared/lib/fileUpload.js`
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：Web 端已恢复到可构建、可测试的稳定基线；`REF-FE-01` 可继续按“小批量迁移 + 每批 lint/test/build 回归”方式推进。

### 6.15 2026-03-28 变更记录（Web 页面导入收口：`lib/* -> shared/*`）

- 变更类型：重构
- 变更摘要：在页面层完成一批无行为变更的导入收口：将 `src/pages` 与 `src/pages/ai` 中对 `lib/http`、`lib/formMessages`、`lib/displayText` 的直接依赖迁移到 `shared/api/http` 与 `shared/lib/*`。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/pages/AdminDashboardPage.vue`
  - `web-frontend/src/pages/ClientsPage.vue`
  - `web-frontend/src/pages/LawyersPage.vue`
  - `web-frontend/src/pages/OverviewPage.vue`
  - `web-frontend/src/pages/SuperAdminTenantsPage.vue`
  - `web-frontend/src/pages/SuperAdminUsersPage.vue`
  - `web-frontend/src/pages/ai/DocumentParsingPage.vue`
  - `web-frontend/src/pages/ai/FalsificationPage.vue`
  - `web-frontend/src/pages/ai/LegalAnalysisPage.vue`
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
- 状态结论：页面层共享依赖边界进一步清晰，`REF-FE-01` 继续向 `src/lib` 存量逻辑模块迁移推进。

### 6.16 2026-03-28 变更记录（Web `lib` 实现下沉到 `shared`）

- 变更类型：重构
- 变更摘要：将 Web 端 `src/lib` 中仍承载业务实现的三项核心能力（`displayText`、`formMessages`、`http`）下沉到 `src/shared/lib` 与 `src/shared/api`，`src/lib/*` 调整为兼容 re-export 壳，降低旧目录承载业务逻辑的风险。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/shared/lib/displayText.js`
  - `web-frontend/src/shared/lib/formMessages.js`
  - `web-frontend/src/shared/api/http.js`
  - `web-frontend/src/lib/displayText.js`
  - `web-frontend/src/lib/formMessages.js`
  - `web-frontend/src/lib/http.js`
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
- 状态结论：`src/lib` 已由“实现目录”收敛为“兼容壳目录”；`REF-FE-01` 下一步聚焦 `src/modules` 业务实现与测试收口。

### 6.17 2026-03-28 变更记录（Web `src/modules/cases` 收口）

- 变更类型：重构
- 变更摘要：将 `src/modules/cases` 下遗留测试迁移到 `entities/case/model` 与 `features/cases/model`，并删除 `src/modules/cases` 中 6 个 re-export 壳文件（`api / domain-api / mapper / policy / useCaseDetail / useCaseDetailOrchestration`），避免旧目录继续承担逻辑入口。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/entities/case/model/policy.test.js`
  - `web-frontend/src/features/cases/model/*.test.js`
  - `web-frontend/src/modules/cases/*.js`（删除）
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
- 状态结论：`src/modules/cases` 已无代码文件承载；`REF-FE-01` 进入尾段，剩余工作转向清理空目录与 `src/lib` 兼容壳退场策略。

### 6.18 2026-03-28 变更记录（Web 空目录与测试落位收口）

- 变更类型：重构
- 变更摘要：删除已清空的 `web-frontend/src/modules` 目录；将 `src/lib/formMessages.test.js` 迁移到 `src/shared/lib/formMessages.test.js`，使测试目录结构与实现目录一致。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/shared/lib/formMessages.test.js`
  - `web-frontend/src/lib/formMessages.test.js`（删除）
  - `web-frontend/src/modules/`（删除）
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：`src/modules` 已完成清理，Web 存量收口只剩 `src/lib` 兼容壳退场决策与外围目录治理。

### 6.19 2026-03-28 变更记录（改进建议清单复核）

- 变更类型：状态复核
- 变更摘要：对外部评审提出的 7 项改进建议进行逐条核验，确认 `P0 路由归位`、`P0 CI 门禁升级`、`P1 小程序配置与 common 清理` 已完成；`P1 Repository 静态门禁`、`P1 双端 HTTP 错误映射单一源`、`P2 schema 最终边界统一`、`P2 服务体积阈值预警` 仍有收口工作。
- 影响范围：`backend`、`web-frontend`、`mini-program`、`docs`（状态口径）
- 受影响目录（核验证据）：
  - `backend/app/api/api_v1.py`
  - `.github/workflows/backend-ci.yml`
  - `.github/workflows/web-ci.yml`
  - `mini-program/shared/config/index.js`
  - `mini-program/shared/api/http.js`
  - `web-frontend/src/shared/api/http.js`
  - `backend/app/modules/auth/repository.py`
  - `docs/current-project-status.md`
- 状态结论：评审建议已并入当前未完成清单，后续按优先级执行。

### 6.20 2026-03-29 变更记录（`auth` Repository 边界门禁 + 服务体积阈值预警）

- 变更类型：门禁脚本 + CI
- 变更摘要：新增 `auth` 模块 Repository 边界静态检查，禁止 `service/deps/router` 直接 `db.query/db.execute`；新增服务文件体积阈值检查脚本（默认 warning-only，支持 `--fail-on-violation`），并接入后端 CI。
- 影响范围：`backend`、`CI`、`docs`
- 受影响目录：
  - `scripts/check-auth-repository-boundaries.py`
  - `scripts/check-service-size-threshold.py`
  - `.github/workflows/backend-ci.yml`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-auth-repository-boundaries.py`：`PASS`（扫描 14 个文件）
  - `python scripts/check-service-size-threshold.py --threshold 280`：`PASS`（warning-only，识别 5 个超阈值文件）
  - `python scripts/check-service-size-threshold.py --threshold 280 --fail-on-violation`：按预期 `FAIL`（用于门禁升级验证）
- 状态结论：`REF-BE-03` 与 `REF-CI-02` 已完成第一阶段落地；下一步为按告警清单继续拆分超阈值服务。

### 6.21 2026-03-29 变更记录（双端 HTTP 错误码映射统一源）

- 变更类型：重构
- 变更摘要：新增统一契约源 `contracts/status-code-map.json`，并通过生成脚本同步产出 Web/小程序端 `statusCodeMap.js`；`web-frontend/src/shared/api/http.js` 与 `mini-program/shared/api/http.js` 改为导入共享映射，移除两端重复内联定义。
- 影响范围：`web-frontend`、`mini-program`、`scripts`、`contracts`、`docs`
- 受影响目录：
  - `contracts/status-code-map.json`
  - `scripts/sync-status-code-map.py`
  - `web-frontend/src/shared/api/statusCodeMap.js`
  - `mini-program/shared/api/statusCodeMap.js`
  - `web-frontend/src/shared/api/http.js`
  - `mini-program/shared/api/http.js`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/sync-status-code-map.py`：`PASS`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
  - `npm --prefix web-frontend run test`：`58 passed`
- 状态结论：`REF-FE-02` 已完成，双端错误码映射进入“单一源 + 生成落位”维护模式。

### 6.22 2026-03-29 变更记录（schema 边界门禁第一阶段）

- 变更类型：门禁脚本 + CI
- 变更摘要：新增 `scripts/check-schema-boundaries.py`，禁止 `backend/app` 与 `backend/tests` 新增 `app.schemas.*`（仅 `app.schemas.validators` 例外）；并将检查接入 `backend-ci`。
- 影响范围：`backend`、`CI`、`docs`
- 受影响目录：
  - `scripts/check-schema-boundaries.py`
  - `.github/workflows/backend-ci.yml`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-schema-boundaries.py`：`PASS`（扫描 227 个 Python 文件）
- 状态结论：`REF-BE-04` 已完成“禁止新增旧路径依赖”的门禁阶段，后续仅剩 `validators` 归属策略与历史兼容层退场节奏决策。

### 6.23 2026-03-29 变更记录（服务体积拆分：`tenants/service.py`）

- 变更类型：重构
- 变更摘要：将租户创建与管理员初始化逻辑从 `modules/tenants/service.py` 拆分到 `modules/tenants/provisioning_service.py`，`TenantsService` 改为编排与委托，保持对外行为不变。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/modules/tenants/service.py`
  - `backend/app/modules/tenants/provisioning_service.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-service-size-threshold.py --threshold 280`：warning 数量从 5 降至 4
  - `python scripts/check-auth-repository-boundaries.py`：`PASS`
  - `python scripts/check-schema-boundaries.py`：`PASS`
  - `python -m pytest backend/tests/test_tenants_api.py backend/tests/test_tenants_budget_service_unit.py -q`：`7 passed`
- 状态结论：`REF-BE-05` 完成一项超阈值文件拆分，剩余 4 个超阈值服务待继续处理。

### 6.24 2026-03-29 变更记录（服务体积收口：`integrations/llm/service.py`）

- 变更类型：重构
- 变更摘要：在 `OpenAICompatibleProvider` 中提炼 `_ensure_provider_ready()`，消除三处重复的 provider 配置校验逻辑，压缩服务文件体积且不改变调用行为。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/integrations/llm/service.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-service-size-threshold.py --threshold 280`：warning 数量从 4 降至 3
  - `python -m pytest backend/tests/test_openai_compatible_logging.py backend/tests/test_tenants_api.py backend/tests/test_tenants_budget_service_unit.py -q`：`9 passed`
- 状态结论：`REF-BE-05` 持续推进，超阈值服务剩余 3 个。

### 6.25 2026-03-29 变更记录（服务体积拆分：`analysis_service.py`）

- 变更类型：重构
- 变更摘要：将分析流程中的通用归一化与估算函数下沉到 `modules/ai/services/analysis_helpers.py`，`analysis_service.py` 仅保留任务执行与业务组装逻辑。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/modules/ai/services/analysis_service.py`
  - `backend/app/modules/ai/services/analysis_helpers.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-service-size-threshold.py --threshold 280`：warning 数量从 3 降至 2
  - `python -m pytest backend/tests/test_ai_api.py backend/tests/test_ai_queue_and_budget.py -q`：`20 passed`
- 状态结论：`REF-BE-05` 再完成一项拆分，超阈值服务剩余 2 个。

### 6.26 2026-03-29 变更记录（服务体积拆分：`runtime_service.py`）

- 变更类型：重构
- 变更摘要：将队列重试相关公共逻辑（`get_queue_attempt`、`effective_worker_id`）抽离到 `runtime_helpers.py`，`runtime_service.py` 聚焦任务生命周期与重试流程。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/modules/ai/services/runtime_service.py`
  - `backend/app/modules/ai/services/runtime_helpers.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-service-size-threshold.py --threshold 280`：warning 数量从 2 降至 1
  - `python -m pytest backend/tests/test_ai_queue_and_budget.py backend/tests/test_ai_queue_adapter.py backend/tests/test_ai_ws.py -q`：`17 passed`
- 状态结论：`REF-BE-05` 持续推进，超阈值服务剩余 1 个。

### 6.27 2026-03-29 变更记录（服务体积拆分：`integrations/wechat/service.py`）

- 变更类型：重构
- 变更摘要：将微信登录票据与案件邀请令牌的编解码逻辑下沉到 `integrations/wechat/token_service.py`，`service.py` 保留兼容导出与业务入口，调用方式不变。
- 影响范围：`backend`、`docs`
- 受影响目录：
  - `backend/app/integrations/wechat/service.py`
  - `backend/app/integrations/wechat/token_service.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-service-size-threshold.py --threshold 280`：`PASS`（56 个 service 文件全部不超阈值）
  - `python -m pytest backend/tests/test_auth_wechat_mini.py backend/tests/test_auth_sms_and_invite_flow.py -q`：`40 passed`
  - `python scripts/check-auth-repository-boundaries.py`：`PASS`
  - `python scripts/check-schema-boundaries.py`：`PASS`
- 状态结论：`REF-BE-05` 已完成，本轮服务体积预警清单已清零。

### 6.28 2026-03-29 变更记录（Web `src/lib` 兼容壳退场）

- 变更类型：重构
- 变更摘要：删除 Web 端剩余兼容壳 `src/lib/{displayText,formMessages,http}.js`，完成 `REF-FE-01` 的目录收口；当前业务导入统一为 `shared/*`。
- 影响范围：`web-frontend`、`docs`
- 受影响目录：
  - `web-frontend/src/lib/displayText.js`（删除）
  - `web-frontend/src/lib/formMessages.js`（删除）
  - `web-frontend/src/lib/http.js`（删除）
  - `docs/current-project-status.md`
- 验证结果：
  - `npm --prefix web-frontend run lint -- --no-fix`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
- 状态结论：`REF-FE-01` 已完成，Web 目录主线已收敛到 `app / pages / features / entities / shared`。

### 6.29 2026-03-29 变更记录（schema 边界最终收口 + 编码回归修复）

- 变更类型：重构 + 修复
- 变更摘要：
  - 将共享校验器正式迁移到 `app/core/validators.py`，`app/schemas/validators.py` 降级为兼容 re-export；
  - 删除未再被运行路径引用的旧 `app/schemas/{analytics,asr,notification,tenant,user}.py`；
  - 升级 `check-schema-boundaries` 规则为“`app/schemas` 兼容包外禁止任何 `app.schemas.*` 引用”；
  - 修复 `auth/account_service.py` 与 `integrations/wechat/service.py` 的编码破坏导致语法异常。
- 影响范围：`backend`、`scripts`、`docs`
- 受影响目录：
  - `backend/app/core/validators.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/schemas/validators.py`
  - `backend/app/schemas/{analytics,asr,notification,tenant,user}.py`（删除）
  - `backend/app/modules/auth/account_service.py`
  - `backend/app/integrations/wechat/service.py`
  - `scripts/check-schema-boundaries.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python scripts/check-schema-boundaries.py`：`PASS`
  - `python scripts/check-auth-repository-boundaries.py`：`PASS`
  - `python scripts/check-service-size-threshold.py --threshold 280`：`PASS`
  - `python -m compileall backend/app -q`：`PASS`
  - `python -m pytest backend/tests -q`：`232 passed`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
- 状态结论：`REF-BE-04` 已完成（门禁 + 归属 + 存量清理）。

### 6.30 2026-03-29 变更记录（Usage Advice 落地 + 任务清单回顾）

- 变更类型：功能增强 + 文档同步
- 本轮变更摘要：
  - 新增登录前置判断接口：`POST /auth/login-advice`，返回 `requires_tenant_code`、`requires_admin_approval`、`recommended_entry`、`login_state`、`support_hint`。
  - Web 登录页接入前置判断：手机号校验后可提前提示“必填 tenant_code / 待审批 / 推荐端”。
  - 小程序登录页接入前置判断：短信/密码登录前预判 tenant_code 与审批状态，统一状态提示。
  - 当事人补材页强化“批次 + 主题”引导文案，并增强缺失说明时的上传前提醒。
  - 通知脚本新增“待审批律师 SLA（2h）提醒”，并增加 24h 去重，避免提醒轰炸。
- 影响范围：`backend / web-frontend / mini-program / docs`
- 受影响目录：
  - `backend/app/modules/auth/{router.py,service.py,services/login_service.py,schemas.py}`
  - `backend/tests/test_auth_sms_and_invite_flow.py`
  - `web-frontend/src/pages/auth/LoginPage.vue`
  - `mini-program/pages/login/index.vue`
  - `mini-program/shared/api/http.js`
  - `mini-program/pages/client/upload-material.vue`
  - `mini-program/features/cases/upload-session-controller.js`
  - `backend/app/scripts/generate_notifications.py`
  - `docs/user-manual.md`
  - `docs/API-CONTRACTS.md`
  - `docs/final-acceptance-checklist.md`
  - `docs/current-project-status.md`
- 任务清单回顾：
  - [x] 复核登录/上传/审批差异与边界
  - [x] 实现 `/auth/login-advice` 与多租户前置判定
  - [x] 改造 Web + 小程序登录页接入前置引导
  - [x] 增强补材页“批次+主题”与补充说明提醒
  - [x] 增加待审批律师 SLA 提醒与去重
  - [x] 更新状态真源、手册、契约与验收清单
- 状态结论：登录支持与培训口径一致性进一步提升；本轮为体验与治理增强，不改变“正式上线仍受云资源与真机联调阻塞”的总判断。

### 6.31 2026-04-01 变更记录（后端模块边界清单收口）

- 变更类型：重构 + 边界治理
- 变更摘要：
  - 完成 `files / upload`、`files / reanalysis-status`、`files / delete-access` 三个文件模块边界节点，相关写操作统一收口到 `FilesRepository`。
  - 完成 `ai / task-create`、`ai / runtime-command`、`ai / submit-budget-flow` 三个 AI 模块边界节点，相关写操作统一收口到 `AIRepository`。
  - `docs/backend-module-boundary-checklist.md` 已清零，后端模块边界清单全部完成。
- 影响范围：`backend / docs`
- 受影响目录：
  - `backend/app/modules/files/{repository.py,case_file_service.py,case_file_reanalysis_service.py,router.py,upload_service.py}`
  - `backend/app/modules/ai/{repository.py,services/analysis_service.py,services/parse_service.py,services/falsification_service.py,services/runtime_service.py,services/task_command_service.py,services/worker_dispatch_service.py,services/submission_service.py,services/budget_service.py,services/flow_service.py}`
  - `backend/tests/test_files_repository_boundaries.py`
  - `backend/tests/test_ai_repository_boundary.py`
  - `docs/backend-module-boundary-checklist.md`
- 验证结果：
  - `pytest backend/tests/test_files_repository_boundaries.py -q`：`4 passed`
  - `pytest backend/tests/test_case_flow_and_file_visibility.py -k "upload or delete or access_link or direct_upload_completion or debounce" -q`：`6 passed, 5 deselected`
  - `pytest backend/tests/test_file_upload_security.py -q`：`5 passed`
  - `pytest backend/tests/test_storage_backends.py -q`：`11 passed`
  - `pytest backend/tests/test_ai_repository_boundary.py -q`：`9 passed`
  - `pytest backend/tests/test_ai_queue_and_budget.py -q`：`7 passed`
  - `pytest backend/tests/test_ai_api.py -q`：`13 passed`
  - `backend/app/modules/files`（排除 `repository.py`）与 `backend/app/modules/ai/services` 裸写库点扫描：`0`
- 状态结论：后端模块边界收口已完成，工程重心应从 Repository 写边界治理转向状态同步、本地质量基线刷新与正式放行准备；正式上线阻塞仍主要在云资源、微信能力、真机验收与云端 E2E。

### 6.32 2026-04-01 变更记录（本地质量基线刷新）

- 变更类型：验收 + 基线刷新
- 变更摘要：
  - 重新执行后端全量回归、Web lint/test/build、小程序静态审查、登录主链路 smoke。
  - Web、小程序与登录链路均通过。
  - 后端全量回归发现 1 个新增失败：`backend/tests/test_dashboard_stats.py::test_dashboard_stats_include_delta_since_previous_login`，当前断言为 `delta_deadline_risk_count == 1`，实际返回 `0`。
- 影响范围：`backend / web-frontend / mini-program / docs`
- 受影响目录：
  - `backend/tests/test_dashboard_stats.py`
  - `docs/current-project-status.md`
- 验证结果：
  - `python -m pytest backend/tests -q`：`264 passed, 1 failed`
  - `npm --prefix web-frontend run lint`：`PASS`
  - `npm --prefix web-frontend run test`：`58 passed`
  - `npm --prefix web-frontend run build`：`PASS`
  - `python scripts/mini_program_static_audit.py`：`17/17 passed`
  - `python scripts/smoke_login_matrix.py`：`PASS`
- 状态结论：当前本地基线已刷新，但未恢复到“全绿”状态；进入放行准备前，应先修复 dashboard 统计回归并重新跑后端全量回归。

## 7. 当前未完成事项

## 7.1 正式上线阻塞项（P0）

### 微信与真机联调

- `WX-01`：真实 `AppID / AppSecret`、合法域名、手机号能力、扫码联调未闭环。
- `QA-03`：仍需 `HBuilderX` GUI、微信开发者工具界面态与真机逐页验收。

### 云资源与部署基线

- `W12-T03`：真实 `CVM / 域名 / HTTPS` 未完成。
- `W12-T04`：真实 `COS / CORS / 下载链路` 未完成。
- `W12-T08`：小程序合法域名联调未完成。
- `W12-V01 ~ W12-V06`：生产 compose、Web、API、COS、worker、report-service、小程序接口联调未完成。
- `OPS-01`：云端迁移、环境变量收口、云端 smoke 未完成。

### 上线门禁

- `W13-T01 ~ W13-T03`：Web / 小程序主流程 smoke 未完成。
- `W13-T04`：真实云端登录链路 E2E 未完成。
- `W13-T05`：上传 → AI → 报告下载全链路 E2E 未完成。
- `W13-T06`：云端回滚演练未完成。
- `W13-T07`：缺陷分级与阻断判定未完成。
- `W13-T08`：最终 `Go / No-Go` 未完成。

## 7.2 部分完成项

- `ACC-14`：概览页只完成了“较上次登录变化”，未补齐规划中的多张增量卡片。
- `ACC-16`：小程序分析管理可用，但 Web `/analysis` 仍重定向到 `overview`。
- `ACC-17`：仅完成租户 AI 预算控制，未形成完整收费闭环。

## 7.3 工程收口剩余任务（非上线阻塞）

- `QA-BE-BASELINE-01`：修复 `backend/tests/test_dashboard_stats.py::test_dashboard_stats_include_delta_since_previous_login` 暴露的 dashboard 增量统计回归，并恢复后端全量回归全绿。

## 8. 推荐执行顺序

1. 先修复 `QA-BE-BASELINE-01`
2. 再完成 `W12-T03 / W12-T04 / W12-T08`
3. 再完成 `WX-01` 与 `QA-03`
4. 再做 `W12-V01 ~ W12-V06`
5. 再做 `W13-T01 ~ W13-T06`
6. 最后完成 `W13-T07 / W13-T08`

## 9. 以后维护时的更新模板

每次优化 / 更新 / 修复后，至少按下面格式追加或改写本文件相关内容：

```md
### YYYY-MM-DD 变更记录

- 变更类型：优化 / 修复 / 新增 / 重构 / 验收
- 变更摘要：
- 影响范围：backend / web-frontend / mini-program / deploy / docs
- 受影响目录：
- 验证结果：
- 是否影响上线结论：是 / 否
- 如果影响，修改第 2、4、5、7、8 节
```

### 2026-03-27 变更记录

- 变更类型：优化 / 门禁
- 变更摘要：新增本地 Git hook 安装脚本，并提供 `pre-commit` / `pre-push` 自动检查。
- 影响范围：scripts / .githooks / docs / CI
- 受影响目录：`.githooks`、`scripts/check-status-doc-update.ps1`、`scripts/install-git-hooks.ps1`、`.github/workflows`
- 验证结果：状态文档门禁脚本通过，文档完整性检查通过。
- 是否影响上线结论：否

## 10. 关联文档

- 文档入口：`docs/README.md`
- 用户手册：`docs/user-manual.md`
- 接口契约：`docs/API-CONTRACTS.md`
- 架构蓝图：`docs/ARCHITECTURE-INTERFACE-BLUEPRINT.md`
- 本地联调：`docs/project-setup.md`
- 生产部署：`docs/production-deployment.md`
- 上线门禁：`docs/final-acceptance-checklist.md`
- 总蓝图：`plans/project-overall-blueprint.md`
