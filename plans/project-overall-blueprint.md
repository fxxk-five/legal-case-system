# 法律案件系统总体蓝图

> 本目录只保留这一份长期有效的总蓝图。  
> 当前实现状态请看 `docs/current-project-status.md`，上线门禁请看 `docs/final-acceptance-checklist.md`。

## 1. 项目目标

- 用一个后端同时服务 Web 管理台与微信小程序。
- 让律师与机构管理员完成案件协作、材料管理、AI 辅助分析。
- 让当事人只在最小操作路径里完成登录、补材、补充说明与查看结果。

## 2. 角色与终端边界

| 角色 | Web | 小程序 | 目标边界 |
| --- | --- | --- | --- |
| `super_admin` | ✅ | ❌ | 只做平台级租户、用户、预算治理 |
| `tenant_admin` | ✅ | ✅ | 管机构内案件、成员、分析管理 |
| `lawyer` | ✅ | ✅ | 办案、上传、备注、查看 AI 结果 |
| 个人工作区律师 | ✅ | ✅ | 仅保留案件相关入口 |
| `client` | ◐ 仅提示页 | ✅ | 只做本人案件协作，不进入 Web 工作台 |

## 3. 产品主链路

1. 管理员或律师创建案件。
2. 系统生成邀请，促使当事人进入小程序。
3. 当事人登录并自动绑案，上传材料与补充说明。
4. 后端统一管理文件、案件状态、时间流与 AI 任务。
5. 律师查看完整结果；当事人只查看摘要与本人可见文件。

## 4. 当前架构基线

### 后端

- 统一入口：`backend/app/main.py`
- 聚合路由：`backend/app/api/api_v1.py`
- 领域结构：`backend/app/modules/*`
- 外部能力：`backend/app/integrations/*`

### Web

- 入口：`web-frontend/src/app/App.vue`
- 路由：`web-frontend/src/app/router/index.js`
- 结构方向：`app / pages / features / entities / shared`

### 小程序

- 页面配置：`mini-program/pages.json`
- 结构方向：`pages / features / entities / shared`

### 部署

- 当前生产基线：`docker-compose.prod.yml`
- 运行拓扑：`nginx + web-frontend + backend + ai-worker + report-service + postgres + redis`
- 文件真源：腾讯云 `COS`

## 5. 冻结业务边界

### 角色可见性

- 当事人只访问本人案件。
- 个人工作区律师不显示机构型管理入口。
- 超级管理员不进入案件域。

### 文件与报告

- 律师 / 机构管理员可查看完整案件文件与完整报告。
- 当事人只能下载本人可见文件，且只看最新报告。
- 文件下载必须走授权链路，不走裸存储地址。

### AI 能力

- 当前 Web 以“文档解析页”为主入口。
- 小程序律师端可看分析结果；当事人只看摘要。
- 上传补材后允许自动重分析。

## 6. 当前上线目标

本轮不是继续扩张功能，而是完成“可上线收口”：

1. 腾讯云 `CVM + COS + HTTPS + 域名` 联通。
2. 微信平台配置与真机联调闭环。
3. 云端 smoke、E2E、回滚与 `Go / No-Go` 闭环。

## 7. 非本轮阻塞项

以下内容重要，但不应阻塞当前正式上线收口：

- 概览增量卡片继续扩展
- Web 分析管理页恢复正式入口
- 订阅 / 账单 / 欠费闭环
- 更深层的双端共享抽象
- 更大规模的基础设施演进

## 8. 执行优先级

### P0：上线前必须完成

- 微信真实配置
- 云资源、HTTPS、COS、合法域名
- 真机验收
- 云端端到端验证
- 回滚演练与最终放行

### P1：上线前建议完成

- AI 失败反馈与错误提示再收口
- 个别页面组件进一步拆分
- 统一错误文案与状态表达

### P2：上线后再推进

- 订阅计费系统
- 更深层领域共享
- 多机 / 负载均衡 / 集群演进

## 9. 配套真源

- 当前状态：`docs/current-project-status.md`
- 用户操作：`docs/user-manual.md`
- 接口契约：`docs/API-CONTRACTS.md`
- 本地联调：`docs/project-setup.md`
- 生产部署：`docs/production-deployment.md`
- 上线门禁：`docs/final-acceptance-checklist.md`
