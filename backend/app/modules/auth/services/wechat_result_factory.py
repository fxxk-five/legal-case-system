from __future__ import annotations

from app.integrations.wechat.service import WechatMiniIdentity
from app.models.user import User
from app.modules.auth.schemas import Token, WechatMiniLoginResult


class WechatResultFactory:
    @staticmethod
    def build_wechat_login_result(
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

    @staticmethod
    def build_pending_approval_result(
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
