## Why

当前项目的生产口径仍以单机 `CVM + Docker Compose + 本地卷` 为主，文件上传和下载也主要经过应用服务器转发。这种模式会让服务可用性、存储容量、文件传输体验和扩容能力过度依赖单台主机、单条公网出口和人工运维动作，不符合“全部服务在线、全部数据上云、尽量降低本地网络与单点影响”的新目标。

现在需要把整体方向正式切换为“首阶段 `CVM + COS` 商用上线 + 后续托管化演进”，让后续实施、成本评估和功能开发都以同一阶段化目标架构为准，而不是继续围绕演示态部署做增量修补。

## What Changes

- 将生产目标架构从“单机本地卷部署”调整为“首阶段 `CVM + COS` 商用基线 + 后续云端托管运行面升级”。
- 新增统一云接入基线：首阶段 `DNSPod/域名 -> SSL -> Nginx(CVM)`，后续演进到 `DNSPod/域名 -> SSL -> WAF -> CDN -> CLB -> 云端应用服务`，明确 Web、小程序、API、文件下载的公网访问路径。
- 新增云端运行基线：应用 API、异步 worker、报告服务首阶段可运行在 `CVM + Docker Compose`，但不再允许“本地卷+手工守护”作为长期模式；后续以容器镜像、滚动发布、自动扩缩和托管密钥为升级目标。
- 新增云端存储基线：证据文件、报告文件、导出文件统一进入 `COS`，上传与下载优先走直传、签名 URL 和 CDN 回源。
- 新增云端数据基线：生产数据库、缓存、消息队列分别使用托管型 PostgreSQL、Redis、消息队列，避免业务能力长期依赖单机本地组件。
- 新增迁移分波：先完成 `CVM + COS` 商用基线，再完成云队列、托管数据面与多实例运行，最后完成容器化、容灾、监控和发布治理。
- **BREAKING**：文件上传与下载的生产链路将从 `server_proxy/local file response` 调整为 `云对象存储签名链路`。
- **BREAKING**：生产部署不再把 `本地磁盘` 视为长期目标形态；`DB Queue` 与单机 `CVM` 仅允许作为首阶段商用兼容方案。

## Capabilities

### New Capabilities
- `cloud-managed-runtime`: 定义 API、worker、报告服务从 `CVM + Compose` 演进到云端托管环境时的运行、发布、扩缩和回滚要求。
- `cloud-object-storage-delivery`: 定义证据文件与报告文件基于 COS 的直传、签名下载、回源和生命周期管理要求。
- `internet-resilient-access`: 定义统一域名、WAF、CDN、CLB、TLS、健康检查和跨网络访问稳定性要求。

### Modified Capabilities
- None.

## Impact

- 后端文件上传、下载、报告生成和 AI 异步任务链路将需要按 `COS` 和阶段化队列策略重构。
- Web 端和小程序端的文件上传/下载交互将从服务端代理切换为签名或临时授权链路。
- 部署文档、生产 runbook、环境变量模板和蓝图文档都需要统一改写。
- 生产资源依赖将分阶段新增或强化：首阶段聚焦 `CVM`、`COS`、域名、`SSL`、安全组、监控、快照；后续再接入 `CDN`、`WAF`、`CLB`、`TencentDB PostgreSQL`、`TencentDB Redis`、`TDMQ/CMQ`、`TCR`、`KMS/Secrets Manager`、`CLS/APM/云监控`。
