## ADDED Requirements

### Requirement: Mini Program SHALL support direct WeChat sign-in
The system SHALL use the mini program WeChat login flow as the default sign-in method for the mini program. The client MUST first submit the `wx.login` code to the backend, and the backend MUST decide whether the user can be logged in immediately or must continue with phone authorization.

#### Scenario: Bound user signs in directly
- **WHEN** a mini program user submits a valid `wx.login` code and the backend finds an active user already bound to the same WeChat identity
- **THEN** the backend returns access token, refresh token, current user profile, and a state indicating no further binding is required

#### Scenario: Unbound user must continue with phone authorization
- **WHEN** a mini program user submits a valid `wx.login` code and the backend does not find a bound active user
- **THEN** the backend returns a short-lived continuation state that requires the client to call the phone authorization step before login can finish

### Requirement: Backend SHALL bind mini program users by verified WeChat phone number
The backend SHALL complete mini program login or binding only after receiving a verified phone number from the WeChat phone authorization flow. The backend MUST use the verified phone number together with tenant context or invite context to resolve the target account safely.

#### Scenario: Unique account match binds automatically
- **WHEN** the backend receives a verified WeChat phone number that matches exactly one eligible account in the resolved tenant
- **THEN** the backend binds the WeChat identity to that account and returns tokens for that account

#### Scenario: Multi-tenant conflict blocks automatic login
- **WHEN** the backend receives a verified WeChat phone number that matches more than one tenant account and no `tenant_code` or invite token narrows the target
- **THEN** the backend returns a conflict state and MUST NOT log the user into any tenant automatically

### Requirement: Client invite flow SHALL create or bind client accounts during WeChat login
The system SHALL allow a client entering with a valid case invite token to complete first-time login by WeChat identity and verified phone number, and the backend SHALL create or bind the corresponding `client` account under the invite tenant and case.

#### Scenario: Invited client without account is created and linked
- **WHEN** a valid invite token is supplied and no client account exists for the resolved tenant and verified phone number
- **THEN** the backend creates an active `client` account, binds the WeChat identity, associates the account to the invited case, and returns tokens

#### Scenario: Invited client with existing account is reused
- **WHEN** a valid invite token is supplied and a matching client account already exists for the resolved tenant and verified phone number
- **THEN** the backend reuses that account, binds the WeChat identity if needed, keeps the tenant association unchanged, and returns tokens

### Requirement: Lawyer and admin roles SHALL NOT be created freely by WeChat login
The system SHALL preserve the existing organization governance rules during mini program WeChat sign-in. Lawyer-like roles and tenant admins MUST only bind to existing accounts, and pending approval users MUST remain blocked until approved.

#### Scenario: Pending lawyer remains blocked after WeChat binding
- **WHEN** a lawyer-like account matched by verified phone number is still pending approval or disabled
- **THEN** the backend refuses login and returns a non-active account error instead of issuing tokens

#### Scenario: No existing lawyer account cannot be auto-created
- **WHEN** a verified WeChat phone number does not match any existing lawyer-like account and no client invite token is present
- **THEN** the backend rejects free account creation and returns guidance to use invite registration or Web registration first
