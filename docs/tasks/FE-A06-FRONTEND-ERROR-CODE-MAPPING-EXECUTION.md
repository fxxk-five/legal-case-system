# FE-A06 执行单：错误码前端映射规范

## 1. 任务目标
- 建立 Web 与小程序统一的错误码映射规则，优先按 `code` 解析而非中文文案匹配。
- 对齐后端统一错误响应结构：`{code,message,detail,request_id}`。
- 保持 UI 展示风格不变，仅调整错误解析与映射逻辑。

## 2. 现状基线（代码事实）
- Web `extractFriendlyError` 主要读取 `detail`，未优先处理 `code`。
- 小程序 `friendlyError` 同样以 `detail/errMsg` 为主，缺少错误码字典。
- 风险：同一错误语义因文案变化导致前端提示不稳定。

## 3. 统一解析顺序（必须）
1. 若有 `code`，按 `code` 映射用户提示。
2. 若无 `code` 且 `detail` 为校验数组，按字段映射拼接提示。
3. 若有 `message`，使用 `message`。
4. 最后回退通用错误文案。

## 4. 错误码映射建议（首批）
- `AUTH_REQUIRED` -> 登录已失效，请重新登录
- `FORBIDDEN` / `CASE_ACCESS_DENIED` / `FILE_ACCESS_DENIED` -> 无权限执行该操作
- `CASE_NOT_FOUND` / `FILE_NOT_FOUND` / `AI_TASK_NOT_FOUND` -> 目标数据不存在或已删除
- `VALIDATION_ERROR` -> 提交信息有误，请检查后重试
- `CONFLICT` / `AI_TASK_CONFLICT` -> 请求冲突，请刷新后重试
- `INTERNAL_ERROR` / `EXTERNAL_SERVICE_ERROR` -> 服务暂时不可用，请稍后重试

## 5. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A06-1 | Web 错误码字典 | `web-frontend/src/lib/formMessages.js` | `code -> message` 映射 |
| A06-2 | 小程序错误码字典 | `mini-program/common/form.js` | 双端一致映射 |
| A06-3 | 校验错误解析统一 | Web + Mini 表单工具 | detail 数组解析一致 |
| A06-4 | request_id 暴露策略（可选） | 日志/调试输出 | 支持问题定位 |
| A06-5 | 回归测试清单 | `docs/tasks/FE-A10...` 关联 | 高频错误场景验证 |

## 6. 验收标准（DoD）
- Web/小程序对相同 `code` 输出一致提示口径。
- 文案轻微变化不影响错误分类与提示稳定性。
- 401 场景可稳定触发登录态处理。
- 不改 UI 风格，不增加新交互流程。

## 7. 风险与默认策略
- 风险：后端短期仍存在仅 HTTPException 文案场景。  
  默认策略：`code` 优先，文案次之，二者并存兼容。
- 风险：错误码新增后前端未覆盖。  
  默认策略：未识别 code 统一回退通用错误并记录日志。

## 8. 回滚策略
1. 保留旧 `detail` 解析逻辑，映射异常时可切回旧分支。
2. 分端灰度，先 Web 后小程序，降低风险。

## 9. 预估工作量
- 映射设计与改造：0.5 人日
- 联调与回归：0.5 人日
- 合计：1 人日
