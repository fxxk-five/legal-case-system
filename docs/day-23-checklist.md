# Day 23 检查清单：微信登录与角色识别

## 今日目标

- 打通微信登录
- 后端根据 `code` 换取 `openid`
- 若未绑定手机号，则进入绑定流程

## 已完成内容

- 新增接口 `POST /api/v1/auth/wx-mini-login`
- 新增接口 `POST /api/v1/auth/wx-mini-bind`
- 后端支持 `WECHAT_MINIAPP_MOCK_LOGIN`
- 小程序登录页已接入这两个接口

## 当前逻辑

1. 小程序调用 `uni.login()` 获取 `code`
2. 后端通过 `wx-mini-login` 返回 `wechat_openid`
3. 若该 openid 已绑定用户，直接签发 token
4. 若未绑定，进入手机号绑定页

## 开发建议

- 本地开发先保留 `WECHAT_MINIAPP_MOCK_LOGIN=true`
- 真正接微信环境时，再填真实 `AppID/AppSecret`
- 律师端优先走“绑定已有账号”流程，避免重复创建律师
