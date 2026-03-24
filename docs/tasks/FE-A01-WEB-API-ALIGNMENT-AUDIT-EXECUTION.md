# FE-A01 执行单：Web API 调用对齐审计

## 1. 任务目标
- 对 Web 端所有 API 调用做逐页面审计，确保路径/方法/参数与 `docs/API-CONTRACTS.md` 一致。
- 输出“现状 -> 契约 -> 修复动作”矩阵，供编码人员直接执行。
- 仅限接口对齐修复，不涉及任何 UI/样式/交互改动。

## 2. 范围
### 2.1 In Scope
- `web-frontend/src/views/*`、`src/stores/*`、`src/utils/aiApi.js` API 调用点。
- 路径、method、参数名、响应解析、类型声明对齐。

### 2.2 Out of Scope
- 页面视觉、布局、文案风格、动画。
- 非接口相关业务重构。

## 3. 审计基线（代码事实）
- 发现多个旧接口调用与契约不一致，集中在案件详情、律师管理、登录加入机构、AI API 前缀。
- 典型风险：调用 404/405、双前缀请求（`/api/v1/api/v1/...`）、错误方法导致联调阻塞。

## 4. 对齐矩阵（可直接改造）
| 位置 | 现状调用 | 契约调用 | 问题类型 | 修复动作 |
|---|---|---|---|---|
| `CaseDetailView.vue` | `GET /cases/{id}/files` | `GET /files/case/{id}` | 路径错误 | 修改路径 |
| `CaseDetailView.vue` | `PATCH /cases/{id}/status` | `PATCH /cases/{id}` | 路径错误 | 修改路径并保持 body |
| `CaseDetailView.vue` | `POST /cases/{id}/files` | `POST /files/upload?case_id={id}` | 路径错误 | 改为上传接口 |
| `CaseDetailView.vue` | `POST /cases/{id}/invite` | `GET /cases/{id}/invite-qrcode` | method+路径错误 | 修改 method/path 与响应解析 |
| `CaseDetailView.vue` | `DELETE /files/{id}` | 无该契约接口 | 非法调用 | 下线该调用或改为已有能力 |
| `LawyersView.vue` | `GET /users` | `GET /users/lawyers` | 路径错误 | 修改路径 |
| `LawyersView.vue` | `POST /users` | `POST /users/lawyers` | 路径错误 | 修改路径 |
| `LawyersView.vue` | `POST /users/{id}/approve` | `PATCH /users/{id}/approve` | method错误 | 改为 PATCH |
| `LawyersView.vue` | `POST /users/{id}/reject` | `DELETE /users/{id}/reject` | method错误 | 改为 DELETE |
| `LoginView.vue` | `POST /users/join` | `POST /tenants/join` | 路径错误 | 修改路径 |
| `utils/aiApi.js` | `API_BASE='/api/v1/ai'` + `http.baseURL='/api/v1'` | `'/ai/*'` | 前缀重复 | 去掉二次 `/api/v1` 前缀 |

## 5. 风险优先级
- P0（立即修复）：
  - `CaseDetailView.vue` 5 项
  - `LawyersView.vue` 4 项
  - `LoginView.vue` join 路径
  - `utils/aiApi.js` 双前缀
- P1（补充验证）：
  - 全站 401/403/404 的错误解析是否按 `code` 处理（衔接 FE-A06）

## 6. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A01-1 | 案件详情 API 对齐 | `src/views/CaseDetailView.vue` | 路径/method 修复 |
| A01-2 | 律师管理 API 对齐 | `src/views/LawyersView.vue` | 路径/method 修复 |
| A01-3 | 登录加入机构 API 对齐 | `src/views/LoginView.vue` | `/tenants/join` 对齐 |
| A01-4 | AI API 前缀修复 | `src/utils/aiApi.js` | 消除双 `/api/v1` |
| A01-5 | 页面回归验证 | `src/views/*` | 关键页面请求成功 |

## 7. 验收标准（DoD）
- Web 所有请求路径与方法与 `API-CONTRACTS.md` 一致。
- 不再出现 `404/405` 的契约性错误调用。
- AI 三链路（parse/analyze/falsify）发起与查询可达。
- 不修改 UI 层表现，仅改接口对齐相关代码。

## 8. 回滚策略
1. 每个页面改动独立提交，出现问题可按页面粒度回退。
2. 优先保留原交互逻辑，仅替换 API 调用细节。
3. 回滚后保留审计矩阵，避免重复引入旧路径。

## 9. 预估工作量
- 审计确认：0.5 人日
- 修复与联调：1 人日
- 回归验证：0.5 人日
- 合计：2 人日
