# 项目文档总索引

> 更新时间：`2026-04-02`
> 原则：只保留当前仍需要阅读、执行或交付的文档。

## `docs` 保留文档

- `docs/README.md`
- `docs/current-project-status.md`
- `docs/release-execution-workorder.md`
- `docs/restructure-overall-assessment-2026-03-26.md`
- `docs/systematic-refactor-implementation-report-2026-03-26.md`
- `docs/documentation-map.md`
- `docs/role-based-reading-map.md`
- `docs/user-manual.md`
- `docs/project-setup.md`
- `docs/production-deployment.md`
- `docs/final-acceptance-checklist.md`
- `docs/ARCHITECTURE-INTERFACE-BLUEPRINT.md`
- `docs/API-CONTRACTS.md`

## `docs` 补充文档（现存但非主入口）

- `docs/auth-boundary-followup-checklist.md`
- `docs/backend-module-boundary-checklist.md`
- `docs/branch-split-plan-current-state.md`
- `docs/branching-model.md`
- `docs/commit-notes-972ae26.md`
- `docs/project-git-workflow.md`
- `docs/superpowers/specs/2026-03-29-copy-fix-scan-design.md`

## `plans` 保留文档

- `plans/project-overall-blueprint.md`

## 建议阅读顺序

1. 先读 `docs/current-project-status.md` 了解当前真实状态。
2. 需要推进放行或上线时，直接读 `docs/release-execution-workorder.md`。
3. 再读 `docs/restructure-overall-assessment-2026-03-26.md` 看收口证据与风险。
4. 继续看 `docs/systematic-refactor-implementation-report-2026-03-26.md` 了解拆分实施细节与剩余清单（当前已更新到 AI 第三十一阶段、Cases 第四十一阶段、Auth 第二十七阶段、Files 第二十三阶段、Analytics 第二十八阶段、Tenants 第三十六阶段、Storage 第三十二阶段、SMS 第三十三阶段、LLM 第三十四阶段）。
5. 根据角色进入 `docs/role-based-reading-map.md`。
6. 需要执行时再分别查看 `docs/project-setup.md`、`docs/production-deployment.md`、`docs/final-acceptance-checklist.md`。

## 本轮清理说明

- 已删除阶段性任务单、历史归档、重复部署说明、重复安全/AI/验收报告。
- `plans` 也已收敛到单蓝图模式，不再保留阶段性任务分发、细化评审和旧兼容映射。
- 仍有价值的信息已合并进：
  - `docs/current-project-status.md`
  - `docs/restructure-overall-assessment-2026-03-26.md`
  - `docs/project-setup.md`
  - `docs/production-deployment.md`
  - `docs/final-acceptance-checklist.md`
