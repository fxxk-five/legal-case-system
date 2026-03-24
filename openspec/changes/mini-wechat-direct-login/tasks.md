## 1. Spec And Contract Freeze

- [x] 1.1 Update blueprint, task list, and OpenSpec artifacts so the WeChat direct-login scope is fixed before coding
- [x] 1.2 Define API contracts for `wx-mini-login`, `wx-mini-phone-login`, `wx-mini-bind-existing`, and logout revocation behavior

## 2. Backend Authentication Core

- [x] 2.1 Add data-model fields for WeChat binding, login channel auditing, and revocable auth sessions
- [x] 2.2 Implement WeChat login helpers for `jscode2session`, phone-number exchange, and access-token caching
- [x] 2.3 Implement the login state machine for direct login, phone authorization continuation, invite-based client binding, and tenant conflict handling
- [x] 2.4 Upgrade `/auth/logout` to revoke the current refresh session and reject future refresh attempts for the same token

## 3. Mini Program Client Flow

- [x] 3.1 Replace the default mini login entry with WeChat direct login and phone authorization actions
- [x] 3.2 Add UI states for tenant conflict, pending approval, invite-first client binding, and login failure fallback
- [x] 3.3 Add visible logout entry points in lawyer workspace and client flow and wire them to local session cleanup

## 4. Platform Configuration And Validation

- [ ] 4.1 Configure AppID, AppSecret, phone-number capability, and legal domains in WeChat / Tencent Cloud environments
- [x] 4.2 Add automated tests for direct login, tenant conflict, invite client creation, and logout revocation
- [ ] 4.3 Run real-device validation and keep a legacy-login fallback switch until the new flow is stable
