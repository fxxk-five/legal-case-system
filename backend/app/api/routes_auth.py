from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.core.security import REFRESH_TOKEN_TYPE, create_access_token, create_refresh_token, hash_token
from app.core.statuses import TenantStatus, UserStatus, is_active_user_status
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_mini_program_source
from app.models.auth_session import AuthSession
from app.models.case import Case
from app.models.invite import Invite
from app.models.tenant import Tenant
from app.models.user import User
from app.models.web_login_ticket import WebLoginTicket
from app.schemas.auth import (
    LogoutRequest,
    PhoneRegisterRequest,
    SmsCodeLoginRequest,
    SmsSendRequest,
    SmsSendResponse,
    SmsVerifyRequest,
    SmsVerifyResponse,
    Token,
    TokenRefreshRequest,
    UserLogin,
    UserRead,
    UserRegister,
    WebWechatLoginTicketCreateRead,
    WebWechatLoginTicketStatusRead,
    WechatMiniBindExisting,
    WechatMiniBind,
    WechatMiniLogin,
    WechatMiniPhoneLogin,
    WechatMiniLoginResult,
)
from app.schemas.invite import InviteRegister
from app.services.auth import authenticate_user, create_user, generate_system_password, resolve_tenant_for_registration
from app.services.invite import get_valid_invite
from app.services.mini_program import (
    WechatMiniIdentity,
    create_wechat_login_ticket,
    generate_mini_program_code,
    decode_case_invite_token,
    decode_wechat_login_ticket,
    exchange_code_for_identity,
    exchange_phone_code_for_phone_number,
)
from app.services.sms import (
    SMS_EXPIRE_SECONDS,
    SMS_SEND_INTERVAL_SECONDS,
    SMS_VERIFY_TOKEN_EXPIRE_SECONDS,
    assert_phone_verified,
    send_sms_code,
    verify_sms_code,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

WEB_WECHAT_LOGIN_TICKET_EXPIRE_MINUTES = 5
WEB_WECHAT_LOGIN_SCENE_PREFIX = "web-login:"
LAWYER_INVITE_SCENE = "lawyer-invite"


def _web_login_scene(ticket: str) -> str:
    return f"{WEB_WECHAT_LOGIN_SCENE_PREFIX}{ticket}"


def _web_login_launch_path(ticket: str) -> str:
    return f"{settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE}?scene=web-login&ticket={ticket}"


def _build_web_login_status_payload(ticket_record: WebLoginTicket) -> WebWechatLoginTicketStatusRead:
    now = datetime.now(timezone.utc)
    expires_at = _as_utc(ticket_record.expires_at) or now
    expires_in_seconds = max(0, int((expires_at - now).total_seconds()))
    return WebWechatLoginTicketStatusRead(
        ticket=ticket_record.ticket,
        status=ticket_record.status,
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds,
        confirmed_at=_as_utc(ticket_record.confirmed_at),
        consumed_at=_as_utc(ticket_record.consumed_at),
        can_exchange=ticket_record.status == "confirmed" and expires_in_seconds > 0,
    )


def _expire_web_login_ticket_if_needed(db: Session, ticket_record: WebLoginTicket) -> WebLoginTicket:
    if ticket_record.status in {"consumed", "expired"}:
        return ticket_record

    expires_at = _as_utc(ticket_record.expires_at)
    if expires_at is not None and expires_at <= datetime.now(timezone.utc):
        ticket_record.status = "expired"
        db.add(ticket_record)
        db.commit()
        db.refresh(ticket_record)
    return ticket_record


def _get_web_login_ticket_or_404(db: Session, *, ticket: str) -> WebLoginTicket:
    ticket_record = db.query(WebLoginTicket).filter(WebLoginTicket.ticket == ticket).first()
    if ticket_record is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Web 微信扫码登录票据不存在。",
            detail="Web 微信扫码登录票据不存在。",
        )
    return _expire_web_login_ticket_if_needed(db, ticket_record)


def _resolve_lawyer_invite(db: Session, *, token: str) -> Invite:
    invite = get_valid_invite(db, token=token)
    if normalize_role(invite.role) != "lawyer":
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_INVALID,
            message="当前邀请仅支持机构律师加入。",
            detail="当前邀请仅支持机构律师加入。",
        )
    return invite


def _token_extra_data(user: User) -> dict:
    return {
        "tenant_id": user.tenant_id,
        "role": user.role,
        "is_tenant_admin": user.is_tenant_admin,
    }


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _auth_required(message: str = "登录状态无效，请重新登录。") -> AppError:
    return AppError(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code=ErrorCode.AUTH_REQUIRED,
        message=message,
        detail=message,
    )


def _is_mini_program_request(request: Request | None) -> bool:
    if request is None:
        return False
    platform = (request.headers.get("X-Client-Platform") or "").strip().lower()
    source = (request.headers.get("X-Client-Source") or "").strip().lower()
    return platform == "mini-program" or source in {"wx-mini", "mini-program"}


def _resolve_login_channel(request: Request | None, *, prefer_wechat: bool = False) -> str:
    if prefer_wechat:
        return "mini_wechat"
    if _is_mini_program_request(request):
        return "mini_password"
    return "web_password"


def _resolve_device_type(request: Request | None) -> str:
    return "mini-program" if _is_mini_program_request(request) else "web"


def _issue_token_pair(
    db: Session,
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
            device_type=_resolve_device_type(request),
            client_ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
        db.add(auth_session)
        db.flush()
    else:
        auth_session = (
            db.query(AuthSession)
            .filter(AuthSession.id == session_id, AuthSession.user_id == user.id, AuthSession.tenant_id == user.tenant_id)
            .first()
        )
        if auth_session is None:
            raise _auth_required()
        if auth_session.is_revoked:
            raise _auth_required("登录会话已失效，请重新登录。")
        auth_session.expires_at = expires_at
        auth_session.last_used_at = now
        auth_session.channel = channel or auth_session.channel
        auth_session.device_type = _resolve_device_type(request)
        auth_session.client_ip = request.client.host if request and request.client else auth_session.client_ip
        auth_session.user_agent = request.headers.get("user-agent") if request else auth_session.user_agent

    if touch_login_audit:
        user.previous_login_at = user.last_login_at
        user.last_login_at = now
        user.last_login_channel = channel
        db.add(user)
        db.flush()

    token_extra = {**_token_extra_data(user), "sid": auth_session.id}
    access_token = create_access_token(user.id, extra_data=token_extra)
    refresh_token = create_refresh_token(user.id, session_id=auth_session.id, extra_data=_token_extra_data(user))

    auth_session.refresh_token_hash = hash_token(refresh_token)
    auth_session.expires_at = expires_at
    auth_session.last_used_at = now
    auth_session.is_revoked = False
    auth_session.revoked_at = None
    db.add(auth_session)
    db.commit()
    db.refresh(user)

    return Token(access_token=access_token, refresh_token=refresh_token)


def _get_valid_refresh_session(db: Session, *, payload: dict, refresh_token: str, user: User) -> AuthSession:
    sid = payload.get("sid")
    if not isinstance(sid, (int, float, str)) or not str(sid).isdigit():
        raise _auth_required()
    auth_session = (
        db.query(AuthSession)
        .filter(AuthSession.id == int(sid), AuthSession.user_id == user.id, AuthSession.tenant_id == user.tenant_id)
        .first()
    )
    if auth_session is None:
        raise _auth_required()
    if auth_session.is_revoked:
        raise _auth_required("登录会话已失效，请重新登录。")
    if auth_session.refresh_token_hash != hash_token(refresh_token):
        raise _auth_required("登录会话已失效，请重新登录。")
    expires_at = _as_utc(auth_session.expires_at)
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        raise _auth_required("登录会话已过期，请重新登录。")
    return auth_session


def _find_user_by_wechat_identity(db: Session, *, identity: WechatMiniIdentity) -> User | None:
    if identity.unionid:
        user = db.query(User).filter(User.wechat_unionid == identity.unionid).first()
        if user is not None:
            return user
    return db.query(User).filter(User.wechat_openid == identity.openid).first()


def _ensure_user_can_login(user: User) -> None:
    if is_active_user_status(user.status):
        return
    raise AppError(
        status_code=status.HTTP_403_FORBIDDEN,
        code=ErrorCode.USER_NOT_ACTIVE,
        message="当前账号未激活，请联系管理员。",
        detail="当前账号未激活，请联系管理员。",
    )


def _resolve_tenant_by_code(db: Session, tenant_code: str) -> Tenant:
    tenant = (
        db.query(Tenant)
        .filter(Tenant.tenant_code == tenant_code, Tenant.status == int(TenantStatus.ACTIVE))
        .first()
    )
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="目标租户不存在或已停用。",
            detail="目标租户不存在或已停用。",
        )
    return tenant


def _resolve_login_tenant(db: Session, *, tenant_code: str | None) -> Tenant | None:
    normalized_code = (tenant_code or "").strip()
    if not normalized_code:
        return None
    return _resolve_tenant_by_code(db, normalized_code)


def _resolve_sms_login_user(db: Session, *, phone: str, tenant_code: str | None) -> User:
    tenant = _resolve_login_tenant(db, tenant_code=tenant_code)
    base_query = db.query(User).filter(User.phone == phone)
    if tenant is not None:
        user = base_query.filter(User.tenant_id == tenant.id).order_by(User.created_at.asc()).first()
        if user is None:
            raise AppError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code=ErrorCode.AUTH_REQUIRED,
                message="手机号或验证码错误。",
                detail="手机号或验证码错误。",
            )
        return user

    matched_users = base_query.order_by(User.created_at.asc()).all()
    if not matched_users:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="手机号或验证码错误。",
            detail="手机号或验证码错误。",
        )

    tenant_ids = sorted({user.tenant_id for user in matched_users})
    if len(tenant_ids) > 1:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
            detail="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
        )

    return matched_users[0]


def _resolve_wechat_tenant_context(
    db: Session,
    *,
    phone: str,
    tenant_code: str | None,
    case_invite_token: str | None,
) -> tuple[Tenant, dict | None]:
    invite_payload = None
    if case_invite_token:
        invite_payload = decode_case_invite_token(case_invite_token)
        tenant = db.query(Tenant).filter(Tenant.id == int(invite_payload["tenant_id"])).first()
        if tenant is None or int(tenant.status) != int(TenantStatus.ACTIVE):
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="目标租户不存在或已停用。",
                detail="目标租户不存在或已停用。",
            )
        return tenant, invite_payload

    if tenant_code:
        return _resolve_tenant_by_code(db, tenant_code), None

    matched_users = db.query(User).filter(User.phone == phone).order_by(User.created_at.asc()).all()
    tenant_ids = sorted({user.tenant_id for user in matched_users})
    if len(tenant_ids) > 1:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="该手机号匹配多个租户，请先指定 tenant_code 或使用案件邀请继续登录。",
            detail="该手机号匹配多个租户，请先指定 tenant_code 或使用案件邀请继续登录。",
        )

    raise AppError(
        status_code=status.HTTP_400_BAD_REQUEST,
        code=ErrorCode.VALIDATION_ERROR,
        message="请提供 tenant_code 或案件邀请后再继续微信登录。",
        detail="请提供 tenant_code 或案件邀请后再继续微信登录。",
    )


def _has_wechat_invite_context(*, case_invite_token: str | None, lawyer_invite_token: str | None) -> bool:
    return bool((case_invite_token or "").strip() or (lawyer_invite_token or "").strip())


def _bind_wechat_identity(user: User, *, identity: WechatMiniIdentity, phone: str) -> None:
    if user.wechat_openid and user.wechat_openid != identity.openid:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="当前账号已绑定其他微信，请先联系管理员处理。",
            detail="当前账号已绑定其他微信，请先联系管理员处理。",
        )
    if identity.unionid and user.wechat_unionid and user.wechat_unionid != identity.unionid:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="当前账号已绑定其他微信，请先联系管理员处理。",
            detail="当前账号已绑定其他微信，请先联系管理员处理。",
        )
    user.wechat_openid = identity.openid
    if identity.unionid:
        user.wechat_unionid = identity.unionid
    user.wechat_phone_snapshot = phone
    user.wechat_bound_at = datetime.now(timezone.utc)


def _ensure_wechat_identity_available(db: Session, *, identity: WechatMiniIdentity, user: User) -> None:
    existing_user = _find_user_by_wechat_identity(db, identity=identity)
    if existing_user is None or existing_user.id == user.id:
        return
    raise AppError(
        status_code=status.HTTP_409_CONFLICT,
        code=ErrorCode.CONFLICT,
        message="当前微信已绑定其他账号，请先退出后使用原账号登录。",
        detail="当前微信已绑定其他账号，请先退出后使用原账号登录。",
    )


def _build_wechat_login_result(
    *,
    identity: WechatMiniIdentity,
    tokens: Token | None = None,
    user: User | None = None,
    need_bind_phone: bool,
    wx_session_ticket: str | None = None,
) -> WechatMiniLoginResult:
    return WechatMiniLoginResult(
        access_token=tokens.access_token if tokens else None,
        refresh_token=tokens.refresh_token if tokens else None,
        wechat_openid=identity.openid,
        need_bind_phone=need_bind_phone,
        login_state="NEED_PHONE_AUTH" if need_bind_phone else "LOGGED_IN",
        wx_session_ticket=wx_session_ticket,
        user=user,
    )


def _build_pending_approval_result(
    *,
    identity: WechatMiniIdentity,
    user: User,
) -> WechatMiniLoginResult:
    return WechatMiniLoginResult(
        access_token=None,
        refresh_token=None,
        wechat_openid=identity.openid,
        need_bind_phone=False,
        login_state="PENDING_APPROVAL",
        wx_session_ticket=None,
        user=user,
    )


@router.post("/web-wechat-login", response_model=WebWechatLoginTicketCreateRead, status_code=status.HTTP_201_CREATED)
def create_web_wechat_login_ticket(request: Request, db: Session = Depends(get_db)) -> WebWechatLoginTicketCreateRead:
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
    db.add(ticket_record)
    db.commit()
    db.refresh(ticket_record)

    base_path = f"{settings.API_V1_STR}/auth/web-wechat-login/{quote(ticket_record.ticket)}"
    return WebWechatLoginTicketCreateRead(
        ticket=ticket_record.ticket,
        status=ticket_record.status,
        expires_at=expires_at,
        expires_in_seconds=int((expires_at - now).total_seconds()),
        mini_program_page=settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE,
        mini_program_scene=_web_login_scene(ticket_record.ticket),
        launch_path=_web_login_launch_path(ticket_record.ticket),
        qr_code_url=f"{base_path}/mini-code",
        poll_url=base_path,
    )


@router.get("/web-wechat-login/{ticket}", response_model=WebWechatLoginTicketStatusRead)
def get_web_wechat_login_ticket_status(ticket: str, db: Session = Depends(get_db)) -> WebWechatLoginTicketStatusRead:
    ticket_record = _get_web_login_ticket_or_404(db, ticket=ticket)
    return _build_web_login_status_payload(ticket_record)


@router.get("/web-wechat-login/{ticket}/mini-code", response_model=None)
def get_web_wechat_login_ticket_mini_code(ticket: str, db: Session = Depends(get_db)) -> FastAPIResponse:
    ticket_record = _get_web_login_ticket_or_404(db, ticket=ticket)
    content, content_type = generate_mini_program_code(
        page=settings.WECHAT_MINIAPP_CLIENT_ENTRY_PAGE,
        scene=_web_login_scene(ticket_record.ticket),
    )
    return FastAPIResponse(content=content, media_type=content_type)


@router.post("/web-wechat-login/{ticket}/confirm", response_model=WebWechatLoginTicketStatusRead)
def confirm_web_wechat_login_ticket(
    ticket: str,
    _: None = Depends(require_mini_program_source),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebWechatLoginTicketStatusRead:
    if normalize_role(current_user.role) == "client":
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.FORBIDDEN,
            message="当事人账号不支持登录 Web 工作台。",
            detail="当事人账号不支持登录 Web 工作台。",
        )

    ticket_record = _get_web_login_ticket_or_404(db, ticket=ticket)
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
    db.add(ticket_record)
    db.commit()
    db.refresh(ticket_record)

    payload = _build_web_login_status_payload(ticket_record)
    payload.user = current_user
    return payload


@router.post("/web-wechat-login/{ticket}/exchange", response_model=Token)
def exchange_web_wechat_login_ticket(
    ticket: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    ticket_record = _get_web_login_ticket_or_404(db, ticket=ticket)
    if ticket_record.status != "confirmed" or ticket_record.user_id is None:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="该扫码票据尚未在微信端确认。",
            detail="该扫码票据尚未在微信端确认。",
        )

    user = db.query(User).filter(User.id == ticket_record.user_id).first()
    if user is None or not is_active_user_status(user.status):
        raise _auth_required("扫码确认用户不可用，请重新扫码。")

    token = _issue_token_pair(
        db,
        user=user,
        request=request,
        channel="web_wechat_scan",
    )

    ticket_record.status = "consumed"
    ticket_record.consumed_at = datetime.now(timezone.utc)
    db.add(ticket_record)
    db.commit()
    return token


@router.post("/sms/send", response_model=SmsSendResponse)
def send_phone_sms(sms_in: SmsSendRequest, db: Session = Depends(get_db)) -> SmsSendResponse:
    sms = send_sms_code(db, phone=sms_in.phone, purpose=sms_in.purpose)
    return SmsSendResponse(
        phone=sms.phone,
        expires_in_seconds=SMS_EXPIRE_SECONDS,
        retry_after_seconds=SMS_SEND_INTERVAL_SECONDS,
        request_id=sms.request_id,
    )


@router.post("/sms/verify", response_model=SmsVerifyResponse)
def verify_phone_sms(sms_in: SmsVerifyRequest, db: Session = Depends(get_db)) -> SmsVerifyResponse:
    token = verify_sms_code(db, phone=sms_in.phone, code=sms_in.code, purpose=sms_in.purpose)
    return SmsVerifyResponse(
        phone=sms_in.phone,
        verification_token=token,
        expires_in_seconds=SMS_VERIFY_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/sms-login", response_model=Token)
def login_by_sms_code(sms_in: SmsCodeLoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    user = _resolve_sms_login_user(
        db,
        phone=sms_in.phone,
        tenant_code=sms_in.tenant_code,
    )
    if not is_active_user_status(user.status):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.USER_NOT_ACTIVE,
            message="账号待审批或已禁用。",
            detail="账号待审批或已禁用。",
        )

    verify_sms_code(db, phone=sms_in.phone, code=sms_in.code, purpose="login")
    return _issue_token_pair(
        db,
        user=user,
        request=request,
        channel="web_sms",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: PhoneRegisterRequest, db: Session = Depends(get_db)) -> User:
    assert_phone_verified(
        db,
        phone=user_in.phone,
        purpose="register",
        verification_token=user_in.phone_verification_token,
    )

    tenant = resolve_tenant_for_registration(db, tenant_code=user_in.tenant_code)
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="无法确定注册目标租户，请传入 tenant_code 或先创建租户。",
            detail="无法确定注册目标租户，请传入 tenant_code 或先创建租户。",
        )
    if tenant.type == "organization":
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_REQUIRED,
            message="机构律师必须通过邀请链接注册。",
            detail="机构律师必须通过邀请链接注册。",
        )

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.phone == user_in.phone)
        .first()
    )
    if existing_user:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已注册。",
            detail="该手机号已注册。",
        )

    return create_user(
        db,
        user_in=UserRegister(
            phone=user_in.phone,
            password=user_in.password,
            real_name=user_in.real_name,
            tenant_code=user_in.tenant_code,
        ),
        tenant_id=tenant.id,
    )


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    tenant = _resolve_login_tenant(db, tenant_code=user_in.tenant_code)
    tenant_id = tenant.id if tenant is not None else None

    try:
        user = authenticate_user(
            db,
            phone=user_in.phone,
            password=user_in.password,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.VALIDATION_ERROR,
            message="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
            detail="该手机号存在于多个租户，请填写 tenant_code 后再登录。",
        ) from exc
    if user is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="手机号或密码错误。",
            detail="手机号或密码错误。",
        )
    if not is_active_user_status(user.status):
        raise AppError(
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.USER_NOT_ACTIVE,
            message="账号待审批或已禁用。",
            detail="账号待审批或已禁用。",
        )

    return _issue_token_pair(
        db,
        user=user,
        request=request,
        channel=_resolve_login_channel(request),
    )


@router.post("/refresh", response_model=Token)
def refresh_token(payload: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    try:
        token_payload = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="刷新令牌无效或已过期。",
            detail="刷新令牌无效或已过期。",
        ) from exc

    if token_payload.get("token_type") != REFRESH_TOKEN_TYPE:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="刷新令牌无效或已过期。",
            detail="刷新令牌无效或已过期。",
        )

    subject = token_payload.get("sub")
    if subject is None:
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="刷新令牌无效或已过期。",
            detail="刷新令牌无效或已过期。",
        )

    user = db.query(User).filter(User.id == int(subject)).first()
    if user is None or not is_active_user_status(user.status):
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="用户不存在或已失效，请重新登录。",
            detail="用户不存在或已失效，请重新登录。",
        )

    token_tenant_id = token_payload.get("tenant_id")
    if token_tenant_id is not None and user.tenant_id != int(token_tenant_id):
        raise AppError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.AUTH_REQUIRED,
            message="租户鉴权失败，请重新登录。",
            detail="租户鉴权失败，请重新登录。",
        )

    auth_session = _get_valid_refresh_session(
        db,
        payload=token_payload,
        refresh_token=payload.refresh_token,
        user=user,
    )
    return _issue_token_pair(
        db,
        user=user,
        request=request,
        channel=auth_session.channel or _resolve_login_channel(request),
        session_id=auth_session.id,
        touch_login_audit=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    refresh_token_value = (payload.refresh_token if payload else "") or ""
    if refresh_token_value:
        try:
            token_payload = jwt.decode(refresh_token_value, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            token_payload = None
        if token_payload and token_payload.get("token_type") == REFRESH_TOKEN_TYPE:
            sid = token_payload.get("sid")
            if isinstance(sid, (int, float, str)) and str(sid).isdigit():
                auth_session = (
                    db.query(AuthSession)
                    .filter(
                        AuthSession.id == int(sid),
                        AuthSession.user_id == current_user.id,
                        AuthSession.tenant_id == current_user.tenant_id,
                    )
                    .first()
                )
                if auth_session is not None and auth_session.refresh_token_hash == hash_token(refresh_token_value):
                    auth_session.is_revoked = True
                    auth_session.revoked_at = datetime.now(timezone.utc)
                    auth_session.last_used_at = datetime.now(timezone.utc)
                    db.add(auth_session)
                    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/wx-mini-login", response_model=WechatMiniLoginResult)
def wx_mini_login(login_in: WechatMiniLogin, request: Request, db: Session = Depends(get_db)) -> WechatMiniLoginResult:
    identity = exchange_code_for_identity(login_in.code)
    user = _find_user_by_wechat_identity(db, identity=identity)
    invite_mode = _has_wechat_invite_context(
        case_invite_token=login_in.case_invite_token,
        lawyer_invite_token=login_in.lawyer_invite_token,
    )
    if user is None or invite_mode:
        return _build_wechat_login_result(
            identity=identity,
            need_bind_phone=True,
            wx_session_ticket=create_wechat_login_ticket(identity),
        )

    _ensure_user_can_login(user)
    tokens = _issue_token_pair(
        db,
        user=user,
        request=request,
        channel=_resolve_login_channel(request, prefer_wechat=True),
    )
    return _build_wechat_login_result(
        identity=identity,
        tokens=tokens,
        user=user,
        need_bind_phone=False,
    )


@router.post("/wx-mini-phone-login", response_model=WechatMiniLoginResult)
def wx_mini_phone_login(
    login_in: WechatMiniPhoneLogin,
    request: Request,
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    identity = decode_wechat_login_ticket(login_in.wx_session_ticket)
    lawyer_invite = _resolve_lawyer_invite(db, token=login_in.lawyer_invite_token) if login_in.lawyer_invite_token else None
    invite_mode = _has_wechat_invite_context(
        case_invite_token=login_in.case_invite_token,
        lawyer_invite_token=login_in.lawyer_invite_token,
    )
    bound_user = _find_user_by_wechat_identity(db, identity=identity)
    if bound_user is not None and not invite_mode:
        _ensure_user_can_login(bound_user)
        tokens = _issue_token_pair(
            db,
            user=bound_user,
            request=request,
            channel=_resolve_login_channel(request, prefer_wechat=True),
        )
        return _build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=bound_user,
            need_bind_phone=False,
        )

    phone = exchange_phone_code_for_phone_number(login_in.phone_code)
    invite_payload = None
    if lawyer_invite is not None:
        tenant = db.query(Tenant).filter(Tenant.id == lawyer_invite.tenant_id).first()
        if tenant is None or int(tenant.status) != int(TenantStatus.ACTIVE):
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.TENANT_NOT_FOUND,
                message="目标机构不存在或已停用。",
                detail="目标机构不存在或已停用。",
            )
    else:
        tenant, invite_payload = _resolve_wechat_tenant_context(
            db,
            phone=phone,
            tenant_code=login_in.tenant_code,
            case_invite_token=login_in.case_invite_token,
        )

    user = db.query(User).filter(User.tenant_id == tenant.id, User.phone == phone).first()
    if user is None:
        if lawyer_invite is None and invite_payload is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.INVITE_REQUIRED,
                message="当前手机号尚未开通账号，请使用案件邀请或机构邀请进入。",
                detail="当前手机号尚未开通账号，请使用案件邀请或机构邀请进入。",
            )

        if lawyer_invite is not None:
            user = create_user(
                db,
                user_in=UserRegister(
                    phone=phone,
                    password=generate_system_password(),
                    real_name=(login_in.real_name or f"律师{phone[-4:]}").strip(),
                ),
                tenant_id=tenant.id,
                role=lawyer_invite.role,
                status=int(UserStatus.PENDING_APPROVAL),
            )
        else:
            user = create_user(
                db,
                user_in=UserRegister(
                    phone=phone,
                    password=generate_system_password(),
                    real_name=(login_in.real_name or f"当事人{phone[-4:]}").strip(),
                ),
                tenant_id=tenant.id,
                role="client",
                status=int(UserStatus.ACTIVE),
            )

    _ensure_wechat_identity_available(db, identity=identity, user=user)
    _bind_wechat_identity(user, identity=identity, phone=phone)
    db.add(user)

    if lawyer_invite is not None and lawyer_invite.status == "pending":
        lawyer_invite.status = "used"
        db.add(lawyer_invite)

    if invite_payload is not None:
        case = (
            db.query(Case)
            .filter(Case.id == int(invite_payload["case_id"]), Case.tenant_id == tenant.id)
            .first()
        )
        if case is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.CASE_NOT_FOUND,
                message="案件不存在。",
                detail="案件不存在。",
            )
        case.client_id = user.id
        db.add(case)

    if int(user.status) == int(UserStatus.PENDING_APPROVAL):
        db.commit()
        db.refresh(user)
        return _build_pending_approval_result(identity=identity, user=user)

    _ensure_user_can_login(user)
    tokens = _issue_token_pair(
        db,
        user=user,
        request=request,
        channel=_resolve_login_channel(request, prefer_wechat=True),
    )
    return _build_wechat_login_result(
        identity=identity,
        tokens=tokens,
        user=user,
        need_bind_phone=False,
    )


@router.post("/wx-mini-bind-existing", response_model=WechatMiniLoginResult)
def wx_mini_bind_existing(
    bind_in: WechatMiniBindExisting,
    request: Request,
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    identity = decode_wechat_login_ticket(bind_in.wx_session_ticket)
    tenant = _resolve_tenant_by_code(db, bind_in.tenant_code) if bind_in.tenant_code else None
    tenant_id = tenant.id if tenant is not None else None

    try:
        authenticated_user = authenticate_user(
            db,
            phone=bind_in.phone,
            password=bind_in.password,
            tenant_id=tenant_id,
        )
    except ValueError as exc:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="该手机号匹配多个租户，请先指定 tenant_code。",
            detail="该手机号匹配多个租户，请先指定 tenant_code。",
        ) from exc

    if authenticated_user is None:
        raise _auth_required("手机号或密码错误，无法绑定微信。")

    _ensure_user_can_login(authenticated_user)
    _ensure_wechat_identity_available(db, identity=identity, user=authenticated_user)
    _bind_wechat_identity(authenticated_user, identity=identity, phone=bind_in.phone)
    db.add(authenticated_user)

    tokens = _issue_token_pair(
        db,
        user=authenticated_user,
        request=request,
        channel=_resolve_login_channel(request, prefer_wechat=True),
    )
    return _build_wechat_login_result(
        identity=identity,
        tokens=tokens,
        user=authenticated_user,
        need_bind_phone=False,
    )


@router.post("/wx-mini-bind", response_model=WechatMiniLoginResult)
def wx_mini_bind(bind_in: WechatMiniBind, request: Request, db: Session = Depends(get_db)) -> WechatMiniLoginResult:
    identity = WechatMiniIdentity(openid=bind_in.wechat_openid)
    existing_user = db.query(User).filter(User.tenant_id == bind_in.tenant_id, User.phone == bind_in.phone).first() if bind_in.tenant_id else None
    if existing_user is None and bind_in.tenant_code:
        tenant = _resolve_tenant_by_code(db, bind_in.tenant_code)
        existing_user = db.query(User).filter(User.tenant_id == tenant.id, User.phone == bind_in.phone).first()

    if existing_user is not None:
        _ensure_user_can_login(existing_user)
        if bind_in.password is None:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.VALIDATION_ERROR,
                message="绑定已有账号时必须输入密码。",
                detail="绑定已有账号时必须输入密码。",
            )
        authenticated_user = authenticate_user(
            db,
            phone=bind_in.phone,
            password=bind_in.password,
            tenant_id=existing_user.tenant_id,
        )
        if authenticated_user is None or authenticated_user.id != existing_user.id:
            raise _auth_required("手机号或密码错误，无法绑定微信。")
        _ensure_wechat_identity_available(db, identity=identity, user=existing_user)
        _bind_wechat_identity(existing_user, identity=identity, phone=bind_in.phone)
        if bind_in.real_name and not existing_user.real_name:
            existing_user.real_name = bind_in.real_name
        db.add(existing_user)
        tokens = _issue_token_pair(
            db,
            user=existing_user,
            request=request,
            channel=_resolve_login_channel(request, prefer_wechat=True),
        )
        return _build_wechat_login_result(
            identity=identity,
            tokens=tokens,
            user=existing_user,
            need_bind_phone=False,
        )

    if not bind_in.case_invite_token:
        raise AppError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.INVITE_REQUIRED,
            message="旧版绑定接口仅允许通过案件邀请创建当事人账号。",
            detail="旧版绑定接口仅允许通过案件邀请创建当事人账号。",
        )

    invite_payload = decode_case_invite_token(bind_in.case_invite_token)
    tenant = db.query(Tenant).filter(Tenant.id == int(invite_payload["tenant_id"])).first()
    if tenant is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.TENANT_NOT_FOUND,
            message="目标租户不存在。",
            detail="目标租户不存在。",
        )

    user = db.query(User).filter(User.tenant_id == tenant.id, User.phone == bind_in.phone).first()
    if user is None:
        user = create_user(
            db,
            user_in=UserRegister(
                phone=bind_in.phone,
                password=generate_system_password(),
                real_name=(bind_in.real_name or f"当事人{bind_in.phone[-4:]}").strip(),
            ),
            tenant_id=tenant.id,
            role="client",
            status=int(UserStatus.ACTIVE),
        )

    _ensure_user_can_login(user)
    _ensure_wechat_identity_available(db, identity=identity, user=user)
    _bind_wechat_identity(user, identity=identity, phone=bind_in.phone)
    if bind_in.real_name and not user.real_name:
        user.real_name = bind_in.real_name
    db.add(user)

    case = (
        db.query(Case)
        .filter(Case.id == int(invite_payload["case_id"]), Case.tenant_id == tenant.id)
        .first()
    )
    if case is None:
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.CASE_NOT_FOUND,
            message="案件不存在。",
            detail="案件不存在。",
        )
    case.client_id = user.id
    db.add(case)

    tokens = _issue_token_pair(
        db,
        user=user,
        request=request,
        channel=_resolve_login_channel(request, prefer_wechat=True),
    )
    return _build_wechat_login_result(
        identity=identity,
        tokens=tokens,
        user=user,
        need_bind_phone=False,
    )


@router.post("/invite-register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user_by_invite(invite_in: InviteRegister, db: Session = Depends(get_db)) -> User:
    invite = get_valid_invite(db, token=invite_in.token)

    assert_phone_verified(
        db,
        phone=invite_in.phone,
        purpose="register",
        verification_token=invite_in.phone_verification_token or "",
    )

    existing_user = (
        db.query(User)
        .filter(User.tenant_id == invite.tenant_id, User.phone == invite_in.phone)
        .first()
    )
    if existing_user:
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.USER_ALREADY_EXISTS,
            message="该手机号已存在于当前租户。",
            detail="该手机号已存在于当前租户。",
        )

    user = create_user(
        db,
        user_in=UserRegister(
            phone=invite_in.phone,
            password=invite_in.password,
            real_name=invite_in.real_name,
        ),
        tenant_id=invite.tenant_id,
        role=invite.role,
        status=int(UserStatus.PENDING_APPROVAL),
    )

    invite.status = "used"
    db.add(invite)
    db.commit()

    return user
