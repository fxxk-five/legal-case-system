# R00 接口兼容映射（兼容优先）

> 版本：2026-03-22
> 策略：保留当前可用旧路径；并行补齐蓝图标准路径；标准路径稳定后再做灰度下线。

## 1. 映射表

| 领域 | 旧路径（已存在） | 标准路径（蓝图） | 当前状态 | 备注 |
| --- | --- | --- | --- | --- |
| 案件列表 | `GET /api/v1/cases` | `GET /api/v1/cases` | 已对齐 | 无差异 |
| 案件详情 | `GET /api/v1/cases/{case_id}` | `GET /api/v1/cases/{case_id}` | 已对齐 | 无差异 |
| 创建案件 | `POST /api/v1/cases` | `POST /api/v1/cases` | 已对齐 | 已支持“手填优先，空值自动生成案号” |
| 文件列表 | `GET /api/v1/files/case/{case_id}` | `GET /api/v1/cases/{case_id}/files` | 已补齐（BE09） | 新旧路径同语义，旧路径继续可用 |
| 文件上传 | `POST /api/v1/files/upload?case_id={id}` | `POST /api/v1/cases/{case_id}/files` | 已补齐（BE09） | 新旧路径同语义，旧路径继续可用 |
| 上传策略 | `GET /api/v1/files/upload-policy?case_id={id}` | `GET /api/v1/cases/{case_id}/files/upload-policy` | 已补齐（BE09） | 新旧路径同语义，旧路径继续可用 |
| 报告下载（最新） | （无统一标准入口） | `GET /api/v1/cases/{case_id}/report` | 已完成（BE09+BE10+BE11） | 按角色模板返回：律师侧最新律师版；当事人侧最新当事人版 |
| 报告版本列表 | （无） | `GET /api/v1/cases/{case_id}/reports` | 已补齐（BE11） | 律师返回历史列表；当事人仅返回最新一条 |
| 指定历史报告下载 | （无） | `GET /api/v1/cases/{case_id}/reports/{report_name}` | 已补齐（BE11） | 仅律师可下载指定历史版本；当事人禁止 |
| 文件下载 | `GET /api/v1/files/{file_id}/download` | `GET /api/v1/files/{file_id}/download` | 已对齐 | BE03 会增加可见性控制 |

## 2. 兼容规则

1. 前端新开发默认调用标准路径；旧路径仅用于存量兼容。
2. 旧路径与标准路径返回结构保持一致，避免双维护字段。
3. 若旧路径与标准路径同时存在，统一走同一服务层逻辑。
4. 旧路径下线前至少保留一个稳定版本周期，并提供迁移通知。

## 3. 验收口径

- 旧路径不回归中断。
- 标准路径可用并与旧路径返回语义一致。
- OpenAPI 文档中明确标注“标准路径推荐 / 旧路径兼容”。
