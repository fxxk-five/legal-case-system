# 提交说明：`972ae26`

## 1. 基本信息

- Commit: `972ae26`
- 标题：`fix: repair user-facing copy and reset-password flow`

## 2. 为什么需要这份说明

这个提交的标题只描述了“用户可见文案修复 + 首登改密流程修复”，但实际提交内容明显超出该范围。

该提交是在一个长期脏工作区中完成的，并且提交时暂存区中已经混入多个主题的历史改动。因此，`972ae26` 不应被理解为一个“单主题修复提交”，而应被理解为一次**集成态快照提交**。

## 3. 实际包含的主题

### 3.1 用户可见修复

这是本次提交标题真正对应的部分，主要包括：

- Web 主壳、导航、通知、退出登录文案修复
- 首登强制改密页文案修复与坏模板展示修复
- 案件详情上传/邀请/提示文案修复
- 前端通用错误提示文案修复
- 后端微信登录票据、案件邀请令牌、ASR 上传格式校验文案修复
- 新增乱码静态扫描脚本

代表文件：

- `web-frontend/src/app/layouts/DashboardLayout.vue`
- `web-frontend/src/features/auth/lib/accessControl.js`
- `web-frontend/src/pages/system/ForceResetPasswordPage.vue`
- `web-frontend/src/shared/lib/formMessages.js`
- `web-frontend/src/pages/cases/CaseDetailPage.vue`
- `backend/app/integrations/wechat/token_service.py`
- `backend/app/modules/asr/router.py`
- `scripts/check_mojibake.py`

### 3.2 后端模块化重构

该提交同时混入了后端模块边界重构，包括：

- `api/routes_*` 向 `modules/*` 路径迁移
- `services/*` 向 `integrations/*` / `modules/*` 路径迁移
- `models/*` 向 `modules/*/models/*` 路径迁移

代表文件：

- `backend/app/modules/auth/router.py`
- `backend/app/modules/cases/router.py`
- `backend/app/modules/clients/router.py`
- `backend/app/modules/ai/router.py`

### 3.3 Web 前端架构迁移

该提交同时混入了 Web 前端结构迁移，包括：

- `views/*` 向 `pages/*` 迁移
- `lib/*` 向 `shared/lib`、`features/*` 迁移
- `stores/*` 向 `app/stores`、`features/*/model` 迁移

代表文件：

- `web-frontend/src/app/router/index.js`
- `web-frontend/src/features/auth/model/store.js`
- `web-frontend/src/pages/auth/LoginPage.vue`
- `web-frontend/src/pages/cases/CasesPage.vue`

### 3.4 小程序能力迁移

该提交同时混入了小程序新结构：

- `mini-program/features/auth/*`
- `mini-program/features/ai/*`
- `mini-program/shared/api/http.js`

### 3.5 过程文档

该提交还包含过程性设计文档：

- `docs/superpowers/specs/2026-03-29-copy-fix-scan-design.md`

## 4. 这次提交的风险

### 4.1 语义风险

提交标题会让人误以为这是一次小范围修复，但实际上它包含大量结构迁移与新增模块。

### 4.2 回滚风险

如果未来只想回滚“文案修复”，不能直接回滚 `972ae26`，因为会连带回滚模块迁移。

### 4.3 审查风险

如果把这个提交当作一个普通 fix commit 来 review，会低估它的真实影响范围。

## 5. 历史解释约定

从本说明生效后，团队应按以下方式理解 `972ae26`：

- 它是**集成快照提交**
- 它不是“单主题修复提交”
- 它不能作为“文案修复已被独立隔离”的证据

## 6. 后续提交策略

为避免再次出现类似问题，后续改动必须遵守：

1. 所有新任务从 `codex/integration-current-state` 切子分支
2. 提交前只显式 `git add` 目标文件
3. 提交前必须检查 `git diff --cached --name-only`
4. 用户可见修复、结构重构、文档更新不能再混在一个提交里

## 7. 建议的后续主题拆分

后续应按主题推进，而不是继续扩大集成提交：

- `codex/fix-copy-governance`
- `codex/fix-auth-main-path`
- `codex/refactor-backend-modules`
- `codex/refactor-web-frontend-structure`
- `codex/refactor-mini-program-structure`

## 8. 结论

`972ae26` 应被视为当前仓库历史中的一个“集成态锚点”。后续开发不再延续这种混合提交方式，而是以 `codex/integration-current-state` 为基线，按单主题分支继续推进。
