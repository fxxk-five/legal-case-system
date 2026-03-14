# 第 21 天检查清单

## 今日目标

- 完成案件详情页
- 接入文件上传和下载
- 支持状态更新

## 已完成

- 已完成案件详情页：
  - `web-frontend/src/views/CaseDetailView.vue`
- 已接入：
  - `GET /api/v1/cases/{id}`
  - `PATCH /api/v1/cases/{id}`
  - `POST /api/v1/files/upload`
  - `GET /api/v1/files/case/{case_id}`
  - `GET /api/v1/files/{file_id}/download`

## 当前可用流程

1. 在案件列表点击案号进入详情页
2. 查看案件基本信息
3. 上传案件材料
4. 下载已上传文件
5. 更新案件状态
