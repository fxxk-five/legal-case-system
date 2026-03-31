from io import BytesIO

import pytest
from starlette.datastructures import Headers, UploadFile

from app.core.errors import AppError
from app.integrations.wechat.token_service import (
    decode_case_invite_token_payload,
    decode_wechat_login_ticket_payload,
)
from app.modules.asr.router import _detect_audio_format


def test_wechat_login_ticket_error_message_is_readable():
    with pytest.raises(AppError) as exc_info:
      decode_wechat_login_ticket_payload(ticket="invalid-ticket", scene="wx_mini_login_ticket")

    assert exc_info.value.message == "微信登录凭证已失效，请重新发起登录。"
    assert exc_info.value.detail == "微信登录凭证已失效，请重新发起登录。"


def test_case_invite_token_error_message_is_readable():
    with pytest.raises(AppError) as exc_info:
      decode_case_invite_token_payload("invalid-token")

    assert exc_info.value.message == "案件邀请链接无效或已过期。"
    assert exc_info.value.detail == "案件邀请链接无效或已过期。"


def test_asr_format_validation_message_is_readable():
    upload = UploadFile(
        file=BytesIO(b"fake-audio"),
        filename="voice.unsupported",
        headers=Headers({"content-type": "application/octet-stream"}),
    )

    with pytest.raises(AppError) as exc_info:
      _detect_audio_format(upload)

    assert exc_info.value.message == "暂不支持该音频格式上传。"
    assert "支持的格式" in exc_info.value.detail
