from __future__ import annotations

import base64
import hashlib
import hmac

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _normalize_identifier(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _normalize_secret(value: str | None, *, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be configured")
    return normalized


def _encrypt_secret() -> str:
    return _normalize_secret(
        settings.WECHAT_IDENTITY_ENCRYPTION_SECRET,
        field_name="WECHAT_IDENTITY_ENCRYPTION_SECRET",
    )


def _hash_secret() -> str:
    return _normalize_secret(
        settings.WECHAT_IDENTITY_HASH_SECRET,
        field_name="WECHAT_IDENTITY_HASH_SECRET",
    )


def _legacy_secret(*, current_secret: str) -> str | None:
    legacy_secret = (settings.SECRET_KEY or "").strip()
    if not legacy_secret or legacy_secret == current_secret:
        return None
    return legacy_secret


def _derive_fernet(kind: str, *, secret: str) -> Fernet:
    key_material = hashlib.sha256(f"wechat:{kind}:{secret}".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def encrypt_wechat_identifier(value: str, *, kind: str) -> str:
    normalized = _normalize_identifier(value)
    if normalized is None:
        raise ValueError("wechat identifier cannot be empty")
    return _derive_fernet(kind, secret=_encrypt_secret()).encrypt(normalized.encode("utf-8")).decode("utf-8")


def decrypt_wechat_identifier(value: str | None, *, kind: str) -> str | None:
    normalized = _normalize_identifier(value)
    if normalized is None:
        return None
    current_secret = _encrypt_secret()
    try:
        return _derive_fernet(kind, secret=current_secret).decrypt(normalized.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        legacy_secret = _legacy_secret(current_secret=current_secret)
        if legacy_secret is not None:
            try:
                return _derive_fernet(kind, secret=legacy_secret).decrypt(normalized.encode("utf-8")).decode("utf-8")
            except InvalidToken:
                pass
    raise ValueError(f"invalid encrypted wechat {kind}")


def _hash_wechat_identifier_with_secret(value: str, *, kind: str, secret: str) -> str:
    return hmac.new(
        key=f"wechat:{kind}:{secret}".encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def wechat_identifier_hash_candidates(value: str | None, *, kind: str) -> list[str]:
    normalized = _normalize_identifier(value)
    if normalized is None:
        return []
    current_secret = _hash_secret()
    candidates = [
        _hash_wechat_identifier_with_secret(normalized, kind=kind, secret=current_secret),
    ]
    legacy_secret = _legacy_secret(current_secret=current_secret)
    if legacy_secret is not None:
        legacy_hash = _hash_wechat_identifier_with_secret(normalized, kind=kind, secret=legacy_secret)
        if legacy_hash not in candidates:
            candidates.append(legacy_hash)
    return candidates


def hash_wechat_identifier(value: str | None, *, kind: str) -> str | None:
    normalized = _normalize_identifier(value)
    if normalized is None:
        return None
    return _hash_wechat_identifier_with_secret(normalized, kind=kind, secret=_hash_secret())
