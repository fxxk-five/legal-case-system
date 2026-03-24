# V3 双端同构验收矩阵

> 更新时间：2026-03-23  
> 目标：验证 Web 端与小程序律师端功能同构；小程序仅额外承载当事人端链路。  
> 对应任务：`V3-QA01`、`V3-QA02`

## 1. 验收范围

- Web 端：律师/机构管理员/超级管理员入口、案件管理、当事人管理、律师管理
- 小程序律师端：与 Web 端同一后端、同一权限模型、同一业务主链路
- 小程序当事人端：邀请注册、单案直达/多案列表、补充材料、进度查看、仅最新 PDF
- 后端：统一 API、多租户隔离、角色权限、AI 队列、报告可见性、预算熔断

## 2. 角色与菜单矩阵

| 角色 | Web 端 | 小程序律师端 | 小程序当事人端 | 验收要点 |
| --- | --- | --- | --- | --- |
| `tenant_admin` | 概览 / 案件管理 / 当事人管理 / 律师管理 | 概览 / 案件管理 / 当事人管理 / 律师管理 | 不适用 | 必须 4 菜单；可生成邀请、审批律师 |
| `lawyer` | 概览 / 案件管理 / 当事人管理 | 机构律师：概览 / 案件管理 / 当事人管理；独户律师：直达案件台 | 不适用 | Web 必须 3 菜单；独户律师与机构律师首页不同，不可进入律师管理 |
| `client` | 受限 | 受限 | 案件列表/案件详情/补充材料/邀请注册 | 只能看到本人案件，只能下载最新 PDF |
| `super_admin` | 后端能力已具备，前端视角后续扩展 | 暂无专属端 | 不适用 | 当前以 API 能力验收为主 |

## 3. 页面与接口同构矩阵

| 能力域 | Web 端页面 | 小程序页面 | 核心接口 | 自动化覆盖 | 人工验收 |
| --- | --- | --- | --- | --- | --- |
| 登录/刷新/登出 | `LoginView` | `pages/login/index` | `/auth/web-wechat-login*` `/auth/wx-mini-login` `/auth/wx-mini-phone-login` `/auth/refresh` `/auth/logout` | `scripts/qa02_full_e2e.py` | 浏览器 + HBuilderX |
| 概览 | `OverviewView` | `pages/lawyer/home` | `/users/me` `/tenants/current` `/stats/dashboard` | `scripts/qa02_full_e2e.py` | 核对增量卡片 |
| 案件管理 | `CasesView` `CaseDetailView` | `pages/lawyer/cases` `pages/lawyer/case-detail` | `/cases` `/cases/{id}` `/cases/{id}/files` | `scripts/qa02_full_e2e.py` | 检查 30/7 天预警色 |
| 当事人管理 | `ClientsView` | `pages/lawyer/clients` | `/clients` `/clients/{id}` `/clients/{id}` PATCH | `scripts/qa02_full_e2e.py` | 验证详情编辑与案件回跳 |
| 律师管理 | `LawyersView` | `pages/lawyer/lawyers` | `/users/lawyers` `/users/pending` `/users/{id}/approve` `/users/{id}/status` `/users/invite-lawyer` | `scripts/qa02_full_e2e.py`（管理员账号） | 检查邀请路径和审批结果 |
| AI 解析入口 | `DocumentParsing` | `pages/ai/document-parsing` | `/ai/cases/{id}/parse-document` `/ai/tasks/{id}` | `scripts/qa02_full_e2e.py` | 核对解析任务状态 |
| 当事人邀请注册 | Web 仅提供邀请入口 | `pages/client/entry` | `/cases/{id}/invite-qrcode` `/auth/wx-mini-login` `/auth/wx-mini-phone-login` | `scripts/qa02_full_e2e.py` | 用真实邀请码走一遍 |
| 当事人案件列表/详情 | 不适用 | `pages/client/case-list` `pages/client/case-detail` | `/cases` `/cases/{id}` `/ai/cases/{id}/analysis-results` | `scripts/qa02_full_e2e.py` | 检查单案直达 / 多案列表 |
| 当事人补材 | 不适用 | `pages/client/upload-material` | `/cases/{id}/files` | `scripts/qa02_full_e2e.py` | 检查聊天文件 / 相册图片 |
| 报告可见性 | `CaseDetailView` | 律师端 `case-detail` / 当事人端 `case-detail` | `/cases/{id}/report` `/cases/{id}/reports` `/cases/{id}/reports/{name}` | `scripts/smoke_report_visibility.py` `scripts/qa02_full_e2e.py` | 检查客户端仅最新、历史 403 |

## 4. 自动化执行清单

### 4.1 全链路 E2E

```bash
python scripts/qa02_full_e2e.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --lawyer-phone 13900000011 \
  --lawyer-password lawyer123456 \
  --tenant-code <可选> \
  --file-path upload-smoke.txt
```

通过标准：

- 创建案件成功
- 当事人可登录且只看到本人案件
- 当事人上传材料成功
- AI 解析完成
- 报告下载成功
- V3 扩展接口通过：概览、当事人管理、律师管理（管理员时）、AI 解析状态

### 4.2 报告可见性

```bash
python scripts/smoke_report_visibility.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --case-id <CASE_ID> \
  --lawyer-token <LAWYER_JWT> \
  --client-token <CLIENT_JWT>
```

### 4.3 主链路 Smoke

```bash
python scripts/smoke_core_chain.py \
  --base-url http://127.0.0.1:8000/api/v1 \
  --lawyer-token <LAWYER_JWT> \
  --client-token <CLIENT_JWT可选> \
  --case-id <CASE_ID可选> \
  --file-path upload-smoke.txt
```

## 5. 人工验收清单

### 5.1 Web 端

- `tenant_admin` 登录后必须看到 4 菜单；`lawyer` 必须只看到 3 菜单
- 概览页显示登录用户信息、机构信息、增量卡片
- 案件列表支持 `legal_type`、状态、排序、截止时间预警色
- 当事人详情可编辑姓名/手机号，并能回跳案件详情
- 律师管理可生成邀请、审批待加入成员、启停账号
- 旧 `分析管理`、`法律分析`、`证伪` 入口不应出现在正式导航和案件详情按钮中

### 5.2 小程序律师端

- 机构律师菜单与 Web 端同构，独户律师默认直达案件台
- 当事人管理、律师管理与 Web 端字段保持一致
- 从当事人详情进入案件详情后，返回应回到当事人详情或上一页
- 旧 `分析管理`、`法律分析`、`证伪` 入口不应出现在正式导航和案件详情按钮中

### 5.3 小程序当事人端

- 邀请路径能自动带入 `scene/token`，不再要求短信注册
- 单案件直达详情；多案件进入列表
- 案件详情展示概览、时间流、AI 摘要、材料列表、最新 PDF 下载
- 补充材料支持聊天/本地文件与相册图片
- 材料部分失败时保留失败项，不应误跳回详情

## 6. 通过判定

全部满足以下条件才算 V3 QA 通过：

- 自动化：`qa02_full_e2e.py`、`smoke_report_visibility.py`、`smoke_core_chain.py` 全部通过
- 人工：Web 与小程序律师端同构菜单、同构页面、同构核心操作无明显差异
- 当事人端：邀请注册、补材、进度、最新 PDF 下载完整可用
- 权限：客户端历史报告下载返回 `403`；非管理员不能进入律师管理
- 数据：Web 与小程序显示的案件、文件、时间流、分析结果来自同一后端
