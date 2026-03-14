# 第 30 天检查清单

## 今日目标

- 完成律师管理页
- 支持新增、邀请、审批、启用禁用

## 已完成

- 已新增律师管理页：
  - `web-frontend/src/views/LawyersView.vue`
- 已接入：
  - `GET /api/v1/users/lawyers`
  - `POST /api/v1/users/lawyers`
  - `POST /api/v1/users/invite-lawyer`
  - `GET /api/v1/users/pending`
  - `PATCH /api/v1/users/{user_id}/approve`
  - `DELETE /api/v1/users/{user_id}/reject`
  - `PATCH /api/v1/users/{user_id}/status`
