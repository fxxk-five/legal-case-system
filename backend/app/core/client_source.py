from __future__ import annotations

from fastapi import Request


MINI_PROGRAM_PLATFORM = "mini-program"
MINI_PROGRAM_SOURCES = {"wx-mini", "mini-program"}
MINI_PROGRAM_SESSION_CHANNELS = {"mini_password", "mini_wechat"}


def is_mini_program_request(request: Request | None) -> bool:
    if request is None:
        return False
    platform = (request.headers.get("X-Client-Platform") or "").strip().lower()
    source = (request.headers.get("X-Client-Source") or "").strip().lower()
    return platform == MINI_PROGRAM_PLATFORM and source in MINI_PROGRAM_SOURCES


def is_mini_program_session(*, device_type: str | None = None, channel: str | None = None) -> bool:
    normalized_device_type = (device_type or "").strip().lower()
    normalized_channel = (channel or "").strip().lower()
    return normalized_device_type == MINI_PROGRAM_PLATFORM or normalized_channel in MINI_PROGRAM_SESSION_CHANNELS
