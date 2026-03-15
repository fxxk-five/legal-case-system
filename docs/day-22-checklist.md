# Day 22 检查清单：小程序项目初始化

## 今日目标

- 初始化 `mini-program` 目录
- 确认技术路线为 `uni-app + 微信开发者工具 + FastAPI`
- 配置基础页面、清单文件和请求封装

## 已完成内容

- 已创建 `mini-program/App.vue`
- 已创建 `mini-program/main.js`
- 已创建 `mini-program/pages.json`
- 已创建 `mini-program/manifest.json`
- 已创建 `mini-program/common/http.js`
- 已创建登录页、律师页、当事人页骨架

## 你现在要做的事

1. 用 HBuilderX 导入 [mini-program](/D:/code/law/legal-case-system/mini-program)。
2. 在 `manifest.json` 中填入你自己的微信小程序 `appid`。
3. 点击“运行到小程序模拟器”，让微信开发者工具接管调试。

## 注意事项

- 代码可以继续在 VS Code 写。
- 真机预览、授权能力、上传体验版，仍然必须经过微信开发者工具。
- 当前小程序主后端仍是 FastAPI，不切换到微信云开发。
