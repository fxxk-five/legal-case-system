# Frontend Bundle Optimization Baseline

更新日期：`2026-03-24`

## 1. 本次结果

- Web 前端已完成路由懒加载与 `Element Plus` 精确子路径导入优化。
- `npm run build` 不再出现大包体 warning。
- `vendor-element-plus` 由约 `774 kB` 降至约 `336 kB`。

## 2. 关键约束

- 禁止在模板组件解析上重新使用 `ElementPlusResolver()` 默认的 `element-plus/es` 总入口。
- `vite.config.js` 必须保持自定义 resolver，把 `El*` 组件解析到 `element-plus/es/components/<name>/index`。
- `ElOption`、`ElTableColumn`、`ElTabPane`、`ElTimelineItem` 这类子组件必须继续走当前父入口映射，不要直接改成不存在的子路径。
- 脚本内服务类导入必须继续使用子路径：
  - `element-plus/es/components/message/index`
  - `element-plus/es/components/message-box/index`
  - `element-plus/es/components/loading/index`

## 3. 验证命令

```powershell
cd web-frontend
npm run lint
npm run test
npm run build
```

## 4. 后续优化边界

- 当前优化已解决首要风险：公共 UI chunk 过大且触发构建告警。
- 如后续继续做体积治理，优先检查业务组件和图标使用面，不要先回退现有 resolver。
- 如需进一步拆包，只允许拆稳定第三方依赖或业务路由，不再对 `element-plus` 内部目录做高耦合手工切块。
