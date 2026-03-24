# FE-A08 执行单：小程序 API 封装与 Web 对齐

## 1. 任务目标
- 统一小程序与 Web 的 API 封装口径，保证同一业务接口“双端路径/参数/响应解析一致”。
- 固化双端差异边界（仅传输层差异，业务语义一致）。
- 不改 UI，仅做接口封装对齐。

## 2. 现状基线（代码事实）
- 小程序已在 `mini-program/common/http.js` 封装 AI 接口，路径整体与后端契约基本一致。
- Web 存在 `aiApi.js` 前缀问题与部分页面绕过统一封装的情况。
- 双端在字段归一化函数上有重复实现，维护成本高。

## 3. 双端对齐规则
- 路径与方法：完全以 `docs/API-CONTRACTS.md` 为准。
- 参数命名：对外 snake_case；端内可 camelCase，但必须在 API 封装层转换。
- 响应适配：统一在 API 封装层做 normalize，不在页面层散落转换逻辑。
- 错误处理：优先按 `code` 解析（衔接 FE-A06）。

## 4. 双端接口对照（AI 核心）
| 能力 | 后端契约 | Web 封装 | Mini 封装 | 对齐要求 |
|---|---|---|---|---|
| 文档解析 | `POST /ai/cases/{id}/parse-document` | `start/parse` | `parseDocument` | 路径一致、入参一致 |
| 事实列表 | `GET /ai/cases/{id}/facts` | `getCaseFacts` | `getCaseFacts` | 分页参数一致 |
| 法律分析 | `POST /ai/cases/{id}/analyze` | `startAnalysis` | `startAnalysis` | options 语义一致 |
| 分析结果 | `GET /ai/cases/{id}/analysis-results` | `getAnalysisResults` | `getAnalysisResults` | normalize 一致 |
| 证伪发起 | `POST /ai/cases/{id}/falsification` | `startFalsification` | `startFalsification` | `analysis_id` 一致 |
| 证伪结果 | `GET /ai/cases/{id}/falsification-results` | `getFalsificationResults` | `getFalsificationResults` | 字段映射一致 |
| 任务状态 | `GET /ai/tasks/{task_id}` | `getTaskStatus` | `getTaskStatus` | 状态字段一致 |

## 5. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A08-1 | 双端 API 对齐清单落地 | `docs/tasks` | 接口对照表 |
| A08-2 | Web API 封装修复 | `web-frontend/src/utils/aiApi.js` | 路径与参数对齐 |
| A08-3 | 小程序封装补齐 | `mini-program/common/http.js` | normalize 与错误处理对齐 |
| A08-4 | 共享映射策略文档 | `docs/` | 双端字段/错误码统一规则 |

## 6. 验收标准（DoD）
- 同一接口在 Web 与小程序行为一致（请求参数、响应解析、错误处理）。
- 双端 API 封装可独立被页面调用，页面不再关心后端细节。
- AI 三链路双端均可完成发起、轮询/WS、结果展示。

## 7. 风险与默认策略
- 风险：双端历史差异导致一次性统一难度高。  
  默认策略：先统一 AI 核心链路，再扩展到 cases/files/users。
- 风险：字段兼容逻辑散落造成后续漂移。  
  默认策略：所有 normalize 集中在封装层。

## 8. 回滚策略
1. 双端按模块改造，单模块异常可单独回退。
2. 保留旧封装函数别名短期兼容。

## 9. 预估工作量
- 对齐改造：1 人日
- 联调回归：0.5 人日
- 合计：1.5 人日
