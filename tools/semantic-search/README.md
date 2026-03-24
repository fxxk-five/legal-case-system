# Semantic Search Tools

本目录用于本地安装和运行免费的代码搜索工具（不依赖全局安装）。

## 已安装

- `@sammysnake/fast-context-mcp`（MCP 语义搜索）
- `@ast-grep/cli`（AST 语义检索）
- 系统已可用 `rg`（ripgrep）

## 快速验证

在仓库根目录执行：

```powershell
npm --prefix tools/semantic-search run sg:version
rg --version
```

## fast-context 说明

- 当前已切换为本地 MCP 服务路径（`~/.codex/config.toml`）。
- `fast-context` 需要 Windsurf API Key 才能真正执行语义搜索。
- 取 Key 的两种方式：
  1. 安装并登录 Windsurf（免费账号可用），工具会自动从本地数据库读取；
  2. 手动设置环境变量 `WINDSURF_API_KEY`。

如果未安装 Windsurf，`fast_context_search` 会报 `Windsurf API Key not found`。

