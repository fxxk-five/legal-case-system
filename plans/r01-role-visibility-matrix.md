# R01 权限与可见性矩阵冻结

> 版本：2026-03-22
> 目标：冻结 `case_flows.visible_to` 与 `files.uploader_role` 的统一判定规则，直接可转测试用例。

## 1. case_flows.visible_to 规则

| visible_to | 律师端可见 | 当事人端可见 | 典型场景 |
| --- | --- | --- | --- |
| `lawyer` | 是 | 否 | 内部备注、内部任务调度 |
| `client` | 否（默认不需要） | 是 | 仅面向当事人的系统提醒 |
| `both` | 是 | 是 | 上传、解析开始/完成、需补充材料 |

查询口径：
- 律师端：`visible_to in ('lawyer', 'both')`
- 当事人端：`visible_to in ('client', 'both')`

## 2. files.uploader_role 规则

| uploader_role | 上传角色 | 律师端 | 当事人端 |
| --- | --- | --- | --- |
| `lawyer` | 律师/管理员 | 可见+可下载 | 仅显示文件名，不可下载 |
| `client` | 当事人 | 可见+可下载 | 可见；仅本人上传可下载/删除 |

## 3. 文件操作权限冻结

1. 当事人可删除自己上传的文件；不可删除律师上传文件。
2. 律师/管理员可删除本租户案件文件（后续结合更细粒度授权）。
3. 当事人端下载鉴权必须额外校验：
   - 文件属于本人案件；
   - 若 `uploader_role='lawyer'`，直接拒绝下载。

## 4. 报告可见性冻结（BE11）

| 场景 | 律师端 | 当事人端 |
| --- | --- | --- |
| `GET /api/v1/cases/{case_id}/report` | 返回“最新律师版”报告（无则按需生成） | 返回“最新当事人版”报告（无则按需生成） |
| `GET /api/v1/cases/{case_id}/reports` | 返回历史报告记录列表 | 仅返回最新 1 条 |
| `GET /api/v1/cases/{case_id}/reports/{report_name}` | 可下载指定历史版本 | 禁止访问（403） |

## 5. 字段落地约束

- `case_flows.visible_to`: `NOT NULL`，默认 `both`。
- `files.uploader_role`: `NOT NULL`，默认 `lawyer`。
- `files.parse_status`: `NOT NULL`，默认 `pending`。
- 历史数据回填：
  - `files.uploader_role`：`users.role='client'` 回填 `client`，否则回填 `lawyer`。
  - `files.parse_status`：空值回填 `pending`。

## 6. 测试断言（最小集）

- 当事人无法下载 `uploader_role='lawyer'` 的文件。
- 当事人只能删除自己上传文件。
- 时间流接口按 `visible_to` 过滤后无越权记录。
- 律师端仍可查看历史解析与操作记录。
- 当事人在仅存在律师版报告时，不可读到律师版报告内容。
- 当事人不可下载指定历史报告文件。
