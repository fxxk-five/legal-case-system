# Day 25 检查清单：律师端案件详情

## 今日目标

- 展示案件详情
- 展示文件列表
- 提供邀请当事人的入口

## 已完成内容

- 页面 [pages/lawyer/case-detail.vue](/D:/code/law/legal-case-system/mini-program/pages/lawyer/case-detail.vue)
- 已接入 `GET /api/v1/cases/{id}`
- 已接入 `GET /api/v1/files/case/{case_id}`
- 已接入 `GET /api/v1/cases/{id}/invite-qrcode`

## 当前实现说明

- 现在先返回小程序路径 `pages/client/entry?token=...`
- 这一步先把邀请链路跑通
- 真正的小程序码图片生成，可以放到后续再接微信接口

## 待补项

- 小程序端文件上传
- 状态修改
- 更完整的案件时间线展示
