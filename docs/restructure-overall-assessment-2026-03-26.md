# 重构总评估

> 本文档替代原来的多份阶段性结构报告、AI 状态报告、安全修复报告、可视检查记录与云端基线记录。

## 已完成的收口

- 后端已从横向 `services / models / schemas / routes_*` 扩散，收口到 `modules` 与 `integrations`。
- Web 已形成 `app / pages / features / entities / shared` 的主结构。
- 小程序已把核心逻辑从 `common` 逐步迁到 `features / entities / shared`。
- 登录、角色限制、首登改密、邀请绑案、超级管理员控制台、案件主流程已接通。
- 用户手册已按当前实际能力重新整理，不再混入规划态信息。

## 已验证证据

- 后端测试：`70 passed`
- Web 测试：`58 passed`
- Web 构建：通过
- 小程序静态审查：`17/17 passed`
- 登录矩阵 smoke：`PASS`

这些结论对应的执行状态统一体现在 `docs/current-project-status.md`。

## 仍需继续推进的风险

### 发布前置风险

- 真实微信平台配置尚未闭环。
- 真实云资源、HTTPS、COS、合法域名尚未闭环。
- 真机页面验收与云端 E2E 尚未闭环。
- 回滚演练与最终 `Go / No-Go` 尚未完成。

### 功能性剩余缺口

- 概览增量卡片未补齐。
- Web 分析管理页未正式恢复。
- 收费 / 订阅 / 账单闭环未实现。

## 文档治理结论

- `docs` 已从大量阶段性 Markdown 收敛为少量常驻文档。
- 历史执行单、归档报告、重复部署与验收说明已删除。
- 仍需维护的真源只剩：
  - `docs/current-project-status.md`
  - `docs/final-acceptance-checklist.md`
  - `docs/project-setup.md`
  - `docs/production-deployment.md`
  - `docs/user-manual.md`

## 使用建议

- 看当前状态：`docs/current-project-status.md`
- 做本地联调：`docs/project-setup.md`
- 做上线放行：`docs/final-acceptance-checklist.md`
- 做生产部署：`docs/production-deployment.md`
