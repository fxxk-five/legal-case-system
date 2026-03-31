from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Request, Response, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.client_source import is_mini_program_request as is_mini_program_request_source
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.security import REFRESH_TOKEN_TYPE, create_access_token, create_refresh_token, hash_token
from app.models.auth_session import AuthSession
from app.models.user import User
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import LogoutRequest, Token, TokenRefreshRequest


class AuthSessionService:
    def __init__(
        self,
        db: Session,
        *,
        ensure_user_can_login: Callable[..., None],
        resolve_login_channel: Callable[..., str],
    ) -> None:
        self.db = db
        self.repository = AuthRepository(db)
        self.ensure_user_can_login = ensure_user_can_login
        self.resolve_login_channel = resolve_login_channel

    @staticmethod
    def _token_extra_data(user: User) -> dict:
        return {
            "tenant_id": user.tenant_id,
            "role": user.role,
            "is_tenant_admin": user.is_tenant_admin,
        }

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _resolve_device_type(request: Request | None) -> str:
        return "mini-program" if is_mini_program_request_source(request) else "web"

    @staticmethod
    def _parse_numeric_claim(value: object) -> int | None:
        if not isinstance(value, (int, float, str)):
            return None
        normalized = str(value)
        if not normalized.isdigit():
            return None
        return int(normalized)

    @staticmethod
    def auth_required(message: str = "登录状态无效，请重新登录。") -> AppError:
        return AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message=message,
            detail=message,
        )

    def issue_token_pair(
        self,
        *,
        user: User,
        request: Request | None,
        channel: str,
        session_id: int | None = None,
        touch_login_audit: bool = True,
    ) -> Token:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        if session_id is None:
            auth_session = AuthSession(
                user_id=user.id,
                tenant_id=user.tenant_id,
                refresh_token_hash="pending",
                expires_at=expires_at,
                last_used_at=now,
                channel=channel,
                device_type=self._resolve_device_type(request),
                client_ip=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
            )
            self.repository.save(auth_session)
            self.repository.flush()
        else:
            auth_session = self.repository.get_auth_session(
                session_id=session_id,
                user_id=user.id,
                tenant_id=user.tenant_id,
            )
            if auth_session is None:
                raise self.auth_required()
            if auth_session.is_revoked:
                raise self.auth_required("登录会话已失效，请重新登录。")
            auth_session.expires_at = expires_at
            auth_session.last_used_at = now
            auth_session.channel = channel or auth_session.channel
            auth_session.device_type = self._resolve_device_type(request)
            auth_session.client_ip = request.client.host if request and request.client else auth_session.client_ip
            auth_session.user_agent = request.headers.get("user-agent") if request else auth_session.user_agent

        if touch_login_audit:
            user.previous_login_at = user.last_login_at
            user.last_login_at = now
            user.last_login_channel = channel
            self.repository.save(user)
            self.repository.flush()

        token_extra = {**self._token_extra_data(user), "sid": auth_session.id}
        access_token = create_access_token(user.id, extra_data=token_extra)
        refresh_token = create_refresh_token(
            user.id,
            session_id=auth_session.id,
            extra_data=self._token_extra_data(user),
        )

        auth_session.refresh_token_hash = hash_token(refresh_token)
        auth_session.expires_at = expires_at
        auth_session.last_used_at = now
        auth_session.is_revoked = False
        auth_session.revoked_at = None
        self.repository.save(auth_session)
        self.repository.commit()
        self.repository.refresh(user)

        return Token(access_token=access_token, refresh_token=refresh_token)

    def _get_valid_refresh_session(
        self,
        *,
        payload: dict,
        refresh_token: str,
        user: User,
    ) -> AuthSession:
        session_id = self._parse_numeric_claim(payload.get("sid"))
        if session_id is None:
            raise self.auth_required()

        auth_session = self.repository.get_auth_session(
            session_id=session_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
        )
        if auth_session is None:
            raise self.auth_required()
        if auth_session.is_revoked:
            raise self.auth_required("登录会话已失效，请重新登录。")
        if auth_session.refresh_token_hash != hash_token(refresh_token):
            raise self.auth_required("登录会话已失效，请重新登录。")

        expires_at = self._as_utc(auth_session.expires_at)
        if expires_at is None or expires_at <= datetime.now(timezone.utc):
            raise self.auth_required("登录会话已过期，请重新登录。")
        return auth_session

    def refresh_token(
        self,
        *,
        payload: TokenRefreshRequest,
        request: Request | None,
    ) -> Token:
        try:
            token_payload = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise self.auth_required("刷新令牌无效或已过期。") from exc

        if token_payload.get("token_type") != REFRESH_TOKEN_TYPE:
            raise self.auth_required("刷新令牌无效或已过期。")

        subject = self._parse_numeric_claim(token_payload.get("sub"))
        if subject is None:
            raise self.auth_required("刷新令牌无效或已过期。")

        user = self.repository.get_user_by_id(user_id=subject)
        if user is None:
            raise self.auth_required("用户不存在或已失效，请重新登录。")
        self.ensure_user_can_login(user, allow_pending=True)

        token_tenant_id = token_payload.get("tenant_id")
        if token_tenant_id is not None:
            tenant_id = self._parse_numeric_claim(token_tenant_id)
            if tenant_id is None or user.tenant_id != tenant_id:
                raise self.auth_required("租户鉴权失败，请重新登录。")

        auth_session = self._get_valid_refresh_session(
            payload=token_payload,
            refresh_token=payload.refresh_token,
            user=user,
        )
        return self.issue_token_pair(
            user=user,
            request=request,
            channel=auth_session.channel or self.resolve_login_channel(request),
            session_id=auth_session.id,
            touch_login_audit=False,
        )

    def logout(
        self,
        *,
        current_user: User,
        payload: LogoutRequest | None = None,
    ) -> Response:
        revoked_any = False
        now = datetime.now(timezone.utc)

        current_session_id = getattr(current_user, "_auth_session_id", None)
        if isinstance(current_session_id, int):
            current_session = self.repository.get_auth_session(
                session_id=current_session_id,
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
            )
            if current_session is not None and not current_session.is_revoked:
                current_session.is_revoked = True
                current_session.revoked_at = now
                current_session.last_used_at = now
                self.repository.save(current_session)
                revoked_any = True

        refresh_token_value = (payload.refresh_token if payload else "") or ""
        if refresh_token_value:
            try:
                token_payload = jwt.decode(refresh_token_value, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            except JWTError:
                token_payload = None

            if token_payload and token_payload.get("token_type") == REFRESH_TOKEN_TYPE:
                session_id = self._parse_numeric_claim(token_payload.get("sid"))
                if session_id is not None:
                    auth_session = self.repository.get_auth_session(
                        session_id=session_id,
                        user_id=current_user.id,
                        tenant_id=current_user.tenant_id,
                    )
                    if auth_session is not None and auth_session.refresh_token_hash == hash_token(refresh_token_value):
                        auth_session.is_revoked = True
                        auth_session.revoked_at = now
                        auth_session.last_used_at = now
                        self.repository.save(auth_session)
                        revoked_any = True

        if revoked_any:
            self.repository.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
