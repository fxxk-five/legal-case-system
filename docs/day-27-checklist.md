# Day 27 检查清单：当事人进入与绑定

## 今日目标

- 当事人扫码进入案件
- 首次进入时绑定手机号
- 自动把当事人与案件关联

## 已完成内容

- 页面 [pages/client/entry.vue](/D:/code/law/legal-case-system/mini-program/pages/client/entry.vue)
- `wx-mini-bind` 支持 `case_invite_token`
- 当令牌有效时，后端会自动把 `case.client_id` 绑定到当前用户

## 当前链路

1. 律师生成邀请链接
2. 当事人进入 `pages/client/entry`
3. 小程序调用 `wx-mini-login`
4. 再调用 `wx-mini-bind`
5. 后端自动完成用户绑定和案件关联

## 注意事项

- 当前当事人若不存在，会自动创建为 `client`
- 当前默认密码策略仅用于开发联调，后续需要进一步收紧
