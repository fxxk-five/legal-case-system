# Git 工作约定

> 适用于当前仓库的多主题并行开发状态。目标是避免混提、降低回滚成本、让每次提交都能解释清楚。

## 1. 当前仓库状态判断

当前仓库不处于“单主题开发”状态，而是同时存在以下情况：

- `main` 分支上有历史重构遗留改动
- 工作区长期不干净
- 暂存区可能混入多个主题
- 路径迁移正在进行中，例如 `api/routes_* -> modules/*`、`lib/* -> shared/*`

因此，后续开发必须以“隔离主题、显式暂存、按批收口”为核心原则。

## 2. 基本原则

1. 不直接在 `main` 上做新需求或新修复。
2. 不使用 `git add .`。
3. 每个任务只提交一个明确主题。
4. 提交前必须复核暂存区内容。
5. 提交前必须运行与本次改动相匹配的最小验证命令。

## 3. 标准开发流程

### 3.1 开始工作前

先执行：

```powershell
git branch --show-current
git status --short
git diff --cached --name-only
```

检查目标：

- 当前不应在 `main` 上直接开发
- 知道工作区里还有哪些未提交改动
- 知道暂存区里是否混有旧内容

### 3.2 创建任务分支

所有新任务从当前集成基线切分支：

```powershell
git switch -c codex/<task-name>
```

分支命名建议：

- `codex/fix-copy-governance`
- `codex/fix-force-reset-flow`
- `codex/fix-case-detail-feedback`
- `codex/refactor-auth-module`

### 3.3 开发过程中

只修改当前主题相关文件，不顺手处理无关问题。

如果发现无关脏改动影响当前任务：

- 优先绕开
- 必要时单独记录
- 不要在同一个提交里顺手清仓

### 3.4 暂存改动

只显式暂存本次任务文件：

```powershell
git add path/to/file1
git add path/to/file2
```

不要使用：

```powershell
git add .
git commit -a
```

### 3.5 提交前复核

必须执行：

```powershell
git diff --cached --name-only
git diff --cached --stat
```

如果出现无关文件，移出暂存区：

```powershell
git restore --staged <path>
```

### 3.6 提交前验证

按改动范围执行最小验证：

前端：

```powershell
cd web-frontend
npm test -- <target-tests>
npm run build
```

后端：

```powershell
cd D:\code\law\legal-case-system
pytest <target-tests> -q
```

文案/编码修复：

```powershell
python scripts/check_mojibake.py
```

### 3.7 提交

提交信息必须说明主题，不写模糊描述。

示例：

```powershell
git commit -m "fix: repair forced password reset flow"
git commit -m "fix: normalize user-facing error copy"
git commit -m "chore: add mojibake scan script"
```

## 4. 分支策略

### 4.1 `main`

- 只保留稳定或接近稳定的集成状态
- 不直接承接新任务开发

### 4.2 集成分支

当前仓库使用一个集成分支承接历史重构：

- `codex/integration-current-state`

用途：

- 收纳当前尚未收口的大规模迁移
- 作为后续任务分支的切出基线

### 4.3 任务分支

后续所有修复或需求从集成分支切出：

- `codex/fix-*`
- `codex/chore-*`
- `codex/refactor-*`

任务分支只解决一个问题域，不同时承担“业务修复 + 结构迁移”。

## 5. 当前仓库的清理策略

建议按三层节奏收口：

### 第一层：用户可见问题

- 文案乱码
- 改密流程
- 登录提示
- 案件详情提示
- 主路径 smoke

### 第二层：模块迁移

- `backend/app/api/routes_*` 向 `backend/app/modules/*` 收口
- `web-frontend/src/lib/*` 向 `shared/*`、`features/*` 收口
- 清除旧路径残余引用

### 第三层：结构清理

- 删除废弃文件
- 补文档
- 统一脚本
- 扩大自动化验证范围

## 6. 每日操作建议

每天开始前：

```powershell
git branch --show-current
git status --short
```

每天结束前：

```powershell
git diff --cached --name-only
git status --short
```

目标：

- 暂存区没有混入无关内容
- 自己清楚哪些改动已提交，哪些故意保留

## 7. 禁止事项

禁止以下操作，除非明确知道后果：

- `git add .`
- `git commit -a`
- `git reset --hard`
- `git checkout -- <path>`
- 在脏工作区里直接切换到另一个主题继续开发

## 8. 推荐命令速查

查看当前状态：

```powershell
git status --short
git diff --cached --name-only
```

创建任务分支：

```powershell
git switch codex/integration-current-state
git switch -c codex/fix-next-task
```

只暂存目标文件：

```powershell
git add file1 file2 file3
```

移出误暂存文件：

```powershell
git restore --staged <path>
```

查看本次将提交什么：

```powershell
git diff --cached --stat
```

## 9. 执行约定

从本文件生效后，后续任何新任务默认按以下顺序进行：

1. 检查状态
2. 切任务分支
3. 开发
4. 显式暂存
5. 复核暂存区
6. 跑最小验证
7. 提交

如果当前工作区不干净，则先说明“本次任务基于脏工作区执行”，并明确只提交本次主题文件。
