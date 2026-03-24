# FE-A02 执行单：API Client 单出口收敛

## 1. 任务目标
- 将 Web 端 API 调用收敛到统一客户端边界，避免页面层散落拼接路径与字段转换。
- 明确 `view/store/composable/api-client` 分层职责，降低联调与回归成本。
- 保持现有页面行为不变，仅做接口对齐型调整。

## 2. 现状基线（代码事实）
- 当前存在两套调用入口：
  - `src/lib/http.js`（基础 axios 实例）
  - `src/utils/aiApi.js`（AI 业务封装）
- 多数页面直接调用 `http`，存在路径写错、method 漂移、重复解析风险。
- `aiApi.js` 存在前缀设计缺陷：`API_BASE='/api/v1/ai'` 与 `http.baseURL='/api/v1'` 组合后可能双前缀。

## 3. 目标分层
- `lib/http.js`：仅负责传输层（baseURL、token 注入、超时、拦截器）。
- `api-client/*`：每个领域一个模块（auth/cases/files/ai/users/tenants）。
- `store/composable`：只调用 `api-client`，不直接拼 URL。
- `view`：只调用 store/composable，不直接请求后端。

## 4. 收敛规则
- 禁止在 `view` 中出现硬编码 API 路径字符串。
- 所有 snake_case <-> 业务字段兼容映射集中在 `api-client`。
- 所有错误响应统一在 `api-client` 或 `formMessages` 边界处理。
- 新增接口必须先在 `api-client` 建立函数，再被上层使用。

## 5. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A02-1 | 建立领域 API 模块骨架 | `web-frontend/src/api-client/`（建议新增） | auth/cases/files/ai/users/tenants |
| A02-2 | AI API 前缀纠偏 | `src/utils/aiApi.js` 或迁移到 `api-client/ai.js` | 去双前缀 |
| A02-3 | 页面调用迁移 | `src/views/*` | 页面不再直接拼 URL |
| A02-4 | store/composable 调用迁移 | `src/stores/*`、`src/composables/*` | 单出口生效 |
| A02-5 | 规则文档与 lint 约束（可选） | `docs/` | “View 禁止直调 http”规则 |

## 6. 验收标准（DoD）
- `view` 层不再出现新增 API 字符串拼接。
- `api-client` 成为唯一业务 API 出口。
- 所有现有页面行为保持一致，无 UI 改动。
- 契约路径/method 统一由 `api-client` 管控。

## 7. 风险与默认策略
- 风险：一次性迁移范围大。  
  默认策略：先 AI + CaseDetail + Lawyers 高频页面，再全量迁移。
- 风险：迁移中出现路径回归。  
  默认策略：每迁移一个模块即执行 FE-A10 回归清单。

## 8. 回滚策略
1. 按模块迁移，出现问题可回退单模块调用。
2. 保留旧 `http` 实例不移除，作为短期兜底。
3. 回滚期间禁止再次新增页面直调 `http`。

## 9. 预估工作量
- 架构收敛设计：0.5 人日
- 迁移与联调：1.5 人日
- 合计：2 人日
