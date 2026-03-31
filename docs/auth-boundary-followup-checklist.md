# Auth 模块边界收口清单

更新时间：2026-04-01
当前分支：`codex/refactor-backend-module-boundaries`

## 已完成

- [x] 遗留 `app.services` 健康检查边界收口
  - 提交：`034552e`
- [x] `web_wechat_service.py` 写操作改走 `AuthRepository`
  - 提交：`5db383b`
- [x] `account_service.py` 写操作改走 `AuthRepository`
  - 验证：边界测试、改密链路、邀请注册、密码策略
- [x] `session_service.py` 写操作改走 `AuthRepository`
  - 验证：边界测试、刷新令牌、退出登录、会话轮换
- [x] `wechat_binding_service.py` 写操作改走 `AuthRepository`
  - 验证：边界测试、微信手机号登录、微信绑定回归
- [x] `wechat_account_binding_service.py` 写操作改走 `AuthRepository`
  - 验证：边界测试、微信绑定已有账号回归

## 待完成

- [x] 扩展 `backend/tests/test_auth_repository_boundaries.py`
  - 已覆盖：`session_service.py`、`wechat_binding_service.py`、`wechat_account_binding_service.py`
  - 要求：静态边界测试只锁定 auth 写路径，不误伤仓储层

- [ ] 跑 auth 定向回归矩阵
  - `backend/tests/test_auth_refresh_logout.py`
  - `backend/tests/test_auth_sms_and_invite_flow.py`
  - `backend/tests/test_auth_wechat_mini.py`
  - `scripts/check-auth-repository-boundaries.py`

## 执行顺序

1. auth 回归矩阵
2. 按结果决定是否继续补非 auth 模块边界
