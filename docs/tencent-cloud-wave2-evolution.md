# 腾讯云二阶段演进与切流方案

> 更新日期：2026-03-23
> 适用范围：在首阶段 `CVM + Docker Compose + COS` 稳定后，继续演进到托管数据面、多实例接入、云队列和容器平台

## 1. 目标

- 把单机 `Postgres/Redis` 迁移到 `TencentDB PostgreSQL / TencentDB Redis`。
- 在不改变 `COS` 文件模型的前提下，演进到 `CLB + 多 CVM`。
- 为 `TDMQ/CMQ`、`TCR`、`TKE` 预留清晰的切换边界。
- 为 `CDN / WAF / CLB` 接入与正式切流提供回滚检查点。

## 2. `TencentDB PostgreSQL / Redis` 迁移路径

### 2.1 触发条件

- 单机 `CVM` 上的数据库与缓存开始影响发布窗口。
- 租户数上升，要求数据库备份、监控、恢复能力更稳定。
- 计划进入多实例或 `CLB` 阶段，不能继续把数据库绑在单主机本地卷上。

### 2.2 目标拓扑

`api / ai-worker / report-service -> VPC 内网 -> TencentDB PostgreSQL / TencentDB Redis`

### 2.3 执行步骤

1. 新建 `TencentDB PostgreSQL` 与 `TencentDB Redis`，限定为私网访问。
2. 在灰度环境导入全量数据库备份，执行只读核验。
3. 将 `staging` 的 `POSTGRES_*`、`REDIS_*` 切换到托管实例。
4. 验证迁移后的迁移脚本、AI 任务、报告生成、登录和文件元数据链路。
5. 生产切换前冻结写流量或进入低峰窗口。
6. 从单机 `postgres` 做最终增量导出并导入托管库。
7. 更新 `production` 环境文件并重启 `backend / ai-worker`。
8. 保留原单机数据库至少一个观察周期，不立即销毁。

### 2.4 回滚检查点

- 检查点 A：灰度环境切库失败，直接恢复灰度环境变量到本机数据库。
- 检查点 B：生产切库后应用健康检查失败，恢复上一版环境文件并重启容器。
- 检查点 C：仅在确认托管库写入稳定后，才解除原单机数据库保留。

## 3. `CLB + 多 CVM` 扩容路径

### 3.1 触发条件

- 单机 CPU、内存或出网带宽持续逼近阈值。
- 需要灰度发布、滚动升级或单机故障切换能力。
- 律所数量和并发访问开始超过单主机舒适区。

### 3.2 目标拓扑

`DNSPod -> SSL -> WAF -> CDN -> CLB -> 多台 CVM(api/web/worker)`  
`文件继续走 COS，数据库/缓存继续走托管实例`

### 3.3 执行步骤

1. 将数据库、缓存、文件真源先从单机解耦。
2. 复制首台 `CVM` 的运行时配置到第二台 `CVM`。
3. 保证各实例只依赖 `COS` 和托管数据面，不依赖本机文件卷。
4. 建立 `CLB` 健康检查，只放行 `health/ready` 为正常的实例。
5. 先灰度接入新实例，再逐步提高流量权重。
6. `ai-worker` 独立于 `web/api` 扩容，避免混部放大资源竞争。

### 3.4 回滚检查点

- 检查点 A：新增实例异常，直接从 `CLB` 摘除该实例。
- 检查点 B：`CLB` 接入异常，DNS 切回单机 `Nginx(CVM)`。
- 检查点 C：扩容后若数据库压力异常，暂停继续加实例，先处理数据面瓶颈。

## 4. `TDMQ / CMQ` 云队列演进路径

### 4.1 当前仓库已完成的边界

- 新增了队列适配层 [ai_queue.py](/D:/code/law/legal-case-system/backend/app/services/ai_queue.py)。
- 当前支持 `QUEUE_DRIVER=db|tdmq|cmq` 的驱动识别与配置校验。
- `db` 仍是本地开发和首阶段商用兼容模式。
- `tdmq/cmq` 已有消息结构、配置入口和失败即停的保护，不再走进程内线程兜底。

### 4.2 启用云队列前置条件

- 明确使用 `TDMQ for Pulsar/CMQ` 的具体产品形态。
- 确认官方 SDK 或 HTTP 客户端接入方式。
- 获取 `region / namespace / topic / subscription / secret`。
- 提供专用 cloud consumer，不再复用当前 DB worker 脚本。

### 4.3 启用步骤

1. 在灰度环境补齐 `TENCENT_QUEUE_*` 配置。
2. 接入真实云队列收发客户端。
3. 为 `api` 启用消息投递，为 cloud consumer 启用消息消费。
4. 对比 `DB Queue` 与云队列在重试、死信、堆积监控上的行为。
5. 稳定后再将生产 `QUEUE_DRIVER` 从 `db` 切换到 `tdmq` 或 `cmq`。

### 4.4 回滚检查点

- 队列投递异常：立即恢复 `QUEUE_DRIVER=db`。
- 云 consumer 异常：停用云 consumer，恢复 `ai-worker` 的 DB 模式消费。

## 5. `TCR + TKE` 容器平台路径

### 5.1 触发条件

- 需要标准化镜像发布、HPA、命名空间隔离和多环境一致性。
- `CLB + 多 CVM` 已经稳定，但发布窗口和弹性仍不够。

### 5.2 执行步骤

1. 将 `api / web / ai-worker / report-service` 镜像发布到 `TCR`。
2. 在 `TKE` 中建立 `Deployment / Service / Ingress / HPA`。
3. 将环境变量从主机文件改为平台注入或密钥服务注入。
4. `report-service` 单独配置资源请求与限制。
5. 先用灰度域名验证，再从 `CLB + CVM` 切换到 `CLB + TKE`。

### 5.3 回滚检查点

- 平台部署异常：Ingress 权重切回 `CVM` 集群。
- 资源限制不合理：先调配额，不要直接删除旧集群。

## 6. `CDN / WAF / CLB` 公网接入演进

### 6.1 接入顺序

1. `DNSPod + SSL + Nginx(CVM)`：首阶段。
2. `CDN`：静态资源、附件下载、报告下载明显上升时接入。
3. `WAF`：正式商用、暴露面变大时接入。
4. `CLB`：进入多实例或容器平台时接入。

### 6.2 路由策略

| 流量类型 | 推荐路径 | 说明 |
| --- | --- | --- |
| Web 静态资源 | `CDN -> web` 或 `CDN -> COS` | 优先减轻源站压力 |
| API 请求 | `WAF -> CLB -> api` | 保持动态接口不走错误缓存 |
| 私有报告/附件下载 | `鉴权 -> COS 签名 URL` 或 `鉴权回源 CDN` | 避免把私有资源长时间缓存到公网 |

### 6.3 缓存与鉴权原则

- 私有文件优先短时签名 URL，不做长时间公网缓存。
- `CDN` 对 `api` 默认关闭缓存。
- `WAF` 只保护公网入口，不改变 `COS` 的私有权限模型。

## 7. 分波切流与回滚方案

### Wave 0：代码与配置收口

- 完成 `COS` 真源、受控环境文件、队列护栏。
- 回滚点：恢复上一版代码与环境文件。

### Wave 1：正式单机云化

- 上线 `CVM + COS + 域名/SSL`。
- 回滚点：DNS 或入口回到旧单机入口。

### Wave 2：托管数据面

- 切换到 `TencentDB PostgreSQL / Redis`。
- 回滚点：恢复到本机数据库/缓存。

### Wave 3：公网接入增强

- 补 `CDN / WAF / CLB`。
- 回滚点：逐层回退，优先摘除 `CLB` 或 `CDN`，不动 `COS` 真源。

### Wave 4：云队列与容器平台

- 切 `TDMQ/CMQ`，再切 `TCR + TKE`。
- 回滚点：`QUEUE_DRIVER` 回退到 `db`，Ingress 切回 `CVM`。

## 8. 当前结论

- 当前仓库已可以支撑首阶段 `CVM + COS` 上线。
- 二阶段所需的迁移路径、触发条件和回滚点现已收口。
- 剩余唯一不能在本地完成的事项，是基于真实云域名与真实腾讯云资源的正式验收。
