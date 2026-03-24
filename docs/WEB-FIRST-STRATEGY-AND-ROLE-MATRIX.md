# Web 先测策略与角色权限四维矩阵

> 目标：基于当前仓库代码现状，给出可执行的 Web 先测方案与角色权限矩阵，不编写业务代码。

## 一、任务 A：Web 先测再对接小程序的实施方案

### A.1 为什么 Web 先测再对接小程序是更优落地方案

1. **共享 API 先收敛可减少双端返工**：当前 Web 与小程序共用 `/api/v1`，先在 Web 端完整压测接口契约，能提前发现字段、状态码、分页等问题，避免在双端重复修复。
2. **问题定位效率更高**：Web 调试链路短、可观测性高，先在 Web 完成接口与权限验证，可显著降低小程序联调阶段的问题噪声。
3. **权限基线可先固化**：后端已有角色/租户校验，Web 路由守卫也较完整，先在 Web 建立权限回归基线再接小程序，风险更可控。
4. **小程序特有约束可集中处理**：端来源头、微信登录绑定、上传策略和 WS 行为属于小程序特性，放在第二阶段聚焦处理更稳。
5. **回归路径更清晰**：先形成 Web 基线回归，再做小程序增量回归，便于快速判断是后端回归还是端适配问题。

### A.2 Web 端测试矩阵（角色 × 功能模块）

| 角色 | 功能模块 | 测试点 | 预期结果 | 验证方式 |
|---|---|---|---|---|
| tenant_admin | 登录与身份 | 登录后访问管理与业务主页面 | 登录成功，可访问机构管理能力 | UI + `GET /api/v1/users/me` |
| tenant_admin | 机构管理 | 成员审批、律师管理、统计 | 可成功调用管理接口 | Network + 状态码/响应体 |
| tenant_admin | 案件管理 | 创建、查看、更新案件 | 可创建并更新本租户案件 | `POST/GET/PATCH /api/v1/cases*` |
| lawyer | 案件流程 | 列表、详情、状态更新 | 可访问本租户案件，按负责人规则更新 | `GET/PATCH /api/v1/cases*` |
| lawyer | 文件流程 | 上传策略、上传、列表、下载 | 文件链路可用 | `GET /files/upload-policy` `POST /files/upload` `GET /files/case/{id}` |
| lawyer | AI 流程 | 解析、分析、证伪、任务查询、重试 | AI 任务创建成功，状态可查询，结果可读 | `/api/v1/ai/*` + WS |
| lawyer | 邀请二维码 | Web 端调用邀请码二维码接口 | **当前应返回 403（预期）**，因仅允许小程序来源 | `GET /api/v1/cases/{id}/invite-qrcode` |
| solo_lawyer 映射账号 | 案件可见性 | personal 租户下查看案件列表 | 仅返回与本人上传文件关联案件 | `GET /api/v1/cases` 数据比对 |
| solo_lawyer 映射账号 | 案件详情越权 | 访问非本人关联案件详情 | 期望禁止；当前需重点核验缺口 | `GET /api/v1/cases/{id}` 越权测试 |
| solo_lawyer 映射账号 | AI 能力 | 有效/无效订阅或余额两种场景 | 有效可调用，无效返回 403 | `/api/v1/ai/*` |
| client | Web 访问 | 登录后尝试进入 Web 业务路由 | 应被前端守卫拦截到提示页 | Router 行为 + 页面跳转 |
| client | 数据边界 | 拉取案件/文件 | 仅本人案件和文件可见 | `GET /cases` `GET /files/case/{id}` |
| client | 上传端来源 | 不带 mini 头调用上传策略 | 应 403；带 mini 头应通过 | Header 对照测试 |

### A.3 小程序对接策略（Mock → 联调 → 回归）

| 阶段 | 目标 | 里程碑 | 切换条件 |
|---|---|---|---|
| Mock 阶段 | 页面状态流与错误处理跑通 | 登录、案件、AI 页面状态机可演示 | Web 基线矩阵通过，API 契约稳定 |
| 联调阶段 | 切换真实 `/api/v1` | 微信登录绑定、邀请进案、上传、AI WS 打通 | 端来源头、鉴权头、幂等键、WS token 全通过 |
| 回归阶段 | 双端一致性与权限边界回归 | 四角色主流程回归通过 | 无 P0/P1 权限偏差，回归清单签收 |

```mermaid
flowchart LR
A[Web基线通过] --> B[小程序Mock]
B --> C[小程序联调]
C --> D[双端回归]
D --> E[发布冻结]
```

### A.4 接口兼容性约束（Web 与小程序共用接口）

| 维度 | 约束 | 现状要点 | 风险与约束结论 |
|---|---|---|---|
| 字段契约 | 统一以后端 schema 为准 | 以 `/api/v1` 响应为单一真源 | 禁止双端各自私有字段解释 |
| 鉴权 | Bearer JWT 必填 | JWT 含 `tenant_id` `role` `is_tenant_admin` | 401 处理逻辑需双端一致 |
| 端来源 | 小程序默认发送 `X-Client-Platform` 与 `X-Client-Source` | Web 默认不发送 | Web 不得调用 mini-only 接口 |
| mini-only 接口 | 邀请二维码必须 mini 来源 | `GET /cases/{id}/invite-qrcode` 已后端强制 | Web 调用失败应视为预期 |
| client 上传策略 | client 调上传相关接口需 mini 来源 | `upload-policy`/`upload` 对 client 强制 | 避免仅前端提示，需按后端规则联调 |
| 分页参数 | 统一分页参数口径 | 已支持兼容但建议统一写法 | 双端统一使用 `page/page_size` |
| AI 幂等 | 发起任务建议统一带幂等键 | 后端支持 `Idempotency-Key` | 避免重试导致重复任务 |
| WS 权限 | WS 订阅需 token 且有角色限制 | client 禁止订阅 AI 任务 WS | 保留轮询兜底策略 |

### A.5 里程碑与时间节点建议（今天可落地 vs 下一迭代）

**今天可落地**
1. 固化并执行 Web 测试矩阵首轮冒烟（含预期 403 用例）。
2. 形成小程序联调前置清单：headers、token、幂等键、WS。
3. 建立权限现状台账：后端已实现、前端守卫、待实现。
4. 锁定 API 契约快照作为联调基线。

**下一迭代**
1. 补齐 `solo_lawyer` 的后端强约束语义。
2. 收敛 client 端来源策略为后端统一规则，减少仅前端守卫。
3. 建立双端统一回归门禁清单。
4. 清理 Web 对 mini-only 接口的调用入口。

---

## 二、任务 B：角色权限与功能清单（四维矩阵）

> 角色说明：`solo_lawyer` 当前无独立后端 role，现状按 `role=lawyer` + `tenant.type=personal` 近似承载。

### B.1 角色 × 菜单/页面

标记：可访问=✅；不可访问=❌；部分可访问=◐。

| 菜单/页面 | tenant_admin | lawyer | solo_lawyer | client | 现状判定 |
|---|---:|---:|---:|---:|---|
| Web 登录页 | ✅ | ✅ | ✅ | ✅ | 已实现 |
| Web 业务主区 | ✅ | ✅ | ✅ | ❌ | client 由前端路由拦截 |
| Web 管理页（机构/成员/统计） | ✅ | ❌ | ❌ | ❌ | 后端管理员校验 + 前端守卫 |
| Web 案件列表 | ✅ | ✅ | ◐ | ❌ | solo 在 personal 下仅列表受限 |
| Web 案件详情 | ✅ | ✅ | ◐ | ❌ | solo 详情边界存在待补点 |
| Web AI 页面 | ✅ | ✅ | ◐ | ❌ | solo 受订阅或余额条件 |
| 小程序律师页 | ✅ | ✅ | ✅（现状） | ❌ | solo 仅 Web 目标未落地 |
| 小程序当事人页 | ❌ | ❌ | ❌ | ✅ | 已按角色分流 |
| 小程序 AI 页 | ✅ | ✅ | ✅（现状） | ❌ | client 不可用 |

### B.2 角色 × 接口（路径）

标记：可调用=✅；禁止=❌；条件可调用=◐。

| 接口路径 | tenant_admin | lawyer | solo_lawyer | client | 状态 |
|---|---:|---:|---:|---:|---|
| `POST /api/v1/auth/login` | ✅ | ✅ | ✅ | ✅ | 已实现 |
| `POST /api/v1/auth/wx-mini-login` | ✅ | ✅ | ✅ | ✅ | 已实现 |
| `GET /api/v1/users/me` | ✅ | ✅ | ✅ | ✅ | 已实现 |
| `GET/POST /api/v1/users/lawyers` | ✅ | ❌ | ❌ | ❌ | 后端管理员强约束 |
| `GET /api/v1/users/pending` | ✅ | ❌ | ❌ | ❌ | 后端管理员强约束 |
| `PATCH /api/v1/users/{id}/approve` | ✅ | ❌ | ❌ | ❌ | 后端管理员强约束 |
| `GET /api/v1/stats/dashboard` | ✅ | ❌ | ❌ | ❌ | 后端管理员强约束 |
| `POST /api/v1/cases` | ✅ | ✅ | ✅ | ❌ | 后端角色限制已实现 |
| `GET /api/v1/cases` | ✅ | ✅ | ◐ | ✅ | solo 与 client 有数据范围限制 |
| `GET /api/v1/cases/{id}` | ✅ | ✅ | ◐ | ◐ | client 本人限制已实现；solo 仍需补强 |
| `PATCH /api/v1/cases/{id}` | ✅ | ◐ | ◐ | ❌ | 负责人或管理员可更新 |
| `GET /api/v1/cases/{id}/invite-qrcode` | ◐ | ◐ | ◐ | ❌ | 需 lawyer/admin + mini 来源 |
| `GET /api/v1/files/upload-policy` | ✅ | ✅ | ✅ | ◐ | client 必须 mini 来源 |
| `POST /api/v1/files/upload` | ✅ | ✅ | ✅ | ◐ | client 必须 mini 来源 |
| `GET /api/v1/files/case/{id}` | ✅ | ✅ | ◐ | ◐ | client 本人边界已实现；solo 需补强 |
| `POST /api/v1/ai/cases/{id}/parse-document` | ✅ | ✅ | ◐ | ❌ | solo 取决订阅或余额 |
| `POST /api/v1/ai/cases/{id}/analyze` | ✅ | ✅ | ◐ | ❌ | 同上 |
| `POST /api/v1/ai/cases/{id}/falsification` | ✅ | ✅ | ◐ | ❌ | 同上 |
| `GET /api/v1/ai/tasks/{task_id}` | ✅ | ✅ | ✅ | ❌ | client 禁止 |
| `POST /api/v1/ai/tasks/{task_id}/retry` | ✅ | ✅ | ◐ | ❌ | solo 取决订阅或余额 |
| `GET /api/v1/ws/ai/tasks/{task_id}` | ✅ | ✅ | ✅ | ❌ | client 被后端禁止 |

### B.3 角色 × 数据权限

| 数据域 | tenant_admin | lawyer | solo_lawyer | client | 现状 |
|---|---|---|---|---|---|
| 租户边界 | 仅本租户全量 | 仅本租户 | 仅本租户 | 仅本租户 | 后端已实现 |
| 案件列表 | 本租户全量 | 本租户可见 | 仅本人上传关联案件 | 仅本人案件 | 基本已实现 |
| 案件详情 | 本租户全量 | 本租户可见 | 目标应仅本人关联 | 仅本人案件 | solo 待补强 |
| 文件可见性 | 本租户可见 | 本租户可见 | 目标应仅本人关联 | 仅本人案件文件 | solo 待补强 |
| AI 发起 | 可发起 | 可发起 | 订阅有效或余额足够可发起 | 禁止 | 已实现 |
| AI 结果读取 | 可读 | 可读 | 可读 | 部分可读 | client 对证伪结果禁止已实现 |
| 成员管理数据 | 可管理 | 禁止 | 禁止 | 禁止 | 已实现 |

### B.4 角色 × 端

| 角色 | Web 可用 | 小程序可用 | 结论 |
|---|---|---|---|
| tenant_admin | ✅ | ✅ | 双端可用 |
| lawyer | ✅ | ✅ | 双端可用 |
| solo_lawyer | ✅ | ✅（现状） | 目标仅 Web，当前未实现 |
| client | ◐（仅提示页） | ✅ | Web 业务不可用主要依赖前端守卫 |

---

## 三、实现状态汇总

### 3.1 后端已实现

- 角色与租户鉴权基础能力。
- 管理员能力的后端强约束。
- client 在上传相关接口的 mini 来源强约束。
- 邀请二维码接口 mini 来源强约束。
- 案件与 AI 关键角色限制。
- client 禁止 AI WS 订阅。

### 3.2 仅前端守卫

- client Web 业务页不可访问（路由拦截与提示页）。
- 小程序页面级角色跳转守卫。
- `solo_lawyer` 目标端限制仅在产品策略层，非后端强约束。

### 3.3 待实现

1. `solo_lawyer` 独立角色语义与后端强鉴权模型。
2. `solo_lawyer` 在案件详情与文件详情的仅本人关联强约束。
3. client 业务接口 mini-only 的统一后端策略化。
4. Web 端对 mini-only 接口调用入口的清理与防误用。

---

## 四、关键依据文件

- `backend/app/dependencies/auth.py`
- `backend/app/api/routes_cases.py`
- `backend/app/api/routes_files.py`
- `backend/app/api/routes_users.py`
- `backend/app/api/routes_stats.py`
- `backend/app/services/ai.py`
- `backend/app/api/routes_ws_ai.py`
- `backend/tests/test_role_access_contracts.py`
- `web-frontend/src/router/index.js`
- `mini-program/common/http.js`
- `mini-program/pages/`
