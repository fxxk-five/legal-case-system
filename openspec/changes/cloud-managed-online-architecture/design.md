## Context

> Status update (2026-03-23): the repository has completed the core `COS` storage path refactor, production env/source-of-truth mapping, single-CVM backup and log-rotation guidance, DB queue guardrails including retry backoff and stale-task recovery, plus the second-wave evolution blueprint for managed data services, multi-CVM ingress, cloud queue adapter boundaries, and the `TCR + TKE` path. The remaining gap is real cloud-domain validation.

当前仓库的实现与文档存在两套并行口径：

- 运行面仍以 `CVM + Docker Compose + 本地卷 + 手工守护 worker` 为主要生产落地路径。
- 蓝图层已经多次提到 `COS`、`TencentDB`、`TDMQ`、`WAF`、`KMS` 等云上能力，但缺少统一的目标架构和迁移原则。
- 文件上传/下载链路仍以应用服务器代理和本地路径读写为主，这会让公网带宽、磁盘容量和单机可用性成为主瓶颈。

业务侧的新方向已经明确：

- 服务必须在云端启动和运行，不能依赖开发机、办公室网络或 SSH 会话。
- 文件和报告必须存放在云端对象存储，而不是本地磁盘。
- 对外访问必须走稳定的统一域名与公网接入链路，避免继续围绕“单台主机+单条出口”设计。

这次设计的目标不是立即替换全部实现，而是把“目标态架构 + 分波迁移路径 + 关键接口变化”一次性定清楚，作为后续实施唯一基线。

## Goals / Non-Goals

**Goals:**

- 将生产目标态正式定义为“全云端托管运行 + 云端对象存储 + 托管型数据底座 + 公网统一接入”。
- 明确 Web、小程序、API、文件上传、文件下载、报告导出的公网访问路径。
- 明确证据文件和报告文件在生产环境下必须进入 `COS`，并优先采用直传和签名下载链路。
- 明确 API、worker、报告服务的云端运行形态、发布方式、扩缩方式和回滚策略。
- 明确从当前单机部署向目标态迁移的阶段、切换顺序和回滚点。

**Non-Goals:**

- 本次不直接完成全部代码改造，也不替代具体实施任务。
- 本次不设计跨云厂商通用层，默认以腾讯云作为主生产平台。
- 本次不承诺多地域双活；目标是先实现单地域高可用和可运维。
- 本次不把本地开发环境删除；本地环境继续保留用于开发和调试。

## Decisions

### 1. 生产运行面采用阶段化演进，而不是直接从单机本地卷跳到最终容器平台

**Decision**

生产环境分两阶段推进：

- 首阶段采用 `CVM + Docker Compose + COS` 作为商用基线。
- 增长期再演进到 `CLB + 多 CVM` 或 `TCR + TKE`。

无论运行面处于哪个阶段，文件与报告都统一进入 `COS`，并保持以下服务拆分边界：

- `api`
- `web`
- `ai-worker`
- `report-service`

首阶段对外流量统一进入 `域名 + SSL + Nginx(CVM)`；增长期再切到 `CLB Ingress` 或容器编排入口。`CVM + Docker Compose` 允许作为首阶段商用基线，但不再允许和本地卷深度耦合。

**Rationale**

- 当前系统已经是多容器结构，首阶段直接落 `CVM + Compose` 成本最低，后续迁移到容器编排的工程成本也可控。
- `ai-worker` 与 `report-service` 的资源模型明显不同，需要独立伸缩和独立发布。
- `Puppeteer/Chromium` 场景对运行时控制要求较高，保留容器形态比改写为其它托管函数更稳妥。

**Alternatives considered**

- `单机 CVM + Docker Compose + 本地卷`：实现最简单，但单点明显，也不利于文件与报告后续扩容。
- `Serverless Cloud Functions`：对 API 轻量场景适合，但不适合长时任务、队列消费和 Chromium 渲染主链路。

### 2. 文件与报告统一进入 COS，生产链路改为“直传 + 签名下载”

**Decision**

生产环境的证据文件、报告文件、导出文件全部进入 `COS`。上传采用 `STS/签名策略 -> 前端直传 COS -> 后端确认入库`，下载采用 `签名 URL` 或 `鉴权后跳转 CDN/COS`，不再将大文件长期经由应用服务器转发。

**Rationale**

- 将文件流量从应用层剥离，显著降低 API 服务器的带宽与磁盘压力。
- 便于接入 `CDN`、生命周期管理、版本控制、审计和回收站策略。
- 能更好支持小程序、Web 和报告下载的统一云端链路。

**Alternatives considered**

- `服务端代理上传/下载`：逻辑简单，但会把公网带宽和磁盘压力全部压在应用服务上。
- `继续使用本地卷`：不能满足“存储也在云端”的目标，也不利于扩容和迁移。

### 3. 数据面采用托管数据库、缓存和消息队列

**Decision**

生产数据面采用：

- `TencentDB for PostgreSQL`
- `TencentDB for Redis`
- `TDMQ/CMQ` 作为异步任务投递与消费通道

当前 `DB Queue` 保留为开发和过渡方案，但不再作为长期生产目标。

**Rationale**

- 业务已经明确需要“全部都在网上”的在线服务能力，核心依赖不应长期绑在单机容器里。
- 队列从数据库中拆出后，AI 任务可观测性、重试、积压处理和 worker 扩缩都会更稳定。
- 托管数据面更适合后续做备份、审计、告警和资源隔离。

**Alternatives considered**

- `保留 DB Queue`：短期成本低，但长期会把业务表、任务表和重试逻辑绑死在同一个数据库里。
- `自建 Redis/RabbitMQ`：仍然增加自运维负担，与目标方向不一致。

### 4. 公网统一入口采用“域名 + TLS + WAF + CDN + CLB”

**Decision**

公网入口统一为：

`DNSPod / 域名 -> SSL -> WAF -> CDN -> CLB -> TKE Ingress -> api/web`

其中：

- `Web` 静态资源优先走 CDN
- `API` 走 CLB + Ingress
- `COS` 下载链路可选择 CDN 回源 COS
- 小程序合法域名与 Web/API 主域名统一规划

**Rationale**

- 用户访问路径固定在腾讯云公网入口，服务不再依赖办公室网络、家庭宽带或某台开发机。
- CDN 能改善跨地域访问体验，降低静态资源和文件下载对应用层的冲击。
- WAF、TLS、CLB 健康检查共同构成生产接入基线。

**Alternatives considered**

- `仅域名 -> 单台 Nginx`：实现简单，但接入层仍是单点。
- `仅 CLB 不加 CDN`：API 可行，但静态资源与下载体验较差。

### 5. 密钥和配置采用云端托管，不再以手工 .env 为生产真源

**Decision**

生产敏感配置统一进入 `Secrets Manager / KMS`，非敏感配置通过配置中心或 CI/CD 注入。应用实例在启动时从云端读取配置，不以手工编辑主机上的 `.env` 作为真源。

**Rationale**

- 避免密钥散落在主机、本地工作目录和临时脚本中。
- 便于权限收口、审计与轮换。
- 与容器化发布方式一致。

**Alternatives considered**

- `继续依赖 .env 文件`：适合开发，但不适合长期生产治理。

## Risks / Trade-offs

- [云资源成本上升] → 通过分波迁移、容量分层和对象存储卸载带宽来控制成本；先迁移存储与接入，再迁移运行面。
- [厂商锁定增强] → 在代码层保留存储、队列、配置的适配器边界，避免直接把腾讯云 SDK 散落在业务层。
- [上传链路复杂度增加] → 采用“签名 -> 直传 -> 回写确认”的固定模式，并补齐幂等键与回调验签。
- [报告服务对容器资源较敏感] → 将 `report-service` 独立部署，单独配置 CPU/内存 requests/limits 和健康检查。
- [切换期间双链路并存] → 采用双写/灰度读策略，明确每一波的回滚点，避免一次性大爆炸切换。
- [签名 URL 与 CDN 缓存策略冲突] → 对私有文件使用短时签名 URL 或鉴权回源，避免错误缓存私有资源。

## Migration Plan

1. **蓝图收口**
   - 更新总蓝图、框架文档、生产目标拓扑和实施波次。
   - 明确首阶段推荐为 `CVM + COS`，增长阶段再进入多实例或容器化。

2. **首阶段云基础设施落地**
   - 创建 `VPC`、子网、安全组、`CVM`、`COS`、域名、证书、监控和快照。
   - 用现有 `Docker Compose` 在 `CVM` 启动服务，确保服务完全运行在云端。

3. **存储链路迁移**
   - 新增 `COS` 存储后端。
   - Web 与小程序改为获取上传凭证后直传 COS。
   - 下载与报告导出改为签名 URL。
   - 视切换策略决定是否短期双写本地与 COS。

4. **增量稳态演进**
   - 按预算和稳定性需求接入 `CDN`、托管 `PostgreSQL/Redis`、第二台 `CVM`、`CLB`。
   - 补齐单机恢复、日志留存、快照、备份和回滚机制。

5. **容器化与队列化升级**
   - 将 AI 任务投递从 `DB Queue` 切换到 `TDMQ/CMQ`。
   - 为 `api`、`web`、`ai-worker`、`report-service` 构建镜像并推送到 `TCR`。
   - 在 `TKE` 创建 Deployment / Service / Ingress / HPA。
   - 接入云端配置与密钥管理。

6. **切流与回滚**
   - 先以灰度域名验证 API、上传、下载、报告、WebSocket/轮询兜底。
   - 主域名切换到 `CVM + COS` 基线入口，再视阶段切换到 `CLB/TKE`。
   - 如出现严重问题，回退 DNS/Ingress 到上一阶段入口，同时保留数据库与对象存储一致性校验。

## Open Questions

- `web` 是否最终部署为 `CDN + COS 静态站点`，还是继续作为 TKE 内部服务暴露到 CLB。
- 上传鉴权选型优先 `STS 临时密钥` 还是 `预签名 POST`。
- 报告文件是统一走私有 COS + 签名 URL，还是为公开模板引入独立下载域名。
- `TKE` 选择标准集群还是 Serverless 集群，取决于 `report-service` 的稳定性与成本评估结果。
