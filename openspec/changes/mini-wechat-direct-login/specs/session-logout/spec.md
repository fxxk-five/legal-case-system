## ADDED Requirements

### Requirement: Web and mini clients SHALL expose explicit logout entry points
The system SHALL provide a visible logout action in both the Web workspace and the mini program workspace / client flow so that users can intentionally end the current session.

#### Scenario: Workspace user logs out from visible entry
- **WHEN** a logged-in user taps or clicks the logout entry in Web or mini program
- **THEN** the client calls the logout API, clears local session data, and returns the user to the login screen

### Requirement: Logout SHALL revoke the current refresh session on the server
The backend SHALL revoke the current refresh session when logout is requested with a valid refresh token. After revocation, the same refresh token MUST NOT be accepted again.

#### Scenario: Revoked refresh token cannot refresh again
- **WHEN** a user logs out successfully and then replays the same refresh token to the refresh endpoint
- **THEN** the backend rejects the request as invalid or expired and does not issue a new access token

### Requirement: Logout SHALL preserve WeChat binding while clearing local access
The system SHALL treat logout as session termination, not account unbinding. Logout MUST clear local tokens and cached user data, but it MUST NOT remove the WeChat identity already linked to the account.

#### Scenario: Bound user logs out and signs in again later
- **WHEN** a previously bound mini program user logs out and later performs WeChat direct sign-in again
- **THEN** the backend recognizes the existing WeChat binding and allows direct login without requiring a new manual bind step
