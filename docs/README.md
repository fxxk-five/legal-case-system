# 项目文档入口

> `docs` 已按“只保留仍有执行价值的信息”收口；历史阶段报告、执行单、归档记录已合并删除。

## 建议先读

1. `docs/current-project-status.md`：当前实现状态、上线阻塞项、推荐执行顺序。
2. `docs/release-execution-workorder.md`：放行前、上线后稳定期、稳定后切 `dev` 的单人执行作业单。
3. `docs/restructure-overall-assessment-2026-03-26.md`：本轮重构收口结果、验证证据、剩余风险。
4. `docs/documentation-map.md`：`docs` 与 `plans` 的完整索引。
5. `docs/user-manual.md`：按当前角色与实际可用功能整理的用户手册。
6. `docs/final-acceptance-checklist.md`：联调、上线、放行使用的验收门禁。

## 按主题查看

- 本地开发与联调：`docs/project-setup.md`
- 生产部署：`docs/production-deployment.md`
- 工程推进与上线作业单：`docs/release-execution-workorder.md`
- 系统结构：`docs/ARCHITECTURE-INTERFACE-BLUEPRINT.md`
- 接口契约：`docs/API-CONTRACTS.md`
- 按角色最短阅读路径：`docs/role-based-reading-map.md`

## 文档维护规则

- 每次优化、更新、修复、结构调整后，必须先更新 `docs/current-project-status.md`。
- 架构收口、问题闭环、风险结论更新 `docs/restructure-overall-assessment-2026-03-26.md`。
- 新增或保留的 `docs/*.md`、`plans/*.md` 必须登记到 `docs/documentation-map.md`。
- 合并前执行 `powershell -ExecutionPolicy Bypass -File scripts/check-docs-integrity.ps1`。
- 如有代码、脚本、部署、CI 等非文档变更，还必须执行 `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`。
- 建议本地执行 `powershell -ExecutionPolicy Bypass -File scripts/install-git-hooks.ps1`，启用 `pre-commit` / `pre-push` 自动门禁。
