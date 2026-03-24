# Blueprint Execution Status Board (V3)

> Updated: 2026-03-23  
> Baseline: `plans/project-overall-blueprint.md`（V3 第 15-22 章，双端同构版）

## 1. 当前结论

- V2 主链路（上传 -> 解析 -> 报告）已可本地联调通过。
- V3 代码收口已完成：Web/小程序律师端功能同构、小程序当事人附加链路、分析管理与当事人管理闭环均已落地。
- V3 QA 工件已补齐：自动化 E2E 扩展与双端同构验收矩阵已完成；当前进入 **本地部署 + 人工验收阶段**。
- V5 认证演进已完成核心代码：小程序微信直登、微信手机号绑定、多租户冲突分流、refresh session 撤销登出已落地；剩余微信平台配置、真机联调、全量 E2E/灰度回滚开关。

## 2. V3 对齐状态（按能力域）

| 能力域 | 状态 | 备注 |
| --- | --- | --- |
| 角色与准入（邀请注册+审批） | Completed | 已封禁组织租户开放加入与后台直建律师，统一走邀请注册。 |
| Web 角色化导航与页面差异 | Completed | `tenant_admin` 五菜单、`lawyer` 四菜单已按角色收口。 |
| 案件 `legal_type` 全链路 | Completed | 已覆盖 DB/Schema/API/自动案号/筛选排序。 |
| 截止时间 30/7 天预警规则 | Completed | Web 列表提醒规则已统一为 30/7。 |
| 概览“较上次登录增量卡片” | Completed | 已补 `previous_login_at` / `last_login_at` 与 `/stats/dashboard` 增量统计。 |
| 当事人管理（列表/详情/回跳） | Completed | 已提供独立 `/clients` 接口、详情编辑与案件回跳。 |
| 分析管理（用量+提示词+Provider） | Completed | 已补齐用量统计、提示词配置、Provider 设置与任务列表重试控制台。 |
| 小程序律师/管理员同构能力 | Completed | 已完成角色入口、概览、案件管理、当事人管理、律师管理与分析管理同构页面。 |
| 小程序当事人附加链路 | Completed | 已完成邀请注册、单案直达/多案列表、补材重解析进度跟踪、仅最新 PDF 下载与异常兜底。 |
| 双端同构验收矩阵 | Completed | 已新增 `docs/v3-dual-end-parity-matrix.md`，覆盖角色、菜单、页面、接口、自动化与人工验收。 |
| 本地部署可运行性 | Ready | Docker/迁移/worker/report-service 路径可用。 |
| 小程序微信直登与会话撤销 | In Progress | 核心 API、页面入口、logout revoke、自动化测试已完成；待微信平台配置与真机验收。 |

## 3. 已完成的基础能力（可复用）

- BE07：DB 队列 + worker（替代高成本 MQ）。
- BE08：解析进度与时间流同步。
- BE09：API 兼容路径收口。
- BE10：Node + Puppeteer 报告服务。
- BE11：律师可见历史、当事人仅最新报告。
- BE12：月预算上限 + 单案件上限 + 降级/停用熔断。
- FEM01/FEM04/FEM05：当事人详情结构、补材页、WS+轮询体验。
- AUTH refresh/logout：双端闭环。
- QA02：已升级全量自动化 E2E（后续扩展 V3 同构用例）。

## 4. V3 P0 剩余清单（执行中）

| 任务ID | 状态 | 对应蓝图章节 |
| --- | --- | --- |
| V3-BE01 邀请注册+审批强约束 | Completed | 16 |
| V3-BE02 `legal_type` 全链路 | Completed | 17.3 / 19 / 20.2 |
| V3-BE03 30/7 截止预警统一 | Completed | 15.2 / 17.3 |
| V3-BE04 上次登录增量统计 | Completed | 17.2 / 19.3 / 20.3 |
| V3-BE05 当事人管理接口闭环 | Completed | 17.5 / 20.2 |
| V3-BE06 分析管理接口闭环 | Completed | 17.7 / 20.3 |
| V3-FE01 角色导航 5/4 收口 | Completed | 17.1 |
| V3-FE02 案件页 legal_type + 预警色 | Completed | 17.3 |
| V3-FE03 概览增量卡片 | Completed | 17.2 |
| V3-FE04 当事人页闭环 | Completed | 17.5 |
| V3-FE05 分析管理控制台 | Completed | 17.7 |
| V3-MP01 小程序角色入口同构 | Completed | 18.1 |
| V3-MP02 小程序概览同构 | Completed | 18.2 |
| V3-MP03 小程序案件管理同构 | Completed | 18.2 |
| V3-MP04 小程序当事人管理同构 | Completed | 18.2 |
| V3-MP05 小程序律师管理同构 | Completed | 18.2 |
| V3-MP06 小程序分析管理同构 | Completed | 18.2 |
| V3-MP07 小程序当事人附加链路稳定化 | Completed | 18.3 |
| V3-MP08 小程序全角色 UI 风格统一 | Completed | 18.2 / 18.3 |
| V3-MP09 小程序交互逻辑收口 | Completed | 18.2 / 18.3 |
| V3-QA01 E2E 扩展 | Completed | 22 |
| V3-QA02 双端同构验收矩阵 | Completed | 22 |

## 5. 本地部署达标结论（当前）

- `docker compose` 路径可起服务，适合作为当前开发与联调基线。
- DB 队列模式可持续运行（不依赖云 MQ），满足低成本要求。
- 报告服务（BE10）已具备本地可验收条件。
- 已在本地跑通 `scripts/qa02_full_e2e.py`、`scripts/smoke_core_chain.py`、`scripts/smoke_report_visibility.py`。
- 未完成项主要是“HBuilderX / 微信开发者工具人工验收与平台差异收口”，不是“运行环境不可用”。

## 6. 下一执行批次（单人 + Codex）

1. 下一步转入 HBuilderX / 微信开发者工具人工验收，验证双端菜单、路由、上传、报告下载与返回链路。
2. 按 `docs/v3-dual-end-parity-matrix.md` 逐项勾验 Web vs Mini 的角色、页面、接口和权限。
3. 同步完成微信公众平台配置、合法域名与 `AppID/AppSecret` 落地，再执行 `scripts/smoke_wechat_direct_login.py` + 真机登录回归。
4. 若联调再暴露平台差异，优先修补小程序真机文件选择、上传 MIME、预览/下载兼容问题。

## 7. 安全加固波次 S1（2026-03-24）

| Task ID | 状态 | 说明 |
| --- | --- | --- |
| S1-01 环境安全基线校验 | Completed | 已在 `config.py` 增加生产/准生产环境校验：禁止默认 `SECRET_KEY`、禁止 `localhost` CORS、禁止 `AI_MOCK_MODE=True`。 |
| S1-02 Access Token 绑定 Session | Completed | 已在 `dependencies/auth.py` 按 `sid` 回查 `auth_sessions`，并在 `logout` 默认撤销当前 Access Session。 |
| S1-03 Mini 来源判定统一 | Completed | `routes_auth` 与 `dependencies/auth` 已统一为严格的 mini 请求头判定。 |
| S1-04 租户上下文跨事务重放 | Completed | `db/session.py` 已把租户上下文写入 `Session.info`，并在每个新事务开始时自动重放。 |
| S1-05 角色别名查询统一 | Completed | `role_values_for_query()` 已替换多处硬编码 `User.role.in_(["lawyer", "tenant_admin"])`。 |
| S1-06 文件访问入口加固 | Completed | 文件列表改为返回 `access-link`，本地访问令牌改为一次性消费，新增 `file_access_grants` 表。 |
| S1-07 AI 队列默认非阻塞 | Completed | `AI_DB_QUEUE_EAGER` 默认关闭，新增 `AI_DB_QUEUE_EAGER_BLOCKING` 控制仅测试/显式场景下阻塞执行。 |
| S1-08 AI 失败信息脱敏 | Completed | AI 任务对外只返回通用失败信息，不再透传原始异常文本。 |
| S1-09 短信 IP 限流 | Backlog | 当前仍只有手机号维度限流，需补充 IP/设备维度。 |
| S1-10 微信标识密文存储 | Backlog | 需要设计“密文列 + 检索哈希列”迁移方案。 |
| S1-11 注册租户显式选择 | Backlog | 需要移除单租户自动命中逻辑并补 UI/API 承接。 |
| S1-12 Async ORM 迁移评估 | Backlog | 作为架构级改造单独立项，不在本轮直接硬切。 |
