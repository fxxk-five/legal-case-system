# 第 5 天检查清单

## 今日目标

- 实现密码哈希
- 实现 JWT 登录认证
- 提供注册、登录、当前用户接口

## 已完成

- 已添加密码与 JWT 工具：
  - `backend/app/core/security.py`
- 已添加认证依赖：
  - `backend/app/dependencies/auth.py`
- 已添加认证服务：
  - `backend/app/services/auth.py`
- 已添加认证数据结构：
  - `backend/app/schemas/auth.py`
- 已添加接口：
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/users/me`

## 当前行为

- 注册接口默认注册到租户 `id=1`
- 登录返回 JWT
- JWT 中包含：
  - `sub`
  - `tenant_id`
  - `role`

## 使用前提

- 需要先完成数据库初始化
- 需要默认租户存在

## 测试建议

1. 先执行 `python init_db.py`
2. 使用默认管理员登录，或先调用注册接口创建律师账号
3. 用登录接口获取 token
4. 在 `Authorization: Bearer <token>` 下请求 `/api/v1/users/me`
