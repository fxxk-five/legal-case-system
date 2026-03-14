# 第 33 天检查清单

## 今日目标

- 实现通知模型与通知接口
- 生成基础提醒数据

## 已完成

- 已新增 `notifications` 表及迁移
- 已新增接口：
  - `GET /api/v1/notifications`
  - `PATCH /api/v1/notifications/{id}/read`
- 已新增提醒生成脚本：
  - `backend/app/scripts/generate_notifications.py`
- 已在初始化脚本中生成默认欢迎通知
