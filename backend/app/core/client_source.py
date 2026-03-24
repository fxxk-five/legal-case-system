from __future__ import annotations

from fastapi import Request


MINI_PROGRAM_PLATFORM = "mini-program"
MINI_PROGRAM_SOURCES = {"wx-mini", "mini-program"}


def is_mini_program_request(request: Request | None) -> bool:
    if request is None:
        return False
    platform = (request.headers.get("X-Client-Platform") or "").strip().lower()
    source = (request.headers.get("X-Client-Source") or "").strip().lower()
    return platform == MINI_PROGRAM_PLATFORM and source in MINI_PROGRAM_SOURCES
