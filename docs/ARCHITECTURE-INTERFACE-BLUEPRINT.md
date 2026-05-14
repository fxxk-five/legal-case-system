# 架构与接口蓝图

## 运行时组成

- `web-frontend`：Web 管理台，面向超级管理员、机构管理员、律师。
- `mini-program`：微信小程序，面向律师移动端与当事人端。
- `backend`：统一 API 与业务中台。
- `ai-worker`：消费 AI 任务队列。
- `report-service`：报告渲染服务。
- `postgres` + `redis`：持久化与缓存/辅助依赖。

## 当前代码结构

### 后端

- 统一入口：`backend/app/main.py`
- API 聚合：`backend/app/api/api_v1.py`
- 业务模块：`backend/app/modules/*`
  - `auth`
  - `cases`
  - `clients`
  - `files`
  - `ai`
  - `analytics`
  - `notifications`
  - `asr`
  - `tenants`
  - `users`
- 外部集成：`backend/app/integrations/*`
  - `llm`
  - `wechat`
  - `storage`
  - `sms`
  - `report`
  - `asr`

### Web

- 入口：`web-frontend/src/app/App.vue`
- 路由：`web-frontend/src/app/router/index.js`
- 页面：`web-frontend/src/pages/*`
- 结构目标：`app / pages / features / entities / shared`

### 小程序

- 页面配置：`mini-program/pages.json`
- 页面：`mini-program/pages/*`
- 公共层：`mini-program/features`、`mini-program/entities`、`mini-program/shared`

## 核心业务链路

1. 用户登录并按角色进入对应工作台。
2. 律师或机构管理员创建案件。
3. 当事人通过邀请进入小程序并上传材料。
4. 文件进入案件上下文并触发 AI 任务。
5. `ai-worker` 消费任务，结果回写到案件与报告。
6. 律师查看完整结果；当事人只看摘要和本人可见内容。

## 接口域划分

- 认证与会话：`/api/v1/auth/*`
- 租户与用户：`/api/v1/tenants/*`、`/api/v1/users/*`
- 案件与当事人：`/api/v1/cases/*`、`/api/v1/clients/*`
- 文件与报告：`/api/v1/files/*`、`/api/v1/cases/{id}/files*`、`/api/v1/cases/{id}/report*`
- AI 与进度：`/api/v1/ai/*`、`/ws/ai/tasks/{task_id}`
- 统计与通知：`/api/v1/stats/*`、`/api/v1/analytics/*`、`/api/v1/notifications/*`

## 当前前端边界

- Web `/analysis` 当前重定向到 `overview`。
- Web `cases/:id/ai/analyze` 与 `cases/:id/ai/falsify` 当前都重定向到文档解析页。
- 当事人 Web 端不提供业务工作台，只显示“小程序使用提示页”。
- 个人工作区律师仅保留案件相关入口。

## 生产部署边界

- 当前生产基线使用 `docker-compose.prod.yml`。
- 对外仅开放 `80/443`。
- 文件真源使用 `COS`，AI 任务使用数据库队列 + `ai-worker`。
