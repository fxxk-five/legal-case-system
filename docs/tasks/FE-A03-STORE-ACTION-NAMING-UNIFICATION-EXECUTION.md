# FE-A03 执行单：Store Action 命名统一

## 1. 任务目标
- 统一 AI store action 命名，消除“调用名与实现名不一致”导致的运行时错误。
- 建立 action 命名规范，确保页面调用、store、api-client 一一对应。
- 仅改接口对齐相关代码，不改 UI 展示逻辑。

## 2. 现状基线（代码事实）
- `src/stores/ai.js` 已实现：
  - `startAnalysis`
  - `startFalsification`
  - `parseDocument`
- 但页面存在调用：
  - `LegalAnalysis.vue` 使用 `aiStore.analyzeCase(...)`（不存在）
  - `Falsification.vue` 使用 `aiStore.falsifyCase(...)`（不存在）
- 结果：页面操作触发时直接报错，AI 链路中断。

## 3. 命名规范（建议）
- 发起任务：统一前缀 `start*`
  - `startParseDocument`
  - `startAnalysis`
  - `startFalsification`
- 查询列表：统一前缀 `fetch*`
  - `fetchCaseFacts`
  - `fetchAnalysisResults`
  - `fetchFalsificationResults`
- 查询任务：`fetchTaskStatus`

> 兼容策略：短期可保留别名方法（如 `analyzeCase` -> `startAnalysis`）避免页面一次性改动过大。

## 4. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A03-1 | 定义命名规范文档 | `docs/tasks` 或 `docs/` | store action 命名表 |
| A03-2 | store action 重命名/别名 | `src/stores/ai.js` | 规范命名 + 兼容别名 |
| A03-3 | 页面调用对齐 | `src/views/ai/*.vue` | 调用名一致 |
| A03-4 | 任务状态查询命名统一 | `stores/composables` | `fetchTaskStatus` 对齐 |

## 5. 验收标准（DoD）
- AI 三个页面调用的 store action 全部存在且可执行。
- 不再出现同义双命名（如 `analyzeCase` 与 `startAnalysis` 并行无说明）。
- 命名规则有文档，后续新增 action 可复用。

## 6. 风险与默认策略
- 风险：重命名引发全局引用断裂。  
  默认策略：先加别名兼容，再逐步替换引用。
- 风险：store 与 api-client 命名继续漂移。  
  默认策略：命名规范中要求“store action 与 api-client 函数语义一一映射”。

## 7. 回滚策略
1. 保留旧方法别名，支持快速回退调用方。
2. 若上线报错，优先恢复别名而非回退整页逻辑。

## 8. 预估工作量
- 命名与改造：0.5 人日
- 联调回归：0.5 人日
- 合计：1 人日
