from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.core.wechat_identity import wechat_identifier_hash_candidates
from app.integrations.wechat.service import WechatMiniIdentity
from app.models.user import User
from app.modules.auth.repository import AuthRepository


class WechatIdentityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = AuthRepository(db)

    def find_user_by_wechat_identity(self, *, identity: WechatMiniIdentity) -> User | None:
        if identity.unionid:
            unionid_hashes = wechat_identifier_hash_candidates(identity.unionid, kind="unionid")
            user = self.repository.get_user_by_wechat_unionid_hashes(
                unionid_hashes=unionid_hashes,
            )
            if user is not None:
                return user
        openid_hashes = wechat_identifier_hash_candidates(identity.openid, kind="openid")
        return self.repository.get_user_by_wechat_openid_hashes(openid_hashes=openid_hashes)

    def ensure_wechat_identity_available(self, *, identity: WechatMiniIdentity, user: User) -> None:
        existing_user = self.find_user_by_wechat_identity(identity=identity)
        if existing_user is None or existing_user.id == user.id:
            return
        raise AppError(
            status_code=status.HTTP_409_CONFLICT,
            code=ErrorCode.CONFLICT,
            message="当前微信已绑定其他账号，请先退出后使用原账号登录。",
            detail="当前微信已绑定其他账号，请先退出后使用原账号登录。",
        )

    @staticmethod
    def bind_wechat_identity(user: User, *, identity: WechatMiniIdentity, phone: str) -> None:
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
