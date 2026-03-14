# 第 18 天检查清单

## 今日目标

- 落地案件文件上传能力
- 先使用本地开发存储方案
- 记录文件元数据到数据库

## 已完成

- 已添加文件上传接口：
  - `POST /api/v1/files/upload`
- 已添加案件文件列表接口：
  - `GET /api/v1/files/case/{case_id}`
- 已添加文件下载接口：
  - `GET /api/v1/files/{file_id}/download`
- 已添加文件数据结构：
  - `backend/app/schemas/file.py`
- 已添加本地文件存储服务：
  - `backend/app/services/file.py`

## 当前实现说明

- 上传文件先保存到本地目录 `backend/storage/`
- 再把文件路径和元数据写入 `files` 表
- 后续接入云存储时，只需要替换 `services/file.py` 的实现

## 使用方式

1. 先保证服务已经启动
2. 使用登录 token 调用上传接口
3. 上传时携带 `case_id`
4. 然后通过列表接口查看文件记录
