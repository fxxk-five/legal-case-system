# BE-A06 执行单：文件上传安全基线规范

## 1. 任务目标
- 为文件上传与下载链路建立可执行的安全基线，覆盖“准入校验、存储落盘、访问控制、审计追踪、异常处理”。
- 在不改变既有接口路径与前端 UI 的前提下，补齐后端强约束，避免仅依赖前端校验。
- 为后续对象存储（COS/OSS）扩展提供一致安全口径。

## 2. 范围
### 2.1 In Scope
- 上传接口 `POST /api/v1/files/upload?case_id=...` 安全规则。
- 上传策略接口 `GET /api/v1/files/upload-policy` 安全规则。
- 下载接口 `GET /api/v1/files/{file_id}/download` 与 `GET /api/v1/files/access/{token}` 安全规则。
- 文件服务层安全控制（大小、类型、流式写入、令牌、安全日志）。
- 错误码与异常响应对齐（依赖 BE-A05）。

### 2.2 Out of Scope
- 前端样式、交互改版。
- 文件删除、版本管理、内容审阅工作流重构。
- 完整 DLP/内容合规引擎接入（仅预留扩展位）。

## 3. 现状基线（代码事实）
- `backend/app/api/routes_files.py` 已提供上传、上传策略、列表、访问链接、下载接口。
- `backend/app/services/file.py` 当前存在以下现实限制：
  - 仅校验文件名非空，未限制文件大小、文件类型、扩展名。
  - `upload.file.read()` 一次性读入内存，存在大文件内存放大风险。
  - `file_type` 直接使用客户端 `content_type`，缺少服务端真实性校验。
  - 下载 token 在 URL path 中传递，存在代理/日志泄漏风险。
- 当前配置仅有 `FILE_ACCESS_TOKEN_EXPIRE_MINUTES`，无上传大小与类型白名单配置。
- 前端现实：
  - Web AI 组件有 50MB 与类型前置校验，但后端未强制。
  - 小程序上传链路可直接发起上传策略与上传请求，后端仍需兜底校验。

## 4. 安全基线规范（目标）

## 4.1 上传准入规则
- 文件名：
  - 必填，去首尾空格后长度 `1..255`。
  - 拒绝控制字符与非法路径字符（`../`, `..\\`, `\0` 等）。
- 大小限制（默认）：
  - `FILE_UPLOAD_MAX_SIZE_MB=50`
  - 超限返回 `413`。
- 类型限制（默认白名单）：
  - `application/pdf`
  - `application/msword`
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `image/jpeg`
  - `image/png`
  - `image/jpg`
  - 非白名单返回 `415`。
- 双重校验：
  - 客户端声明 MIME（`content_type`）仅作参考；
  - 服务端依据扩展名 + 魔数（magic bytes）二次校验，冲突时以服务端检测为准。

## 4.2 存储落盘规则
- 必须使用流式写入（chunk 写入），禁止一次性 `read()` 全量文件。
- 存储 key 使用后端生成 UUID，不使用用户原始路径。
- 文件落盘路径必须约束在 `LOCAL_STORAGE_DIR` 根目录内，禁止越界写入。
- 可选增强：
  - 写入同时计算 `sha256`，用于审计与去重基础能力。

## 4.3 访问控制规则
- `download` 直连接口：保持 JWT 鉴权 + 案件可见性校验。
- `access/{token}` 短链下载：
  - token 必须包含 `file_id + tenant_id + scene=file_access + exp`；
  - 默认有效期沿用 `FILE_ACCESS_TOKEN_EXPIRE_MINUTES`（当前 10 分钟）；
  - 建议单次用途（可选）与下载次数记录（可选）。
- 令牌泄漏防护：
  - 日志与网关必须脱敏 token；
  - 避免在错误日志中输出完整 URL。

## 4.4 审计与可观测性
- 上传成功日志最少字段：
  - `request_id`, `tenant_id`, `case_id`, `uploader_id`, `file_id`, `file_name`, `file_size`, `detected_mime`
- 上传失败日志最少字段：
  - `request_id`, `tenant_id`, `case_id`, `reason_code`, `reason_detail`
- 下载日志最少字段：
  - `request_id`, `tenant_id`, `file_id`, `access_mode(jwt|token)`, `result`

## 5. 错误码与状态码约定（对齐 BE-A05）
- `400 VALIDATION_ERROR`：文件名非法、参数缺失。
- `401 AUTH_REQUIRED`：未登录访问鉴权接口。
- `403 FILE_ACCESS_DENIED`：越权访问文件。
- `404 FILE_NOT_FOUND`：文件记录或文件内容不存在。
- `413 FILE_UPLOAD_INVALID`（或 `FILE_TOO_LARGE`）：文件超限。
- `415 FILE_UPLOAD_INVALID`（或 `FILE_TYPE_NOT_ALLOWED`）：文件类型不支持。
- `500 STORAGE_ERROR`：存储读写异常。

> 默认建议：若暂不扩增细分错误码，先统一到 `FILE_UPLOAD_INVALID` + detail 区分具体原因。

## 6. 配置项建议（新增环境变量）
- `FILE_UPLOAD_MAX_SIZE_MB=50`
- `FILE_UPLOAD_ALLOWED_MIME=application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg,image/png,image/jpg`
- `FILE_UPLOAD_ALLOWED_EXT=.pdf,.doc,.docx,.jpg,.jpeg,.png`
- `FILE_UPLOAD_SCAN_ENABLED=false`（预留）
- `FILE_UPLOAD_QUARANTINE_DIR=storage/quarantine`（预留）

## 7. 可分配子任务（开发拆分）
| 子任务 | 说明 | 目标目录 | 产出 |
|---|---|---|---|
| A06-1 | 上传准入校验器 | `backend/app/services/file.py` | 文件名/大小/MIME/扩展名校验 |
| A06-2 | 流式写入改造 | `backend/app/services/file.py` | chunk 写入与超限中断 |
| A06-3 | 路径安全与存储约束 | `services/file.py`、`models/file.py` | 存储路径不可越界 |
| A06-4 | 下载 token 脱敏与审计日志 | `routes_files.py`、`main.py` | 关键日志字段与脱敏策略 |
| A06-5 | 错误码对齐 | `core/errors.py`、`services/file.py`、`routes_files.py` | 413/415/403/404 语义稳定 |
| A06-6 | 单元/集成测试 | `backend/tests/` | 超限、类型非法、越权、token 过期测试 |
| A06-7 | 契约文档同步 | `docs/API-CONTRACTS.md`、`docs/production-deployment.md` | 上传限制与部署配置说明 |

## 8. 验收标准（DoD）

## 8.1 功能验收
- 合法文件可上传并可下载。
- 超过大小限制返回 `413`，错误响应结构正确。
- 非白名单类型返回 `415`，错误响应结构正确。
- 越权下载返回 `403`。
- 无效/过期 token 下载返回 `400/401`（按最终错误码约定）。

## 8.2 安全验收
- 上传过程不使用全量内存读取。
- 服务日志不打印完整下载 token。
- 下载路径不允许跳出 `LOCAL_STORAGE_DIR`。

## 8.3 联调验收
- Web AI 上传组件无需改 UI，超限与类型错误能收到稳定错误码。
- 小程序上传链路无需改页面，后端错误可通过现有错误处理显示。
- 现有 `GET /files/upload-policy` -> 上传 -> 列表刷新流程保持可用。

## 8.4 测试验收
- 最少新增 8 条测试：
  - 上传成功（pdf）
  - 空文件名
  - 超限文件
  - 非白名单类型
  - 客户端 MIME 与服务端检测冲突
  - 越权下载
  - token 失效下载
  - 文件内容缺失下载

## 9. 风险与默认策略
- 风险：严格类型校验可能拦截历史边缘文件。  
  默认策略：先灰度记录“将被拦截”日志，再切强拦截。
- 风险：流式写入改造可能影响现有对象存储适配。  
  默认策略：抽象统一写入接口，本地与对象存储共用同一校验器。
- 风险：短链 token 暴露在 URL，仍可能被外部系统记录。  
  默认策略：缩短有效期 + 日志脱敏 + 仅 HTTPS 传输。

## 10. 回滚策略
1. 保留旧上传路径与逻辑开关，若误拦截过多可临时降级到“仅记录不拦截”模式。
2. 大小/类型限制通过环境变量回调，支持热修配置。
3. 审计日志策略保留，不回滚 request_id 追踪。

## 11. 预估工作量
- 设计与评审：0.5 人日
- 后端实现与测试：1.5 人日
- 联调与文档同步：0.5 人日
- 合计：2.5 人日
