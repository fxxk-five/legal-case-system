# Day 24 检查清单：律师端首页

## 今日目标

- 建立律师端首页
- 展示案件列表
- 提供新建案件入口

## 已完成内容

- 页面 [pages/lawyer/home.vue](/D:/code/law/legal-case-system/mini-program/pages/lawyer/home.vue)
- 页面 [pages/lawyer/create-case.vue](/D:/code/law/legal-case-system/mini-program/pages/lawyer/create-case.vue)
- 已接入 `GET /api/v1/cases`
- 已接入 `POST /api/v1/cases`

## 当前交互

- 进入首页自动拉取案件列表
- 点击“新建案件”进入创建页
- 创建成功后跳转案件详情页

## 下一步建议

- 后续可以补状态筛选
- 可以加“仅看我负责的案件”
- 可以接通知未读角标
