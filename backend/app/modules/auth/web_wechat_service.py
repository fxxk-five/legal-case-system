from __future__ import annotations

from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import quote

from fastapi import Request, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.statuses import is_active_user_status
from app.integrations.wechat.service import generate_mini_program_code
from app.models.user import User
from app.models.web_login_ticket import WebLoginTicket
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import Token, WebWechatLoginTicketCreateRead, WebWechatLoginTicketStatusRead


WEB_WECHAT_LOGIN_TICKET_EXPIRE_MINUTES = 5
WEB_WECHAT_LOGIN_SCENE_PREFIX = "web-login:"


class WebWechatLoginService:
    def __init__(
        self,
        db: Session,
        *,
        issue_token_pair,
        auth_required,
    ) -> None:
        self.repository = AuthRepository(db)
        self.issue_token_pair = issue_token_pair
        self.auth_required = auth_required

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _web_login_scene(ticket: str) -> str:
        return f"{WEB_WECHAT_LOGIN_SCENE_PREFIX}{ticket}"

    @staticmethod
    def _web_login_launch_path(ticket: str) -> str:
        return f"{settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE}?scene=web-login&ticket={ticket}"

    def _build_web_login_status_payload(self, ticket_record: WebLoginTicket) -> WebWechatLoginTicketStatusRead:
        now = datetime.now(timezone.utc)
        expires_at = self._as_utc(ticket_record.expires_at) or now
        expires_in_seconds = max(0, int((expires_at - now).total_seconds()))
        return WebWechatLoginTicketStatusRead(
            ticket=ticket_record.ticket,
            status=ticket_record.status,
            expires_at=expires_at,
            expires_in_seconds=expires_in_seconds,
            confirmed_at=self._as_utc(ticket_record.confirmed_at),
            consumed_at=self._as_utc(ticket_record.consumed_at),
            can_exchange=ticket_record.status == "confirmed" and expires_in_seconds > 0,
        )

    def _expire_web_login_ticket_if_needed(self, ticket_record: WebLoginTicket) -> WebLoginTicket:
        if ticket_record.status in {"consumed", "expired"}:
            return ticket_record

        expires_at = self._as_utc(ticket_record.expires_at)
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            ticket_record.status = "expired"
            self.repository.save_commit_refresh(ticket_record)
        return ticket_record

    def _get_web_login_ticket_or_404(self, *, ticket: str) -> WebLoginTicket:
        ticket_record = self.repository.get_web_login_ticket_by_ticket(ticket=ticket)
        if ticket_record is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="Web 微信扫码登录票据不存在。",
                detail="Web 微信扫码登录票据不存在。",
            )
        return self._expire_web_login_ticket_if_needed(ticket_record)

    def create_ticket(self, *, request: Request) -> WebWechatLoginTicketCreateRead:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=WEB_WECHAT_LOGIN_TICKET_EXPIRE_MINUTES)
        ticket = token_urlsafe(12)
        ticket_record = WebLoginTicket(
            ticket=ticket,
            status="pending",
            expires_at=expires_at,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        self.repository.save_commit_refresh(ticket_record)

        base_path = f"{settings.API_V1_STR}/auth/web-wechat-login/{quote(ticket_record.ticket)}"
        return WebWechatLoginTicketCreateRead(
            ticket=ticket_record.ticket,
            status=ticket_record.status,
            expires_at=expires_at,
            expires_in_seconds=int((expires_at - now).total_seconds()),
            mini_program_page=settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE,
            mini_program_scene=self._web_login_scene(ticket_record.ticket),
            launch_path=self._web_login_launch_path(ticket_record.ticket),
            qr_code_url=f"{base_path}/mini-code",
            poll_url=base_path,
        )

    def get_ticket_status(self, *, ticket: str) -> WebWechatLoginTicketStatusRead:
        ticket_record = self._get_web_login_ticket_or_404(ticket=ticket)
        return self._build_web_login_status_payload(ticket_record)

    def get_ticket_mini_code(self, *, ticket: str) -> FastAPIResponse:
        ticket_record = self._get_web_login_ticket_or_404(ticket=ticket)
        content, content_type = generate_mini_program_code(
            page=settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE,
            scene=self._web_login_scene(ticket_record.ticket),
        )
        return FastAPIResponse(content=content, media_type=content_type)

    def confirm_ticket(self, *, ticket: str, current_user: User) -> WebWechatLoginTicketStatusRead:
        if normalize_role(current_user.role) == "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.FORBIDDEN,
                message="当事人账号不支持登录 Web 工作台。",
                detail="当事人账号不支持登录 Web 工作台。",
            )

        ticket_record = self._get_web_login_ticket_or_404(ticket=ticket)
        if ticket_record.status == "consumed":
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="该扫码票据已完成登录。",
                detail="该扫码票据已完成登录。",
            )
        if ticket_record.status == "expired":
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.AUTH_REQUIRED,
                message="该扫码票据已过期，请返回电脑端刷新二维码。",
                detail="该扫码票据已过期，请返回电脑端刷新二维码。",
            )
        if ticket_record.status == "confirmed" and ticket_record.user_id not in {None, current_user.id}:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="该扫码票据已被其他账号确认。",
                detail="该扫码票据已被其他账号确认。",
            )

        now = datetime.now(timezone.utc)
        ticket_record.status = "confirmed"
        ticket_record.confirmed_at = now
        ticket_record.user_id = current_user.id
        ticket_record.tenant_id = current_user.tenant_id
        self.repository.save_commit_refresh(ticket_record)

        payload = self._build_web_login_status_payload(ticket_record)
        payload.user = current_user
        return payload

    def exchange_ticket(self, *, ticket: str, request: Request) -> Token:
        ticket_record = self._get_web_login_ticket_or_404(ticket=ticket)
        if ticket_record.status != "confirmed" or ticket_record.user_id is None:
            raise AppError(
                status_code=status.HTTP_409_CONFLICT,
                code=ErrorCode.CONFLICT,
                message="该扫码票据尚未在微信端确认。",
                detail="该扫码票据尚未在微信端确认。",
            )

        user = self.repository.get_user_by_id(user_id=ticket_record.user_id)
        if user is None or not is_active_user_status(user.status):
            raise self.auth_required("扫码确认用户不可用，请重新扫码。")

        token = self.issue_token_pair(
            user=user,
            request=request,
            channel="web_wechat_scan",
        )
        ticket_record.status = "consumed"
        ticket_record.consumed_at = datetime.now(timezone.utc)
        self.repository.save_and_commit(ticket_record)
        return token
