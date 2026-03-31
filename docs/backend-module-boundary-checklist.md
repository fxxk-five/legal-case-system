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

- [x] `invites`
  - 完成：`service.py` 的提交/刷新操作已下沉到 `repository.py`
- [x] `notifications`
  - 完成：`service.py` 的提交/刷新操作已下沉到 `repository.py`
- [x] `clients`
  - 完成：`service.py` 的写操作已下沉到 `repository.py`
- [x] `analytics`
  - 完成：`service.py` 的提交/刷新操作已下沉到 `repository.py`
- [x] `users`
  - 完成：`service.py` 的写操作已下沉到 `repository.py`
- [x] `tenants`
  - 完成：`service.py`、`provisioning_service.py`、`tenants_budget_service.py` 的提交/刷新操作已下沉到 `repository.py`
- [x] `cases`
  - 完成：`command_service.py`、`remark_service.py` 的写操作已下沉到 `repository.py`
- [x] `files / upload`
  - 完成：`case_file_service.py`、`upload_service.py` 的写操作已下沉到 `repository.py`
- [x] `files / reanalysis-status`
  - 完成：`case_file_reanalysis_service.py` 的案件状态写操作已下沉到 `repository.py`
- [x] `files / delete-access`
  - 完成：`router.py` 已切换为 `CaseFileService` / `FilesRepository`，删除与访问写操作已收口到 `repository.py`
- [x] `ai / task-create`
  - 完成：`analysis_service.py`、`parse_service.py`、`falsification_service.py` 的写操作已收口到 `repository.py`
- [x] `ai / runtime-command`
  - 完成：`runtime_service.py`、`task_command_service.py`、`worker_dispatch_service.py` 的写操作已收口到 `repository.py`
- [x] `ai / submit-budget-flow`
  - 完成：`submission_service.py`、`budget_service.py`、`flow_service.py` 的写操作已收口到 `repository.py`

## 执行顺序

1. `invites`
2. `notifications`
3. `clients`
4. `analytics`
5. `users`
6. `tenants`
7. `cases`
8. `files / upload`
9. `files / reanalysis-status`
10. `files / delete-access`
11. `ai / task-create`
12. `ai / runtime-command`
13. `ai / submit-budget-flow`
