# Day 28 检查清单：当事人案件详情页

## 今日目标

- 展示当事人可见的案件详情
- 展示案件文件
- 保证权限只看到自己的案件

## 已完成内容

- 页面 [pages/client/case-detail.vue](/D:/code/law/legal-case-system/mini-program/pages/client/case-detail.vue)
- 后端已修复：`client` 角色调用 `GET /api/v1/cases` 时，只返回自己的案件
- 文件列表继续复用 `GET /api/v1/files/case/{case_id}`

## 当前限制

- 文件上传按钮还没有接完
- 时间轴展示还是简版
- 只取当前用户第一条案件作为详情入口

## 下一步建议

1. 补小程序上传能力
2. 增加案件时间线
3. 增加消息通知与材料状态反馈
