# FE-A04 执行单：AI 任务状态展示口径统一

## 1. 任务目标
- 统一 AI 状态码在 Web/小程序的展示语义，确保与后端状态机一致。
- 修复当前前端状态映射错位（`running` vs `processing`）造成的显示偏差。
- 保持 UI 样式不变，仅调整状态映射与文案来源。

## 2. 现状基线（代码事实）
- 后端任务状态机：`pending -> processing -> completed|failed`。
- Web `TaskProgress.vue` 仍使用 `running` 映射文案，和后端 `processing` 不一致。
- `DocumentParsing.vue` 使用 `currentTask.status === 'running'` 控制图标状态。
- 证伪严重级别映射存在双口径：
  - 后端：`critical/major/minor`
  - Web 代码中另有 `low/medium/high` 分支。

## 3. 统一映射规范

## 3.1 任务状态
- `pending` -> `等待中`
- `processing` -> `处理中`
- `completed` -> `已完成`
- `failed` -> `处理失败`

## 3.2 证伪严重度
- `critical` -> `严重风险`
- `major` -> `高风险`
- `minor` -> `中低风险`

## 4. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A04-1 | 任务状态映射常量统一 | `src/components/ai/TaskProgress.vue`、`src/views/ai/*` | 单一状态字典 |
| A04-2 | `running` 兼容迁移 | `src/components/ai/TaskProgress.vue` | 兼容旧值并切新值 |
| A04-3 | 证伪 severity 映射统一 | `src/views/ai/Falsification.vue` | critical/major/minor 一致 |
| A04-4 | 小程序页面映射对齐 | `mini-program/pages/ai/*.vue` | 双端展示一致 |

## 5. 验收标准（DoD）
- 后端四种状态在 Web/小程序展示一致。
- 不再出现 `running` 专用分支导致的进度显示异常。
- 证伪结果严重级别文案与后端字段严格对齐。
- 不发生 UI 样式与布局变化。

## 6. 风险与默认策略
- 风险：历史数据可能仍存 `running`。  
  默认策略：短期兼容 `running -> processing` 映射。
- 风险：多页面重复定义映射导致再次漂移。  
  默认策略：抽取共享映射常量，禁止页面硬编码。

## 7. 回滚策略
1. 状态字典调整可单文件回滚，不影响接口调用。
2. 若映射异常，先恢复兼容映射再定位字段源头。

## 8. 预估工作量
- 改造：0.5 人日
- 联调回归：0.5 人日
- 合计：1 人日
