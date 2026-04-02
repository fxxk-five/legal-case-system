# 当前状态分支拆分清单

> 基于 `codex/integration-current-state` 当前工作区状态生成。目标是把剩余未提交改动按主题拆成可以独立提交、独立验证、独立回滚的分支批次。

## 1. 当前未提交改动概览

当前未提交改动约 `406` 条，按主题粗分如下：

- `backend-module-refactor`: `140`
- `docs-and-plans`: `64`
- `web-frontend-structure`: `56`
- `mini-program-structure`: `51`
- `backend-tests`: `38`
- `contracts-and-other`: `32`
- `scripts-and-tooling`: `18`
- `backend-migrations`: `8`

结论：

- 当前剩余改动并不适合继续在一个分支里推进
- 应按“结构重构优先收口，再补文档与脚本，再做环境与杂项”的顺序拆分

## 2. 推荐拆分顺序

建议拆成以下 7 个主题分支。

### 批次 1：后端模块边界收口

分支名：

- `codex/refactor-backend-module-boundaries`

范围：

- `backend/app/modules/*`
- `backend/app/integrations/*`
- `backend/app/api/*`
- `backend/app/models/*`
- `backend/app/services/*`
- `backend/app/schemas/*`
- `backend/app/repositories/*`
- `backend/app/db/*`

目标：

- 让后端目录迁移与模块边界形成一个自洽提交
- 停止“旧路径删除一半、新路径新增一半”的中间态

验证建议：

- 后端路由测试
- 认证测试
- 案件主流程测试
- `pytest backend/tests -q` 先从模块相关子集跑起

### 批次 2：后端测试与迁移脚本收口

分支名：

- `codex/refactor-backend-tests-and-migrations`

范围：

- `backend/tests/*`
- `backend/alembic/versions/*`

目标：

- 让数据库迁移与对应测试一起闭环
- 避免“结构已经改了，测试和迁移滞后”

验证建议：

- `pytest backend/tests -q`
- 如涉及迁移，补一次升级/降级验证

### 批次 3：Web 前端结构迁移收口

分支名：

- `codex/refactor-web-frontend-structure`

范围：

- `web-frontend/src/app/*`
- `web-frontend/src/features/*`
- `web-frontend/src/shared/*`
- `web-frontend/src/pages/*`
- `web-frontend/src/lib/*`
- `web-frontend/src/views/*`
- `web-frontend/src/router/*`
- `web-frontend/src/stores/*`

目标：

- 完成 `views -> pages`、`lib -> shared/features`、`stores -> app/features` 的收口
- 消除旧目录残留引用

验证建议：

- `npm run build`
- 针对路由、认证、案件详情的单测或 smoke

### 批次 4：小程序结构迁移收口

分支名：

- `codex/refactor-mini-program-structure`

范围：

- `mini-program/common/*`
- `mini-program/features/*`
- `mini-program/shared/*`
- `mini-program/pages/*`
- `mini-program/components/*`

目标：

- 完成 `common/*` 向 `features/*`、`shared/*` 的迁移
- 保证律师端/当事人端路径不再双轨并存

验证建议：

- 小程序静态检查
- 登录、案件、上传、AI 页面 smoke

### 批次 5：脚本与工程化工具收口

分支名：

- `codex/chore-tooling-and-checks`

范围：

- `scripts/*`
- `.githooks/*`
- `.github/*`
- `.claude/*`
- `.codebuddy/*`

目标：

- 把检查脚本、状态脚本、边界检查脚本独立成一个工程化批次
- 避免和业务修复混在一起

验证建议：

- 逐个跑关键脚本
- 确认失败码与输出符合预期

### 批次 6：文档与计划清理

分支名：

- `codex/docs-cleanup-and-rebaseline`

范围：

- `docs/*`
- `plans/*`

目标：

- 清理已废弃文档
- 保留当前有效文档
- 让状态文档、用户手册、验收清单与现状一致

验证建议：

- 文档链接完整性检查
- 状态文档与实际改动交叉核对

### 批次 7：环境与杂项收尾

分支名：

- `codex/chore-runtime-and-config`

范围：

- `README.md`
- `backend/.env.example`
- `backend/README.md`
- `deploy/*`
- `docker-compose.prod.yml`
- `backend/app/core/*`
- `backend/app/main.py`
- `backend/app/scripts/*`
- 其他不适合归入前六批的杂项

目标：

- 收口配置、运行时、启动方式和部署说明

## 3. 执行方式

每一批都从集成分支重新切：

```powershell
git switch codex/integration-current-state
git switch -c codex/<topic-branch>
```

然后只处理该批次对应文件，不跨批混做。

## 4. 暂存与提交要求

每一批提交都必须：

1. 显式 `git add` 本批文件
2. 执行 `git diff --cached --name-only`
3. 执行对应最小验证
4. 提交信息只描述这一批主题

示例：

```powershell
git commit -m "refactor: finalize backend module boundaries"
git commit -m "refactor: migrate web frontend to app/features/shared structure"
git commit -m "chore: add repository boundary and status checks"
```

## 5. 建议优先级

建议按以下顺序推进：

1. `codex/refactor-backend-module-boundaries`
2. `codex/refactor-web-frontend-structure`
3. `codex/refactor-mini-program-structure`
4. `codex/refactor-backend-tests-and-migrations`
5. `codex/chore-tooling-and-checks`
6. `codex/docs-cleanup-and-rebaseline`
7. `codex/chore-runtime-and-config`

## 6. 使用说明

本清单不是“今天一次做完”的任务列表，而是后续一段时间内的拆分基线。

原则只有一个：

- 不再让“用户修复 + 结构迁移 + 测试迁移 + 文档删除 + 脚本新增”出现在同一个提交里。
