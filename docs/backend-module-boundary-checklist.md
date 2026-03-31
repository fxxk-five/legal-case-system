# 后端模块边界总清单

更新时间：2026-04-01
当前分支：`codex/refactor-backend-module-boundaries`

## 已完成

- [x] `legacy app.services`
  - 提交：`034552e`
- [x] `auth`
  - 提交：`5db383b`
  - 提交：`72699ba`
  - 提交：`1023107`
  - 提交：`7040aaa`
  - 提交：`c3cae22`

## 待完成

- [ ] `invites`
  - 目标：`service.py` 的提交/刷新操作下沉到 `repository.py`
- [x] `notifications`
  - 完成：`service.py` 的提交/刷新操作已下沉到 `repository.py`
- [ ] `clients`
  - 目标：`service.py` 的写操作下沉到 `repository.py`
- [x] `analytics`
  - 完成：`service.py` 的提交/刷新操作已下沉到 `repository.py`
- [ ] `users`
  - 目标：`service.py` 的写操作下沉到 `repository.py`
- [ ] `tenants`
  - 目标：`service.py`、`provisioning_service.py`、`tenants_budget_service.py` 的提交/刷新操作下沉到 `repository.py`
- [ ] `cases`
  - 目标：`command_service.py`、`remark_service.py` 的写操作下沉到 `repository.py`
- [ ] `files`
  - 目标：`case_file_service.py`、`upload_service.py`、`router.py` 的写操作收口
- [ ] `ai`
  - 目标：各 `services/*.py` 的写操作收口到 `repository.py`

## 执行顺序

1. `invites`
2. `notifications`
3. `clients`
4. `analytics`
5. `users`
6. `tenants`
7. `cases`
8. `files`
9. `ai`
