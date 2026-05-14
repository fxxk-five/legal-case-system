from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.modules.auth.deps import (
    get_current_user,
    get_current_user_allow_pending,
    require_mini_program_session,
    require_mini_program_source,
)
from app.modules.auth.schemas import (
    LoginAdviceRequest,
    LoginAdviceResponse,
    LogoutRequest,
    PasswordChangeRequest,
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
    WebWechatLoginTicketCreateRead,
    WebWechatLoginTicketStatusRead,
    WechatMiniBind,
    WechatMiniBindExisting,
    WechatMiniLogin,
    WechatMiniLoginResult,
    WechatMiniPhoneLogin,
)
from app.modules.auth.service import AuthService
from app.modules.auth.web_wechat_service import WebWechatLoginService
from app.modules.auth.wechat_service import WechatAuthService
from app.modules.invites.schemas import InviteRegister


router = APIRouter(prefix="/auth", tags=["Auth"])


def _auth_service(db: Session) -> AuthService:
    return AuthService(db)


def _wechat_auth_service(db: Session) -> WechatAuthService:
    auth_service = _auth_service(db)
    return WechatAuthService(
        db=db,
        issue_token_pair=auth_service.session_service.issue_token_pair,
        resolve_login_channel=auth_service.resolve_login_channel,
        ensure_user_can_login=auth_service.ensure_user_can_login,
        resolve_tenant_by_code=auth_service.resolve_tenant_by_code,
    )


def _web_wechat_login_service(db: Session) -> WebWechatLoginService:
    auth_service = _auth_service(db)
    return WebWechatLoginService(
        db=db,
        issue_token_pair=auth_service.session_service.issue_token_pair,
        auth_required=auth_service.session_service.auth_required,
    )


@router.post("/web-wechat-login", response_model=WebWechatLoginTicketCreateRead, status_code=status.HTTP_201_CREATED)
def create_web_wechat_login_ticket(request: Request, db: Session = Depends(get_db)) -> WebWechatLoginTicketCreateRead:
    return _web_wechat_login_service(db).create_ticket(request=request)


@router.get("/web-wechat-login/{ticket}", response_model=WebWechatLoginTicketStatusRead)
def get_web_wechat_login_ticket_status(ticket: str, db: Session = Depends(get_db)) -> WebWechatLoginTicketStatusRead:
    return _web_wechat_login_service(db).get_ticket_status(ticket=ticket)


@router.get("/web-wechat-login/{ticket}/mini-code", response_model=None)
def get_web_wechat_login_ticket_mini_code(ticket: str, db: Session = Depends(get_db)) -> FastAPIResponse:
    return _web_wechat_login_service(db).get_ticket_mini_code(ticket=ticket)


@router.post("/web-wechat-login/{ticket}/confirm", response_model=WebWechatLoginTicketStatusRead)
def confirm_web_wechat_login_ticket(
    ticket: str,
    _: None = Depends(require_mini_program_session),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebWechatLoginTicketStatusRead:
    return _web_wechat_login_service(db).confirm_ticket(
        ticket=ticket,
        current_user=current_user,
    )


@router.post("/web-wechat-login/{ticket}/exchange", response_model=Token)
def exchange_web_wechat_login_ticket(
    ticket: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Token:
    return _web_wechat_login_service(db).exchange_ticket(
        ticket=ticket,
        request=request,
    )


@router.post("/sms/send", response_model=SmsSendResponse)
def send_phone_sms(request: Request, sms_in: SmsSendRequest, db: Session = Depends(get_db)) -> SmsSendResponse:
    return _auth_service(db).send_phone_sms(
        request=request,
        sms_in=sms_in,
    )


@router.post("/sms/verify", response_model=SmsVerifyResponse)
def verify_phone_sms(request: Request, sms_in: SmsVerifyRequest, db: Session = Depends(get_db)) -> SmsVerifyResponse:
    return _auth_service(db).verify_phone_sms(
        request=request,
        sms_in=sms_in,
    )


@router.post("/sms-login", response_model=Token)
def login_by_sms_code(sms_in: SmsCodeLoginRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    return _auth_service(db).login_by_sms_code(
        sms_in=sms_in,
        request=request,
    )


@router.post("/login-advice", response_model=LoginAdviceResponse)
def get_login_advice(advice_in: LoginAdviceRequest, db: Session = Depends(get_db)) -> LoginAdviceResponse:
    return _auth_service(db).get_login_advice(advice_in=advice_in)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(user_in: PhoneRegisterRequest, db: Session = Depends(get_db)) -> User:
    return _auth_service(db).register_user(user_in=user_in)


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, request: Request, db: Session = Depends(get_db)) -> Token:
    return _auth_service(db).login(
        user_in=user_in,
        request=request,
    )


@router.post("/refresh", response_model=Token)
def refresh_token(payload: TokenRefreshRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    return _auth_service(db).session_service.refresh_token(
        payload=payload,
        request=request,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest | None = None,
    current_user: User = Depends(get_current_user_allow_pending),
    db: Session = Depends(get_db),
) -> Response:
    return _auth_service(db).session_service.logout(
        payload=payload,
        current_user=current_user,
    )


@router.post("/password", response_model=UserRead)
def change_password(
    password_in: PasswordChangeRequest,
    current_user: User = Depends(get_current_user_allow_pending),
    db: Session = Depends(get_db),
) -> User:
    return _auth_service(db).change_password(
        current_user=current_user,
        password_in=password_in,
    )


@router.post("/wx-mini-login", response_model=WechatMiniLoginResult)
def wx_mini_login(
    login_in: WechatMiniLogin,
    request: Request,
    _: None = Depends(require_mini_program_source),
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    return _wechat_auth_service(db).wx_mini_login(
        login_in=login_in,
        request=request,
    )


@router.post("/wx-mini-phone-login", response_model=WechatMiniLoginResult)
def wx_mini_phone_login(
    login_in: WechatMiniPhoneLogin,
    request: Request,
    _: None = Depends(require_mini_program_source),
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    return _wechat_auth_service(db).wx_mini_phone_login(
        login_in=login_in,
        request=request,
    )


@router.post("/wx-mini-bind-existing", response_model=WechatMiniLoginResult)
def wx_mini_bind_existing(
    bind_in: WechatMiniBindExisting,
    request: Request,
    _: None = Depends(require_mini_program_source),
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    return _wechat_auth_service(db).wx_mini_bind_existing(
        bind_in=bind_in,
        request=request,
    )


@router.post("/wx-mini-bind", response_model=WechatMiniLoginResult)
def wx_mini_bind(
    bind_in: WechatMiniBind,
    request: Request,
    _: None = Depends(require_mini_program_source),
    db: Session = Depends(get_db),
) -> WechatMiniLoginResult:
    return _wechat_auth_service(db).wx_mini_bind(
        bind_in=bind_in,
        request=request,
    )


@router.post("/invite-register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user_by_invite(invite_in: InviteRegister, db: Session = Depends(get_db)) -> User:
    return _auth_service(db).register_user_from_invite(invite_in=invite_in)
