# 分支模型建议

> 适用于当前仓库的阶段性分支模型。目标是同时解决两类问题：
>
> 1. 当前仓库处于“大量改动正在集成”的状态
> 2. 未来还需要一个长期可持续的开发分支模型

## 1. 结论

当前仓库不适合立即切到“`main` + `dev`”的简单双分支模式。

更适合分两个阶段：

### 阶段一：集成收口阶段

当前先使用：

- `main`
- `codex/integration-current-state`
- `codex/<task-branch>`

### 阶段二：上线后稳定开发阶段

上线调试完成后，再切换为：

- `main`
- `release/<version>`
- `dev`
- `feature/<topic>`

## 2. 为什么现在不直接进入 `dev`

如果现在直接建立 `dev`，并把当前所有剩余改动继续往 `dev` 里堆，会有几个问题：

1. `dev` 会继承当前混合状态，而不是一个干净的开发基线
2. 结构重构、用户修复、文档迁移仍然会混在一起
3. 上线前一旦发现问题，无法快速判断是哪一类改动导致
4. `dev` 本应承接“后续持续开发”，而不是承接“当前大规模收口中的混乱状态”

因此，`dev` 不应该用来解决当前历史包袱，而应该在**当前集成线稳定后**再建立。

## 3. 当前阶段推荐模型

### 3.1 `main`

职责：

- 保留当前主线历史
- 不直接继续承接新改动
- 作为历史锚点与对照基线

当前建议：

- 暂时不要在 `main` 上继续开发

### 3.2 `codex/integration-current-state`

职责：

- 作为“最终版候选集成线”
- 承接当前尚未收口的大改动
- 用于汇总已经存在但尚未稳定的迁移与修复

当前建议：

- 所有后续任务都从这条线切出子分支
- 这条线不直接承接多个主题同时开发

### 3.3 `codex/<task-branch>`

职责：

- 每个主题一个分支
- 从 `codex/integration-current-state` 切出
- 独立验证、独立提交、独立回收

示例：

- `codex/refactor-backend-module-boundaries`
- `codex/refactor-web-frontend-structure`
- `codex/refactor-mini-program-structure`
- `codex/chore-tooling-and-checks`

## 4. 上线前推荐模型

当 `codex/integration-current-state` 已经收口，并且通过主路径验证后，再切发布分支：

- `release/first-production`

职责：

- 只处理上线前问题
- 只允许小范围修复
- 不再继续做目录重构或结构迁移

这一阶段的规则：

- 只修发布阻塞项
- 不做大范围重构
- 所有修复都回灌到集成线

## 5. 上线后推荐模型

上线稳定后，再建立长期开发分支：

- `main`
- `dev`
- `feature/<topic>`

### 5.1 `main`

职责：

- 生产稳定线
- 只接收经过验证的发布版本或热修复

### 5.2 `dev`

职责：

- 后续日常开发主线
- 承接多个已完成的 `feature/*` 分支
- 作为下一次发布的集成候选线

### 5.3 `feature/<topic>`

职责：

- 单需求或单修复开发分支
- 从 `dev` 切出
- 完成后合回 `dev`

示例：

- `feature/p0-copy-governance`
- `feature/smoke-login-matrix`
- `feature/wechat-auth-hardening`

## 6. 推荐演进路径

### 当前开始

保持：

- `main`
- `codex/integration-current-state`

然后所有后续收口工作走：

- `codex/<task-branch>`

### 当前集成线稳定后

切发布线：

- `release/first-production`

### 正式上线稳定后

建立长期分支：

- `dev`

## 7. 操作建议

### 当前阶段

从集成线切任务分支：

```powershell
git switch codex/integration-current-state
git switch -c codex/refactor-backend-module-boundaries
```

任务完成后：

- 回到 `codex/integration-current-state`
- 合并任务分支
- 继续下一批

### 上线准备阶段

从集成线切发布线：

```powershell
git switch codex/integration-current-state
git switch -c release/first-production
```

### 上线稳定后

建立长期开发分支：

```powershell
git switch main
git switch -c dev
```

## 8. 简化理解

一句话概括：

- **现在**：不要急着用 `dev`，先把 `codex/integration-current-state` 当作最终版候选线收口
- **上线前**：从候选线切 `release/*`
- **上线后**：再建立真正长期使用的 `dev`

## 9. 最终建议

你原本的思路“先做最终版，再上线调试，之后建立 `dev`”在方向上是合理的。

但要补一层中间结构：

- 不要直接把当前脏状态当最终版
- 先用 `codex/integration-current-state` 做候选集成线
- 候选线内部仍然按主题分支逐批收口

这样做的好处是：

- 不打断你“先上线”的总体目标
- 同时避免把当前混乱状态直接固化成未来长期开发基线
