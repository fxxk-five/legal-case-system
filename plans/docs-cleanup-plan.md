# `docs` 目录精简、重组与治理任务规划（可执行版）

## 1. 总体目标与范围

### 1.1 总体目标
- 在不虚构仓库现状的前提下，将 `docs` 从“过程快照型文档集合”重构为“可维护、可交付、可验收”的文档体系。
- 解决四类已确认问题：
  - `day-*` 历史快照过多；
  - AI 文档与当前实现不符（异步假设与同步实现冲突）；
  - 部署文档分散且口径不一致；
  - 缺少前后端接口契约权威文档。

### 1.2 规划范围
- 目录范围：仅 `docs` 与 `plans/docs-cleanup-plan.md`。
- 不在本规划范围内：业务代码改造（如 Web 接口修复、WS 鉴权补丁、Celery 落地）。
- 允许动作：保留、删除、合并、重写、新增、索引重组、交叉引用修正。

### 1.3 当前状态基线（与上下文一致）
- ✅ 已完成：文档价值与时效性分析。
- 🔄 进行中：详细文档精简执行方案编制（即本文件）。
- ⏳ 待开始：删除/合并/重写/新增等执行任务。

---

## 2. 分层结果（保留 / 删除 / 合并 / 重写 / 新增）

### 2.1 保留（并优化）
1. `docs/project-setup.md`：保留，补齐环境启动约束（尤其 `backend/venv`、Docker daemon）。
2. `docs/full-development-roadmap.md`：保留为规划文档，补充“现状偏差说明”。
3. `docs/local-demo-guide.md`：保留，按当前接口契约修正联调步骤。
4. `docs/deployment-guide.md`：保留，定位为“本地/单机容器部署”。
5. `docs/environment-checklist.md`：保留，明确开发/生产变量分层与必填项。
6. `docs/AI-ENHANCEMENT-README.md`：保留但重写关键章节，改为“现状 + 目标双视图”。

### 2.2 删除
#### A. `day-*` 历史快照文档（共 30 份）
- `docs/day-01-checklist.md`
- `docs/day-02-checklist.md`
- `docs/day-03-checklist.md`
- `docs/day-04-checklist.md`
- `docs/day-05-checklist.md`
- `docs/day-13-checklist.md`
- `docs/day-14-checklist.md`
- `docs/day-15-checklist.md`
- `docs/day-16-checklist.md`
- `docs/day-18-checklist.md`
- `docs/day-19-checklist.md`
- `docs/day-20-checklist.md`
- `docs/day-21-checklist.md`
- `docs/day-22-checklist.md`
- `docs/day-23-checklist.md`
- `docs/day-24-checklist.md`
- `docs/day-25-checklist.md`
- `docs/day-26-checklist.md`
- `docs/day-27-checklist.md`
- `docs/day-28-checklist.md`
- `docs/day-29-checklist.md`
- `docs/day-30-checklist.md`
- `docs/day-32-checklist.md`
- `docs/day-33-checklist.md`
- `docs/day-34-checklist.md`
- `docs/day-35-checklist.md`
- `docs/day-36-checklist.md`
- `docs/day-37-checklist.md`
- `docs/day-38-checklist.md`
- `docs/day-39-checklist.md`

#### B. 与现实现不符或重复价值低文档（共 6 份）
- `docs/ai-backend-implementation.md`
- `docs/ai-enhancement-architecture.md`
- `docs/ai-frontend-implementation.md`
- `docs/ai-testing-acceptance.md`
- `docs/current-gap-analysis.md`
- `docs/project-structure-and-flows.md`

### 2.3 合并
- 源文档：
  - `docs/tencent-cloud-deployment-guide.md`
  - `docs/final-acceptance-checklist.md`
- 目标文档：
  - `docs/production-deployment.md`（生产部署统一入口）
- 说明：`docs/mini-program-demo-guide.md` 不并入生产部署文档，保留并重写为端侧联调文档（见 2.4）。

### 2.4 重写
1. `docs/mini-program-demo-guide.md`：重写为“基于当前接口的小程序联调指南”。
2. `docs/AI-ENHANCEMENT-README.md`：重写 AI 能力矩阵、状态字段说明、验收口径。
3. `docs/local-demo-guide.md`：重写接口调用与前端页面路径校验步骤。
4. `docs/environment-checklist.md`：重写变量分级与模板差异说明。

### 2.5 新增
1. `docs/README.md`：`docs` 目录导航与版本说明。
2. `docs/API-CONTRACTS.md`：前后端契约单一真源。
3. `docs/AI-CURRENT-STATUS.md`：AI 已实现能力、限制、下一步。
4. `docs/KNOWN-ISSUES.md`：P0/P1/P2 问题清单与缓解措施。

---

## 3. 分阶段执行计划（按优先级）

## 阶段 0：冻结与备份（P0）
**目标**
- 在执行删除前建立可回滚基线，避免误删与引用断裂不可恢复。

**输入**
- 当前仓库 `docs` 全量文件。
- 本规划文档 `plans/docs-cleanup-plan.md`。

**输出**
- 冻结清单（保留/删除/重写/新增）最终确认版。
- 备份分支或备份目录（按团队流程执行）。

**执行步骤**
1. 锁定本次变更范围（仅 `docs` + `plans/docs-cleanup-plan.md`）。
2. 导出删除候选清单并复核一次文件名。
3. 生成备份点（Git 分支或压缩归档）。

**完成定义（DoD）**
- 删除候选清单与本规划一致；
- 已存在可验证的回滚点。

## 阶段 1：删除与减负（P0）
**目标**
- 移除 36 份低价值或冲突文档，降低维护噪音。

**输入**
- 阶段 0 冻结清单。

**输出**
- `docs` 中删除目标文件不再存在。
- 删除记录（提交说明或变更日志）可追溯。

**执行步骤**
1. 按“删除执行批次建议”分批删除（见第 6 节）。
2. 每批删除后执行一次链接/引用搜索（`rg`）检查。
3. 修复引用到已删除文件的入口（主要是索引文档）。

**完成定义（DoD）**
- 36 份目标文档全部移除；
- 无核心入口仍引用已删除路径。

## 阶段 2：合并与统一入口（P0）
**目标**
- 形成生产部署单一入口文档，消除多文档口径冲突。

**输入**
- `docs/tencent-cloud-deployment-guide.md`
- `docs/final-acceptance-checklist.md`
- 当前 `deploy/nginx/nginx.conf`、`docker-compose.yml`。

**输出**
- `docs/production-deployment.md`（MVP 可用版）。

**执行步骤**
1. 提取部署步骤、配置项、验收项。
2. 按“环境准备 → 部署 → 验收 → 回滚”重排结构。
3. 明确 `/docs` 与 `/api` 实际路径说明（避免现有歧义）。

**完成定义（DoD）**
- 生产部署相关信息可在单文档闭环执行；
- 与当前 `nginx` 和 compose 口径一致。

## 阶段 3：重写与补齐（P0/P1）
**目标**
- 建立“现状准确、可联调、可验收”的核心文档集。

**输入**
- 保留文档 + 当前后端路由与前端调用现状。

**输出**
- 重写后的 4 份文档；
- 新增 4 份文档（索引/契约/AI状态/已知问题）。

**执行步骤**
1. 先产出 `docs/API-CONTRACTS.md`（作为其他文档引用基线）。
2. 再重写 `docs/local-demo-guide.md`、`docs/mini-program-demo-guide.md`。
3. 重写 `docs/AI-ENHANCEMENT-README.md`，并新增 `docs/AI-CURRENT-STATUS.md`。
4. 新增 `docs/KNOWN-ISSUES.md`，沉淀 P0/P1/P2 问题。
5. 新增 `docs/README.md`，统一导航与阅读顺序。

**完成定义（DoD）**
- 文档内 API 示例与当前后端路由可一一映射；
- AI 文档不再把“异步队列”描述为“已实现”；
- 新人按索引可完成最小联调路径。

## 阶段 4：校验与发布（P1）
**目标**
- 完成一致性验收与团队发布。

**输入**
- 阶段 1~3 产出。

**输出**
- 文档治理发布记录；
- 下一轮维护节奏（如双周审查）约定。

**执行步骤**
1. 运行链接/引用校验（文内路径、文件存在性）。
2. 抽样执行：本地 demo、部署步骤、接口契约一致性检查。
3. 形成发布说明（变更摘要 + 风险提示 + 回滚点）。

**完成定义（DoD）**
- 关键文档抽样可执行；
- 验收标准全部满足（见第 8 节）。

---

## 4. 任务清单（可勾选）

- [x] T001 分析文档价值与时效性（已完成）
- [-] T002 编制精简执行方案（进行中）
- [ ] T003 冻结范围与建立回滚点
- [ ] T004 删除批次 A（day-01~day-21）
- [ ] T005 删除批次 B（day-22~day-39）
- [ ] T006 删除批次 C（过时 AI + 冗余文档）
- [ ] T007 合并部署文档产出 `production-deployment.md`
- [ ] T008 重写 `mini-program-demo-guide.md`
- [ ] T009 重写 `local-demo-guide.md`
- [ ] T010 重写 `environment-checklist.md`
- [ ] T011 重写 `AI-ENHANCEMENT-README.md`
- [ ] T012 新增 `API-CONTRACTS.md`
- [ ] T013 新增 `AI-CURRENT-STATUS.md`
- [ ] T014 新增 `KNOWN-ISSUES.md`
- [ ] T015 新增 `docs/README.md` 并修复交叉引用
- [ ] T016 全量校验与发布说明

---

## 5. 详细任务表（可追踪）

| 任务ID | 任务名称 | 类型 | 优先级 | 前置依赖 | 产出物 | 预计工时 | 负责人角色 | 当前状态 |
|---|---|---|---|---|---|---:|---|---|
| T001 | 文档价值与时效性分析 | 分析 | P0 | 无 | 审查结论 | 6h | 架构/文档负责人 | 已完成 |
| T002 | 精简执行方案编制 | 规划 | P0 | T001 | `plans/docs-cleanup-plan.md` | 3h | 架构/文档负责人 | 进行中 |
| T003 | 冻结范围与回滚点建立 | 治理 | P0 | T002 | 冻结清单、回滚点记录 | 1h | 配置管理员 | 待开始 |
| T004 | 删除批次 A（day-01~day-21） | 删除 | P0 | T003 | 删除提交 A | 1h | 文档维护工程师 | 待开始 |
| T005 | 删除批次 B（day-22~day-39） | 删除 | P0 | T004 | 删除提交 B | 1h | 文档维护工程师 | 待开始 |
| T006 | 删除批次 C（AI 旧文档+冗余） | 删除 | P0 | T005 | 删除提交 C | 1h | 文档维护工程师 | 待开始 |
| T007 | 统一生产部署文档 | 合并/重写 | P0 | T006 | `docs/production-deployment.md` | 4h | 后端+运维文档负责人 | 待开始 |
| T008 | 小程序联调文档重写 | 重写 | P1 | T012 | `docs/mini-program-demo-guide.md` | 2h | 小程序工程师 | 待开始 |
| T009 | 本地联调文档重写 | 重写 | P1 | T012 | `docs/local-demo-guide.md` | 2h | 前端工程师 | 待开始 |
| T010 | 环境清单文档重写 | 重写 | P1 | T003 | `docs/environment-checklist.md` | 1.5h | 后端工程师 | 待开始 |
| T011 | AI 总览文档重写 | 重写 | P0 | T013 | `docs/AI-ENHANCEMENT-README.md` | 3h | AI/后端工程师 | 待开始 |
| T012 | 接口契约文档补齐 | 新增 | P0 | T006 | `docs/API-CONTRACTS.md` | 4h | 后端+前端联合 | 待开始 |
| T013 | AI 当前状态文档新增 | 新增 | P0 | T006 | `docs/AI-CURRENT-STATUS.md` | 2h | AI/后端工程师 | 待开始 |
| T014 | 已知问题文档新增 | 新增 | P1 | T001 | `docs/KNOWN-ISSUES.md` | 1.5h | 架构负责人 | 待开始 |
| T015 | docs 索引与导航构建 | 新增/治理 | P0 | T007,T008,T009,T010,T011,T012,T013,T014 | `docs/README.md` | 1.5h | 文档负责人 | 待开始 |
| T016 | 全量校验与发布 | 验收 | P0 | T015 | 发布说明、验收记录 | 2h | QA/发布经理 | 待开始 |

---

## 6. 删除执行批次建议（分批执行）

## 批次 A：`day-01` ~ `day-21`
- **范围**：`docs/day-01-checklist.md` 至 `docs/day-21-checklist.md`。
- **风险**：少量引用可能仍出现在历史说明中。
- **验证点**：`rg "day-[0-9]+-checklist" docs README.md` 无关键入口引用。
- **回滚点**：回滚到删除提交 A 或恢复备份包 A。

## 批次 B：`day-22` ~ `day-39`
- **范围**：`docs/day-22-checklist.md` 至 `docs/day-39-checklist.md`。
- **风险**：小程序相关历史条目可能被误当现行文档引用。
- **验证点**：`docs` 根索引不包含 `day-*` 链接。
- **回滚点**：回滚到删除提交 B。

## 批次 C：过时 AI 文档 + 冗余文档
- **范围**：
  - `docs/ai-backend-implementation.md`
  - `docs/ai-enhancement-architecture.md`
  - `docs/ai-frontend-implementation.md`
  - `docs/ai-testing-acceptance.md`
  - `docs/current-gap-analysis.md`
  - `docs/project-structure-and-flows.md`
- **风险**：AI 与架构背景信息短时缺口。
- **验证点**：在同一迭代内补齐 `docs/AI-CURRENT-STATUS.md` 与 `docs/API-CONTRACTS.md`。
- **回滚点**：回滚到删除提交 C；或从备份恢复单文件。

---

## 7. 文档重组信息架构（IA）建议

## 7.1 推荐目录结构（未来态）
```text
docs/
├── README.md                         # 文档导航与阅读顺序
├── project-setup.md                  # 开发环境初始化
├── environment-checklist.md          # 环境变量与配置清单
├── local-demo-guide.md               # 本地联调路径
├── mini-program-demo-guide.md        # 小程序联调路径
├── deployment-guide.md               # 本地/单机容器部署
├── production-deployment.md          # 生产部署与回滚
├── API-CONTRACTS.md                  # API 契约单一真源
├── AI-CURRENT-STATUS.md              # AI 现状与限制
├── AI-ENHANCEMENT-README.md          # AI 路线与演进（与现状分层）
├── KNOWN-ISSUES.md                   # 已知问题与缓解
└── full-development-roadmap.md       # 中长期路线图
```

## 7.2 文档定位规则
- **操作型文档**：必须可按步骤执行并有“前置条件/验收点”。
- **契约型文档**：以当前代码为准，不写“计划态”接口。
- **规划型文档**：必须显式标注“目标态”，禁止冒充“已实现”。

---

## 8. 接口契约文档补齐计划（MVP）

## 8.1 MVP 目标
- 一周内形成可用的 `docs/API-CONTRACTS.md`，覆盖当前联调阻塞点。

## 8.2 MVP 步骤
1. 以后端路由为准梳理最小接口集：
   - `backend/app/api/routes_auth.py`
   - `backend/app/api/routes_cases.py`
   - `backend/app/api/routes_files.py`
   - `backend/app/api/routes_users.py`
   - `backend/app/api/routes_ai.py`
   - `backend/app/api/routes_tenants.py`
2. 结构化输出：`方法 + 路径 + 请求体 + 响应体 + 错误码 + 权限`。
3. 显式列出“已知前端漂移点”（如登录、案件详情、律师管理）。
4. 与前端负责人完成一次逐条对齐评审并冻结版本号。

## 8.3 MVP 完成定义
- CaseDetail、Lawyers、Login 三条关键链路的接口描述可直接指导修复。
- AI 接口明确“当前同步执行”而非异步队列。

---

## 9. 部署文档统一计划（MVP）

## 9.1 MVP 目标
- 合并形成 `docs/production-deployment.md`，作为线上部署唯一入口。

## 9.2 MVP 步骤
1. 吸收 `docs/tencent-cloud-deployment-guide.md` 的云资源与主机准备内容。
2. 吸收 `docs/final-acceptance-checklist.md` 的验收条目，改为发布闸门。
3. 对齐当前 `deploy/nginx/nginx.conf` 与 `docker-compose.yml` 实际行为。
4. 明确 `/api`、健康检查、HTTPS、回滚流程与备份策略。

## 9.3 MVP 完成定义
- 按文档可完成一次从拉起到验收的部署演练。
- 文档中不再出现与当前 Nginx 路由冲突的描述。

---

## 10. 依赖与并行关系

### 10.1 关键依赖链
- `T002 -> T003 -> T004/T005/T006 -> T012/T013/T007 -> T008/T009/T010/T011 -> T015 -> T016`

### 10.2 可并行执行
- 在 `T006` 完成后，可并行：
  - `T012`（接口契约）
  - `T013`（AI现状）
  - `T007`（生产部署统一）
- 在 `T012` 完成后，可并行：
  - `T008`（小程序联调）
  - `T009`（本地联调）

### 10.3 不建议并行
- 删除批次与索引构建（`T004~T006` 与 `T015`）不并行，避免导航频繁失效。

---

## 11. 风险与回滚

| 风险 | 等级 | 触发条件 | 缓解措施 | 回滚策略 |
|---|---|---|---|---|
| 误删仍被引用文档 | 高 | 删除后入口链接失效 | 批次删除 + 每批引用扫描 | 回滚该批次提交 |
| AI 文档删除后信息断层 | 高 | 新文档未及时补齐 | 删除批次 C 与 T013 同迭代 | 恢复单文件并标记 deprecated |
| 部署口径再次分叉 | 中 | 合并时未按真实配置修订 | 以 `nginx.conf`/compose 为唯一依据 | 回滚 `production-deployment.md` 到上版 |
| 契约文档与代码漂移 | 中 | 后端变更未同步文档 | 建立“接口变更必须改契约”门禁 | 回滚契约文档到冻结版并补差异 |

---

## 12. 验收标准

### 12.1 结构验收
- `docs` 文档数量与目标 IA 一致（删除目标全部移除，新文档全部到位）。
- `docs/README.md` 能导航到所有现行文档，无失效链接。

### 12.2 准确性验收
- `docs/API-CONTRACTS.md` 与当前后端路由逐项可映射。
- AI 文档中“已实现能力”与“目标能力”明确分层。
- 部署文档与 `deploy/nginx/nginx.conf`、`docker-compose.yml` 口径一致。

### 12.3 可执行性验收
- 按 `docs/local-demo-guide.md` 可完成最小本地联调。
- 按 `docs/production-deployment.md` 可完成部署演练与回滚演练（文档级）。

### 12.4 治理验收
- 建立更新机制：接口变更、部署变更、AI 架构变更需同步文档。
- `docs/KNOWN-ISSUES.md` 包含当前 P0/P1/P2 且有状态字段。

---

## 13. 里程碑与工时预估

| 里程碑 | 时间窗 | 包含任务 | 预计工时 | 交付物 |
|---|---|---|---:|---|
| M1 方案冻结 | Day 1 | T002,T003 | 4h | 冻结清单 + 回滚点 |
| M2 删除完成 | Day 1 | T004,T005,T006 | 3h | 删除提交 A/B/C |
| M3 核心文档成型 | Day 2 | T007,T012,T013 | 10h | 部署统一文档 + 契约 + AI现状 |
| M4 重写与导航完成 | Day 3 | T008,T009,T010,T011,T014,T015 | 11.5h | 重写文档 + docs 索引 |
| M5 验收发布 | Day 3 | T016 | 2h | 验收记录 + 发布说明 |

**总预估工时**：约 `30.5h`（1 人）；2~3 人并行可压缩至 `2~3` 天。

---

## 14. 责任分工建议

- **文档治理负责人（1人）**：统筹范围冻结、IA、验收口径（主责 `T002/T003/T015/T016`）。
- **后端代表（1人）**：提供路由与部署事实基线（主责 `T007/T010/T012/T013`）。
- **前端代表（1人）**：确认联调文档可执行性（主责 `T009`，协作 `T012`）。
- **小程序代表（1人）**：确认小程序联调路径（主责 `T008`）。
- **QA/发布经理（可兼职）**：执行抽样验收与发布记录（主责 `T016`）。

---

## 15. 执行注意事项
- 本规划不引入任何未在仓库出现的新模块或新服务，仅整理文档层。
- 所有“未来能力”必须以“目标态”标注，禁止写成“已实现”。
- 删除动作必须分批，并在每批次后做引用校验与可回滚确认。
- 以 `docs/API-CONTRACTS.md` 作为联调事实基线，其他文档仅引用不重复定义。
