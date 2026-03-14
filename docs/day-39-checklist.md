# 第 39 天检查清单

## 今日目标

- 准备初始化与维护说明
- 为试点部署收尾

## 已完成

- `init_db.py` 可自动建库、迁移、写入种子数据
- `generate_notifications.py` 可生成截止提醒
- `scripts/smoke-test.ps1` 可做基础接口验证

## 建议的上线前动作

1. 先执行 `python init_db.py`
2. 再执行通知生成脚本
3. 最后运行冒烟测试脚本
