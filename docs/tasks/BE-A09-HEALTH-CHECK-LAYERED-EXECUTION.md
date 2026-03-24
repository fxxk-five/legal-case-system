# BE-A09 执行单：健康检查分层设计

## 1. 任务目标
- 将当前单一 `/api/v1/health` 健康检查升级为分层模型，区分“进程存活”和“依赖可用”。
- 为容器编排、反向代理与监控系统提供可操作的探针接口。
- 保持向后兼容：现有 `/api/v1/health` 继续可用。

## 2. 范围
### 2.1 In Scope
- 健康接口分层：`live` / `ready` /（可选）`deps`。
- 状态码与响应结构定义。
- 数据库、缓存、关键配置检查项。
- 部署文档与监控接入约束。

### 2.2 Out of Scope
- 监控平台替换（Prometheus/Grafana 等）。
- 全链路业务自检（只做基础依赖层）。

## 3. 现状基线（代码事实）
- `backend/app/main.py` 仅有 `GET /api/v1/health`，固定返回 `{"status":"ok"}`。
- 当前健康检查不验证数据库、Redis、存储可用性，无法支持 readiness 判定。
- `docker-compose.yml` 无明确 probe 配置；`nginx` 也无专门的上游健康探测配置。

## 4. 目标接口规范

## 4.1 `GET /api/v1/health/live`
- 语义：进程存活探针（liveness）。
- 判定：应用进程可响应即可，不检查外部依赖。
- 成功示例：
```json
{ "status": "alive", "service": "backend", "version": "0.1.0" }
```

## 4.2 `GET /api/v1/health/ready`
- 语义：服务就绪探针（readiness）。
- 判定：至少检查数据库连通性；可选检查 Redis、存储后端。
- 成功返回 `200`，失败返回 `503`。
- 响应建议：
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "storage": "ok"
  }
}
```

## 4.3 兼容接口 `GET /api/v1/health`
- 语义：保留旧接口，默认等同 `live` 或返回汇总状态。
- 目标：不破坏既有调用与文档。

## 5. 检查项设计
- `database`：`SELECT 1` 快速探测，超时建议 1 秒。
- `redis`（可选）：`PING` 检测（当前 compose 已含 redis）。
- `storage`（可选）：本地目录可写性检测（或对象存储 SDK 健康探测）。
- `config`（可选）：关键环境变量完整性（只输出缺失项，不回显敏感值）。

## 6. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A09-1 | 健康接口拆分 | `backend/app/main.py` | `/health/live` `/health/ready` |
| A09-2 | DB 探针实现 | `backend/app/db/session.py` 或新 health 模块 | 数据库就绪检查 |
| A09-3 | Redis/Storage 探针（可选） | `backend/app/services` | 扩展依赖检查 |
| A09-4 | 统一响应结构 | `main.py` | 标准 health payload |
| A09-5 | 文档同步 | `docs/API-CONTRACTS.md`、`docs/production-deployment.md` | 探针说明与部署接入 |
| A09-6 | 测试 | `backend/tests/` | live/ready 成功与失败分支 |

## 7. 验收标准（DoD）
- `/health/live` 在依赖异常时仍可返回 `200 alive`。
- `/health/ready` 在数据库不可用时返回 `503`。
- 保持 `/health` 兼容，不破坏现有调用。
- 部署文档明确容器与网关应使用哪个探针。

## 8. 风险与默认策略
- 风险：readiness 检查过重导致探针反压。  
  默认策略：仅做轻量探测，超时快速失败。
- 风险：依赖抖动导致频繁摘除实例。  
  默认策略：编排侧设置 `failureThreshold` 与短期重试。
- 风险：检查项返回敏感信息。  
  默认策略：仅输出状态，不输出凭据与内部地址。

## 9. 回滚策略
1. 新增探针异常时可临时回退到仅 `live` 作为 readiness。
2. 保留旧 `/health` 行为，避免外部监控中断。
3. 回滚后记录依赖探针误报原因并修复。

## 10. 预估工作量
- 设计与实现：0.5 人日
- 测试与部署验证：0.5 人日
- 合计：1 人日
