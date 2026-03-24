# FE-A09 执行单：字段命名边界规范（snake_case / camelCase）

## 1. 任务目标
- 明确双端字段命名边界，杜绝页面层混用 snake_case 与 camelCase。
- 统一“只在 API 客户端层做字段转换”的实现约束。
- 降低联调时字段名漂移与重复映射风险。

## 2. 现状基线（代码事实）
- 后端对外字段以 snake_case 为主。
- Web 与小程序已存在 normalize 逻辑，但页面层仍出现直接访问混合字段。
- 例如 AI 结果中 `result_data`、`fact_description`、`challenge_question` 兼容逻辑分散在多处。

## 3. 命名边界规则
- 后端接口输入输出：固定 snake_case（契约层）。
- API 封装层：
  - 对外返回给页面的对象可统一 camelCase（或约定继续 snake_case，需全局一致）。
  - 所有转换函数集中管理，不得散落在 view/store。
- 页面层：
  - 禁止直接写 `item.result_data || item.resultData` 这类双分支兼容。
  - 只使用封装层承诺的字段。

## 4. 转换策略建议
- 请求方向（前端 -> 后端）：
  - 组件/页面内部 camelCase -> API 前转换成 snake_case。
- 响应方向（后端 -> 前端）：
  - API 封装层一次性 normalize 后传给 store/view。
- 对兼容字段使用明确规则：
  - 例如 `fact_description <- challenge_question`
  - 统一写在映射函数，禁止页面重复写。

## 5. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A09-1 | 命名边界约定文档 | `docs/` | snake/camel 规范 |
| A09-2 | Web 映射收敛 | `web-frontend/src/utils/aiApi.js` | 单点 normalize |
| A09-3 | Mini 映射收敛 | `mini-program/common/http.js` | 单点 normalize |
| A09-4 | 页面层清理 | Web + Mini AI 页面 | 去除散落字段兼容分支 |

## 6. 验收标准（DoD）
- 页面层字段访问不再依赖双命名兜底逻辑。
- 所有字段转换集中在 API 封装层可追溯。
- 新增接口按同一命名规则开发，无临时分支。

## 7. 风险与默认策略
- 风险：一次性改命名触发大面积回归。  
  默认策略：先 AI 模块试点，再推广全站。
- 风险：团队成员命名习惯不一致。  
  默认策略：PR 模板增加“命名边界检查项”。

## 8. 回滚策略
1. 若统一命名后短期不稳定，API 层保留双字段输出兼容窗口。
2. 页面层仍只读取主字段，避免再次耦合兼容字段。

## 9. 预估工作量
- 规范与改造：0.5 人日
- 回归验证：0.5 人日
- 合计：1 人日
