# 发布前后工程落地作业单

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行。本作业单使用复选框 `- [ ]` 追踪节点状态。

**Goal:** 为当前仓库提供一份适合单人推进的统一作业单，覆盖放行前收口、正式上线、上线后首轮稳定期，以及稳定后切换 `dev` 分支的完整执行路径。

**Architecture:** 以 `docs/current-project-status.md` 作为状态真源，以 `docs/final-acceptance-checklist.md` 作为放行门禁，以本作业单作为日常推进顺序与留痕模板。执行顺序固定为阶段 A → B → C → D → E → F；同一时间只允许一个主节点处于 `进行中`；每个节点都必须独立验证、独立更新状态文档、独立提交。

**Tech Stack:** Git / PowerShell / Docker Compose / CVM / Nginx / HTTPS / 腾讯云 COS / 微信公众平台 / 微信开发者工具 / HBuilderX / `pytest` / `npm` / 仓库内门禁脚本

---

## 1. 使用方式

- [ ] 每次开始执行前，先阅读 `docs/current-project-status.md`、`docs/final-acceptance-checklist.md`、`docs/production-deployment.md`。
- [ ] 每天只允许一个主节点处于 `进行中`，其他节点只能标记为 `未开始`、`准备中`、`阻塞` 或 `已完成`。
- [ ] 每完成一个节点，立刻执行“验证 → 状态文档更新 → 精确暂存 → 独立提交”。
- [ ] 任何外部平台动作（云资源、微信平台、真机）也必须在本作业单留下验证结果与阻塞说明，不能只改平台不留痕。
- [ ] 如果遇到阻塞，先更新“阻塞登记模板”，再决定是否切换到下一个允许提前准备的节点。

## 2. 当前总顺序总览

| 阶段 | 节点 | 当前状态（初始） | 前置依赖 | 完成标志 |
| --- | --- | --- | --- | --- |
| A 基础设施收口 | `W12-T03` | 未开始 | 后端 / Web / 小程序本地基线全绿 | 正式域名、HTTPS、云主机可用 |
| A 基础设施收口 | `W12-T04` | 未开始 | `W12-T03` | COS、CORS、下载链路闭环 |
| A 基础设施收口 | `W12-T08` | 未开始 | `W12-T03`、`W12-T04` | 小程序合法域名联调通过 |
| B 微信 / 真机 | `WX-01` | 未开始 | 阶段 A 完成 | 微信真实能力闭环 |
| B 微信 / 真机 | `QA-03` | 未开始 | `WX-01` | 真机逐页验收通过 |
| C 云端联调 | `W12-V01 ~ W12-V06` | 未开始 | 阶段 A、B 完成 | 云端服务与主链路联调通过 |
| D 放行门禁 | `W13-T01 ~ W13-T08` | 未开始 | 阶段 C 完成 | Go / No-Go 结论形成 |
| E 首轮稳定期 | `POST-01 ~ POST-04` | 未开始 | 已正式上线 | 发布后 7 天稳定复核完成 |
| F 切换常规开发 | `DEV-01 ~ DEV-03` | 未开始 | 阶段 E 完成 | `dev` 分支启用并落地新流程 |

## 3. 执行前总控

### Task 1: 锁定当日执行基线

**Files:**
- Read: `docs/current-project-status.md`
- Read: `docs/final-acceptance-checklist.md`
- Read: `docs/project-setup.md`
- Read: `docs/production-deployment.md`
- Read: `docs/user-manual.md`

- [ ] **Step 1: 检查当前分支与工作区状态**
  - Run: `git branch --show-current`
  - Run: `git status --short`
  - Run: `git diff --cached --name-only`
  - Expected: 清楚知道当前基线分支、工作区脏改范围、暂存区是否为空。

- [ ] **Step 2: 确认唯一进行中节点**
  - 打开 `docs/current-project-status.md` 第 7、8 节，确认当前推荐顺序。
  - 在本作业单中将今天要推进的唯一主节点标记为 `进行中`。
  - Expected: 没有第二个主节点同时处于 `进行中`。

- [ ] **Step 3: 准备证据目录**
  - 在本地创建一个不会提交的证据目录，例如 `tmp/evidence/2026-04-02-W12-T03/`。
  - 将页面截图、平台截图、健康检查输出、错误日志摘要统一放入该目录。
  - Expected: 当天所有外部平台动作都有可回看的证据位置。

- [ ] **Step 4: 执行当天开始前健康确认**
  - Run: `python -m pytest backend/tests -q`
  - Run: `npm --prefix web-frontend run lint`
  - Run: `npm --prefix web-frontend run test`
  - Run: `npm --prefix web-frontend run build`
  - Run: `python scripts/mini_program_static_audit.py`
  - Run: `python scripts/smoke_login_matrix.py`
  - Expected: 如无新增回归，可继续推进外部资源与放行项；如新增回归，先停止放行推进，回到“恢复基线全绿”。

## 4. 阶段 A：基础设施收口

### Task 2: `W12-T03` 云主机 / 域名 / HTTPS 就绪

**Files:**
- Read: `docs/current-project-status.md`
- Read: `docs/production-deployment.md`
- Modify: `docs/current-project-status.md`

**Goal:** 获得一个可公网访问、可 HTTPS、可承载 Web 与 API 正式访问的云端入口。

- [ ] **Step 1: 确认输入物**
  - 云主机（`CVM`）登录权限可用。
  - 已购买并可配置 DNS 的正式域名可用。
  - HTTPS 证书已签发或有明确申请路径。
  - Expected: 账号、密码 / 密钥、域名控制权齐备。

- [ ] **Step 2: 完成平台侧配置**
  - 配置域名 A 记录 / CNAME 指向当前云主机或入口层。
  - 配置 `80/443` 开放，非必要端口不对公网暴露。
  - 部署 HTTPS 证书并确认可续期方案。
  - Expected: `https://<正式域名>` 可访问。

- [ ] **Step 3: 完成仓库内检查**
  - 核对 `docker-compose.prod.yml`、`deploy/backend.env.tencent.prod`、Web API 基础地址、Nginx 配置中的正式域名是否一致。
  - 确保 `deploy/backend.env.tencent.prod` 与模板都保留 `APP_ENV=production`（`AI_MOCK_MODE=false`、`BACKEND_CORS_ORIGINS` 与正式域名占位）、`backend` / `ai-worker` 的 Compose `environment` 传递 `APP_ENV: production`，从而让后端的生产态校验逻辑激活。
  - 在文档中同步记录正式域名、HTTPS 证书、CORS 源与 `APP_ENV` 的当前占位状态，防止仓库配置回退至本地地址。
  - 如需修改仓库文件，先在当前节点内修改，再执行最小验证。
  - Expected: 仓库配置不再依赖本地地址或临时域名。

- [ ] **Step 4: 执行验证**
  - 浏览器打开正式域名，确认 HTTPS 无证书告警。
  - Run: `curl -I https://<正式域名>`
  - Run: `curl -I https://<正式域名>/api/v1/health`
  - Expected: 返回 `200` / 可接受的重定向，且 HTTPS 链路正常。

- [ ] **Step 5: 完成判定与留痕**
  - 完成判定：正式域名解析生效、HTTPS 有效、Web / API 入口可达。
  - 失败回退：若域名或证书未生效，标记 `阻塞`，记录平台截图与 DNS 生效状态，不推进 `W12-T04`。
 - 留痕动作：更新 `docs/current-project-status.md`，记录验证结果与阻塞状态；如有仓库改动，独立提交。

> 仓库内 `APP_ENV=production` / CORS / 文档 baseline 通过这个节点已经明确收口，正式域名与 HTTPS 证书仍然由云平台 / 证书小组予以部署；相关阻塞与复验记录请继续在 `docs/current-project-status.md` 里更新。

### Task 3: `W12-T04` COS / CORS / 下载链路闭环

**Files:**
- Read: `docs/production-deployment.md`
- Read: `docs/API-CONTRACTS.md`
- Modify: `docs/current-project-status.md`

**Goal:** 获得真实可用的对象存储与浏览器 / 小程序下载链路，避免上传后只在本地可用。

- [ ] **Step 1: 确认输入物**
  - COS 桶、地域、密钥、权限策略已准备。
  - `STORAGE_*` 与腾讯云密钥配置路径明确。
  - Expected: 对象存储资源可实际读写。

- [ ] **Step 2: 平台侧配置**
  - 配置 Bucket、访问域名、私有 / 公有策略。
  - 配置 CORS，至少放通正式 Web 域名与小程序所需来源。
  - 配置下载域名或签名下载策略。
  - Expected: COS 后台配置与项目部署拓扑一致。

- [ ] **Step 3: 仓库内配置核对**
  - 检查 `deploy/backend.env.tencent.prod`、后端存储配置与正式 Bucket、地域、下载域名一致。
  - 如修改配置文件，执行最小验证后再提交。
  - Expected: 仓库与平台配置不冲突。

- [ ] **Step 4: 链路验证**
  - 通过 Web 或 API 上传一个测试文件。
  - 验证数据库记录、COS 对象、下载链接三者一致。
  - 在浏览器与受控账号下验证下载是否成功。
  - Expected: 上传、访问、下载闭环成立，无跨域报错。

- [ ] **Step 5: 完成判定与留痕**
  - 完成判定：对象成功落入 COS，下载链接可用，跨域无阻断。
  - 失败回退：若上传成功但下载失败，优先排查 CORS、签名域名、Bucket 权限；若平台未配好，标记 `阻塞`。
  - 留痕动作：更新 `docs/current-project-status.md`，必要时补充 `docs/production-deployment.md`；如有仓库改动，独立提交。

### Task 4: `W12-T08` 小程序合法域名联调

**Files:**
- Read: `docs/project-setup.md`
- Read: `docs/user-manual.md`
- Modify: `docs/current-project-status.md`

**Goal:** 使小程序正式 API 域名、上传域名、下载域名都进入合法域名清单，真实设备可连正式环境。

- [ ] **Step 1: 确认输入物**
  - 微信小程序后台权限可用。
  - 阶段 A 的正式域名、HTTPS、COS 域名均已准备。
  - Expected: 小程序后台与正式环境地址清单齐备。

- [ ] **Step 2: 平台侧配置**
  - 在小程序后台录入 `request`、`uploadFile`、`downloadFile`、`socket` 所需合法域名。
  - 确认 HTTPS、证书链与微信要求一致。
  - Expected: 所有正式链路域名均被平台接受。

- [ ] **Step 3: 本地 / 开发者工具验证**
  - 在微信开发者工具切换到正式域名配置，重启项目。
  - 依次验证登录、列表拉取、上传、下载。
  - Expected: 不再出现“非法域名”“证书错误”“网络请求失败”。

- [ ] **Step 4: 完成判定与留痕**
  - 完成判定：开发者工具和真机可访问正式域名。
  - 失败回退：若工具可用但真机不可用，先排查证书链、备案、平台缓存；标记 `阻塞`。
  - 留痕动作：更新 `docs/current-project-status.md`，记录合法域名清单已闭环。

## 5. 阶段 B：微信与真机联调

### Task 5: `WX-01` 微信能力闭环

**Files:**
- Read: `docs/current-project-status.md`
- Read: `docs/final-acceptance-checklist.md`
- Modify: `docs/current-project-status.md`

**Goal:** 让微信扫码登录、手机号能力、票据交换不再停留在本地模拟，而是真实平台闭环。

- [ ] **Step 1: 检查开始条件**
  - 阶段 A 已完成。
  - 小程序合法域名已通过。
  - Expected: 微信平台不再被基础设施问题阻断。

- [ ] **Step 2: 配置微信平台真实能力**
  - 配置真实 `AppID / AppSecret`。
  - 配置扫码登录回调域名、手机号能力、必要的公众号 / 开放平台设置。
  - Expected: 平台侧参数与部署环境一致。

- [ ] **Step 3: 验证登录与票据链路**
  - 验证 Web 微信扫码登录。
  - 验证小程序微信一键登录 / 票据交换。
  - 验证异常路径：票据无效、过期、回调失败时，用户可读错误文案仍正常。
  - Expected: 成功路径与失败路径都可解释、可留痕。

- [ ] **Step 4: 完成判定与留痕**
  - 完成判定：扫码登录、手机号能力、票据交换真测通过。
  - 失败回退：优先排查回调域名、微信白名单、服务端密钥、时间漂移；若是平台审核或账号限制，标记 `阻塞`。
  - 留痕动作：更新 `docs/current-project-status.md` 与 `docs/final-acceptance-checklist.md` 对应项状态。

### Task 6: `QA-03` 真机逐页验收

**Files:**
- Read: `docs/user-manual.md`
- Read: `docs/final-acceptance-checklist.md`
- Modify: `docs/current-project-status.md`

**Goal:** 用真实设备和 GUI 工具确认主流程不是“测试通过但体验损坏”。

- [ ] **Step 1: 准备设备与工具**
  - 打开 `HBuilderX`、微信开发者工具、至少一台真机。
  - 准备机构管理员、律师、当事人三个角色账号。
  - Expected: 真机与 GUI 工具都可连接正式环境。

- [ ] **Step 2: 逐页验收 Web 主流程**
  - 验证密码登录、短信登录、微信扫码登录、待审批、首登改密、当事人 Web 提示页。
  - 验证案件详情上传、上传后自动重分析提示。
  - Expected: 主路径文案、交互、跳转、错误提示都正常。

- [ ] **Step 3: 逐页验收小程序主流程**
  - 验证当事人邀请绑案、上传材料、补充说明、查看案件。
  - 验证律师案件处理、管理页、分析页显示边界。
  - Expected: 真机页面态、上传态、错误态正常。

- [ ] **Step 4: 完成判定与留痕**
  - 完成判定：`docs/final-acceptance-checklist.md` 中第 2~5 节关键条目均有真机 / GUI 证据。
  - 失败回退：出现体验缺陷时，先回归到对应节点修复，不直接进入云端 E2E。
  - 留痕动作：更新 `docs/current-project-status.md`，补真机验收结论。

## 6. 阶段 C：云端部署与联调

### Task 7: `W12-V01 ~ W12-V06` 云端服务联调

**Files:**
- Read: `docker-compose.prod.yml`
- Read: `docs/production-deployment.md`
- Read: `docs/API-CONTRACTS.md`
- Modify: `docs/current-project-status.md`

**Goal:** 把“本地可跑”的主链路提升为“云上可连续跑”的候选发布环境。

- [ ] **Step 1: 校验部署清单**
  - Run: `docker compose -f docker-compose.prod.yml config`
  - 检查 `web-frontend`、`backend`、`ai-worker`、`report-service`、`postgres`、`redis` 配置是否完整。
  - Expected: compose 文件无语法问题，环境变量来源清晰。

- [ ] **Step 2: 启动云端服务**
  - 在候选发布环境启动生产 compose。
  - 确认 `backend`、`web-frontend`、`ai-worker`、`report-service` 都处于健康状态。
  - Expected: 基础服务已运行。

- [ ] **Step 3: 执行健康与链路验证**
  - Run: `curl https://<正式域名>/api/v1/health`
  - Run: `curl https://<正式域名>/api/v1/ready`
  - 验证 Web 登录、案件列表、案件详情、上传、AI 状态、报告访问。
  - Expected: 所有主服务能稳定响应，非本地 mock。

- [ ] **Step 4: 完成判定与留痕**
  - 完成判定：`W12-V01 ~ W12-V06` 涉及的服务、接口、上传下载、AI 回写都在云端跑通。
  - 失败回退：若服务已起但链路断裂，优先查环境变量、COS、worker、report-service 调用；若部署本身失败，停在本节点处理。
  - 留痕动作：更新 `docs/current-project-status.md`，必要时补 `docs/production-deployment.md`。

## 7. 阶段 D：放行门禁

### Task 8: `W13-T01 ~ W13-T03` 主流程 smoke

**Files:**
- Read: `docs/final-acceptance-checklist.md`
- Modify: `docs/current-project-status.md`

**Goal:** 用最小成本先确认放行前的核心链路都可用。

- [ ] **Step 1: 执行 Web 主流程 smoke**
  - 验证管理员、律师、超级管理员视角。
  - 验证 Web `/analysis` 仍按当前口径只视为文档解析主入口。
  - Expected: Web 主流程无阻断。

- [ ] **Step 2: 执行小程序主流程 smoke**
  - 验证当事人、律师、机构管理员、个人工作区律师视角。
  - Expected: 小程序主流程无阻断。

- [ ] **Step 3: 记录 smoke 结论**
  - 直接勾选 `docs/final-acceptance-checklist.md` 中对应条目。
  - Expected: `W13-T01 ~ W13-T03` 有明确通过 / 未通过结论。

### Task 9: `W13-T04 ~ W13-T06` 云端 E2E 与回滚演练

**Files:**
- Read: `docs/final-acceptance-checklist.md`
- Read: `docs/production-deployment.md`
- Modify: `docs/current-project-status.md`

**Goal:** 证明正式环境可用、可连续用、出问题可撤回。

- [ ] **Step 1: 登录链路 E2E**
  - 验证 Web 密码、短信、微信扫码，小程序微信 / 短信 / 密码。
  - Expected: 真实云端登录链路 E2E 闭环。

- [ ] **Step 2: 上传 → AI → 报告 E2E**
  - 执行“上传材料 → 创建 AI 任务 → worker 消费 → 报告生成 / 访问”的完整流程。
  - Expected: 没有人工补 DB 或手工补文件的隐式步骤。

- [ ] **Step 3: 回滚演练**
  - 明确当前版本号、上一稳定版本号、回滚命令和回滚验证步骤。
  - 在可控窗口内完成一次真实回滚演练。
  - Expected: 回滚路径可执行、可验证、可恢复。

### Task 10: `W13-T07 ~ W13-T08` 缺陷分级与 Go / No-Go

**Files:**
- Read: `docs/final-acceptance-checklist.md`
- Modify: `docs/current-project-status.md`

**Goal:** 给出有证据支撑的上线决策。

- [ ] **Step 1: 汇总缺陷**
  - 将未解决问题按 `P0 / P1 / P2 / P3` 分级。
  - 明确哪些会阻断正式放行。
  - Expected: 没有“问题存在但没人定级”的灰区。

- [ ] **Step 2: 形成 Go / No-Go 结论**
  - 若 `P0` 未清零，则结论为 `No-Go`。
  - 若仅剩业务接受的 `ACC-14 / ACC-16 / ACC-17` 之类非正式上线前置项，可进入条件性 `Go`。
  - Expected: 结论与证据一致，不凭感觉。

## 8. 阶段 E：上线后首轮稳定期

### Task 11: `POST-01 ~ POST-04` 发布后 0~7 天巡检

**Files:**
- Read: `docs/current-project-status.md`
- Modify: `docs/current-project-status.md`

**Goal:** 把“上线成功”转化为“稳定运行”，而不是发布后失联。

- [ ] **Step 1: 发布后 0~2 小时**
  - 检查 Web / 小程序登录、上传、AI 任务、报告访问、通知。
  - 检查是否出现集中报错、任务积压、下载失败。
  - Expected: 无新增 `P0` / `P1`。

- [ ] **Step 2: 发布后 24 小时**
  - 复查用户主路径是否持续可用。
  - 复查 COS 下载、AI 消费、通知频率、首登改密、待审批提醒。
  - Expected: 无连续性异常。

- [ ] **Step 3: 发布后 3 天**
  - 判断是否需要热修复、补文档、补监控或补告警。
  - Expected: 已知问题有处理结论，而不是继续漂移。

- [ ] **Step 4: 发布后 7 天**
  - 给出“稳定 / 不稳定”的正式结论。
  - 若仍不稳定，继续停留在稳定期，不切 `dev`。
  - Expected: 稳定性结论明确。

## 9. 阶段 F：稳定后切换常规开发

### Task 12: `DEV-01 ~ DEV-03` 稳定后切出 `dev`

**Files:**
- Read: `docs/current-project-status.md`
- Read: `docs/README.md`
- Modify: `docs/current-project-status.md`
- Modify: `docs/README.md`
- Modify: `docs/documentation-map.md`

**Goal:** 在正式环境稳定后，再从稳定基线切出 `dev`，恢复常规开发节奏。

- [ ] **Step 1: 切 `dev` 前检查**
  - 确认阶段 E 已完成，且无未关闭 `P0` / `P1`。
  - 确认当前 `main`（或实际放行主线）已经包含线上稳定版本。
  - Expected: 不在不稳定状态下切常规开发分支。

- [ ] **Step 2: 创建 `dev`**
  - Run: `git switch <稳定主线分支>`
  - Run: `git pull`
  - Run: `git switch -c dev`
  - Expected: `dev` 从线上稳定基线切出。

- [ ] **Step 3: 启用后续开发规则**
  - 后续功能从 `dev` 切 `feature/*` 或 `codex/*`。
  - 紧急线上修复从稳定主线切 `hotfix/*`，修复后回合并到 `main` 与 `dev`。
  - 仍然坚持“一节点一提交、先验证再提交、状态真源同步更新”。
  - Expected: 仓库从放行期平滑切换到常规开发期。

## 10. 每日执行记录模板

```md
### YYYY-MM-DD 执行记录

- 今日唯一主节点：
- 开始前状态：
- 今日完成：
- 今日验证：
- 今日提交：
- 当前阻塞：
- 明日第一动作：
```

## 11. 阻塞登记模板

```md
### 阻塞记录：<节点编号>

- 日期：
- 阻塞类型：云资源 / 域名HTTPS / 微信平台 / 真机设备 / 第三方服务 / 本地环境 / 待决策
- 阻塞描述：
- 已尝试动作：
- 当前证据位置：
- 是否允许切换到其他准备节点：
- 解除条件：
```

## 12. 节点完成后的统一收口动作

- [ ] 更新 `docs/current-project-status.md`：补变更记录、验证结果、状态结论、推荐执行顺序。
- [ ] 如涉及放行判断，同时更新 `docs/final-acceptance-checklist.md`。
- [ ] 如涉及部署、配置或操作口径，同时更新 `docs/production-deployment.md`、`docs/user-manual.md`。
- [ ] Run: `powershell -ExecutionPolicy Bypass -File scripts/check-docs-integrity.ps1`
- [ ] 如有非文档改动，再 Run: `powershell -ExecutionPolicy Bypass -File scripts/check-status-doc-update.ps1`
- [ ] Run: `git diff --cached --name-only`
- [ ] Run: `git diff --cached --stat`
- [ ] 独立提交当前节点，不混入无关改动。

## 13. 当前推荐推进口径

- [ ] 先完成阶段 A：`W12-T03 / W12-T04 / W12-T08`
- [ ] 再完成阶段 B：`WX-01 / QA-03`
- [ ] 再完成阶段 C：`W12-V01 ~ W12-V06`
- [ ] 再完成阶段 D：`W13-T01 ~ W13-T08`
- [ ] 上线后执行阶段 E：`POST-01 ~ POST-04`
- [ ] 稳定后执行阶段 F：`DEV-01 ~ DEV-03`
