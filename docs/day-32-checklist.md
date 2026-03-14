# 第 32 天检查清单

## 今日目标

- 完成机构设置页面
- 支持管理员修改租户名称

## 已完成

- 已新增机构设置页：
  - `web-frontend/src/views/SettingsView.vue`
- 已接入：
  - `GET /api/v1/tenants/current`
  - `PATCH /api/v1/tenants/current`

## 当前限制

- 当前仅支持修改机构名称
- 联系方式、订阅信息等后续可继续补充
