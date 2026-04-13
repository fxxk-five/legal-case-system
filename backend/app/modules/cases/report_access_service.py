from __future__ import annotations

from typing import Any
from urllib.parse import quote

from fastapi import Response, status
from fastapi.responses import FileResponse, RedirectResponse

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.integrations.storage.service import get_storage_backend

REPORT_CONTENT_TYPE = "application/pdf"


def render_case_report_response(report: Any) -> Response:
    backend = get_storage_backend()
    download_url = backend.build_private_download_url(
        storage_key=report.storage_key,
        file_name=report.file_name,
        content_type=REPORT_CONTENT_TYPE,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return RedirectResponse(url=download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    if not backend.object_exists(storage_key=report.storage_key):
        raise AppError(
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.FILE_NOT_FOUND,
            message="Report file does not exist.",
            detail="Report file does not exist.",
        )

    return FileResponse(
        path=backend.resolve_local_path(storage_key=report.storage_key),
        filename=report.file_name,
        media_type=REPORT_CONTENT_TYPE,
    )


def build_case_report_access_url(report: Any, *, case_id: int, latest: bool) -> str:
    backend = get_storage_backend()
    download_url = backend.build_private_download_url(
        storage_key=report.storage_key,
        file_name=report.file_name,
        content_type=REPORT_CONTENT_TYPE,
        expires_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    if download_url:
        return download_url
    if latest:
        return f"{settings.API_V1_STR}/cases/{case_id}/report"
    return f"{settings.API_V1_STR}/cases/{case_id}/reports/{quote(report.file_name)}"
