# Web 前端说明

## 当前状态

Web 端已完成 P0-2 范围内的认证与角色化改造：

- 登录：手机号 + 密码，支持可选租户编码分流
- 注册：短信验证码发送与校验后提交注册
- 邀请码注册：支持机构律师通过邀请码 token 完成注册
- 角色导航矩阵：
  - 机构管理员：概览 / 案件管理 / 当事人管理 / 律师管理 / 分析管理
  - 独立律师：概览 / 案件管理 / 当事人管理 / 分析管理
  - 其他角色：Web 端最小落地页（待审批 / 访问受限 / 当事人小程序提示）
- 路由守卫与菜单权限逻辑集中化
- 当事人管理页面骨架（列表 + 详情占位）

## 关键页面

- `/login`：登录、手机号注册、邀请码注册
- `/`：概览
- `/cases`：案件管理
- `/clients`：当事人管理（骨架）
- `/lawyers`：律师管理（仅机构管理员）
- `/analysis`：分析管理（骨架）
- `/pending-approval`：待审批页
- `/access-restricted`：访问受限页
- `/client-mini-only`：当事人小程序引导页

## 默认联调地址

前端默认请求：

```text
http://127.0.0.1:8000/api/v1
```

如果后端地址变化，可修改：

- `src/lib/http.js`
- 或复制 `.env.example` 为 `.env` 后修改 `VITE_API_BASE_URL`

## 启动方式

```powershell
cd D:\code\law\legal-case-system\web-frontend
npm install
npm run dev
```

如果需要自定义接口地址：

```powershell
Copy-Item .env.example .env
```

## 最小手工验证清单

1. 注册流程（手机号注册）
   - 进入 `/login` -> 切到“注册”
   - 输入姓名/手机号/密码，发送验证码
   - 输入验证码并点击“校验验证码”
   - 校验通过后点击“提交注册”
2. 邀请码注册流程
   - 机构管理员在“律师管理”生成邀请链接
   - 打开链接后应自动进入“邀请码注册”页签并带入 token
   - 完成短信校验后提交注册，提示“等待管理员审批”
3. 登录与受限
   - 已激活律师/管理员登录后进入概览
   - 待审批账号登录后应落到 `/pending-approval`
   - 当事人账号登录后应落到 `/client-mini-only`
4. 菜单矩阵
   - 机构管理员应看到 5 项菜单
   - 独立律师应看到 4 项菜单（无“律师管理”）

## 构建验证

```powershell
npm run build
```

2026-03-24 补充说明：

- 当前 `npm run build` 已无前端大包体 warning。
- `Element Plus` 模板组件必须继续通过 `vite.config.js` 中的自定义 resolver 按 `element-plus/es/components/<name>/index` 子路径导入。
- 禁止改回 `ElementPlusResolver()` 默认的 `element-plus/es` 总入口，否则会重新把整包 UI 依赖拖入公共 chunk。
- 脚本内的 `ElMessage`、`ElMessageBox`、`ElLoadingDirective` 也必须维持子路径导入。

在当前仓库环境下该命令已通过（存在体积告警但不影响构建成功）。
