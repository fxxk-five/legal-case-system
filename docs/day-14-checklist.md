# 第 14 天检查清单

## 今日目标

- 完成登录页
- 建立基础后台布局
- 配置登录守卫

## 已完成

- 已完成登录页：
  - `web-frontend/src/views/LoginView.vue`
- 已完成后台布局：
  - `web-frontend/src/views/DashboardLayout.vue`
- 已完成路由守卫
- 已接入登录接口：
  - `POST /api/v1/auth/login`

## 当前行为

- 未登录时访问后台页面会跳转到 `/login`
- 登录成功后会获取 token 并保存到本地存储
