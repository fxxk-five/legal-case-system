from __future__ import annotations

from fastapi import Response, status

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.integrations.report.service import ReportService
from app.models.user import User
from app.modules.cases.report_access_service import (
    build_case_report_access_url,
    render_case_report_response,
)
from app.modules.cases.helpers import get_case_or_404
from app.modules.cases.models.case import Case
from app.modules.cases.report_payload_service import build_case_report_payload
from app.modules.cases.repository import CasesRepository
from app.modules.cases.schemas import CaseReportAccessLinkRead, CaseReportVersionRead
from app.modules.cases.report_version_service import (
    CaseReportObject,
    build_case_report_versions,
    persist_generated_report,
    resolve_case_report_by_name,
    resolve_latest_case_report,
    resolve_report_scope,
)


class CaseReportService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = CasesRepository(db)

    def list_case_report_versions(self, *, case_id: int, current_user: User) -> list[CaseReportVersionRead]:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="无权查看该案件。",
                detail="无权查看该案件。",
            )
        return build_case_report_versions(case, viewer_role=current_user.role)

    def get_case_report_access_link(
        self,
        *,
        case_id: int,
        regenerate: bool,
        current_user: User,
    ) -> CaseReportAccessLinkRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        viewer_role = normalize_role(current_user.role)
        if viewer_role == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="Current user cannot access this case report.",
                detail="Current user cannot access this case report.",
            )

        report_scope = resolve_report_scope(current_user.role)
        latest_report = resolve_latest_case_report(case, report_scope=report_scope)
        if latest_report is None or regenerate:
            payload = build_case_report_payload(db=self.db, case=case, viewer=current_user)
            pdf_bytes = ReportService().generate_case_report_pdf(payload)
            latest_report = persist_generated_report(case=case, report_scope=report_scope, pdf_bytes=pdf_bytes)

        return CaseReportAccessLinkRead(
            file_name=latest_report.file_name,
            access_url=build_case_report_access_url(latest_report, case_id=case.id, latest=True),
            expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def get_case_report_version_access_link(
        self,
        *,
        case_id: int,
        report_name: str,
        current_user: User,
    ) -> CaseReportAccessLinkRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        viewer_role = normalize_role(current_user.role)
        if viewer_role == "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="Current user cannot access historical case reports.",
                detail="Current user cannot access historical case reports.",
            )

        report = resolve_case_report_by_name(case, report_name=report_name)
        if report is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.FILE_NOT_FOUND,
                message="Report file does not exist.",
                detail="Report file does not exist.",
            )

        return CaseReportAccessLinkRead(
            file_name=report.file_name,
            access_url=build_case_report_access_url(report, case_id=case.id, latest=False),
            expires_in_seconds=settings.FILE_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def download_case_report_version(
        self,
        *,
        case_id: int,
        report_name: str,
        current_user: User,
    ) -> Response:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        viewer_role = normalize_role(current_user.role)
        if viewer_role == "client":
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="当事人仅可下载最新报告。",
                detail="当事人仅可下载最新报告。",
            )
        report_path = resolve_case_report_by_name(case, report_name=report_name)
        if report_path is None:
            raise AppError(
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.FILE_NOT_FOUND,
                message="报告文件不存在。",
                detail="报告文件不存在。",
            )
        return render_case_report_response(report_path)

    def download_case_report(
        self,
        *,
        case_id: int,
        regenerate: bool,
        current_user: User,
    ) -> Response:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        viewer_role = normalize_role(current_user.role)
        if viewer_role == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="无权查看该案件。",
                detail="无权查看该案件。",
            )

        report_scope = resolve_report_scope(current_user.role)
        latest_report = resolve_latest_case_report(case, report_scope=report_scope)
        if latest_report is not None and not regenerate:
            return render_case_report_response(latest_report)

        report_service = ReportService()
        try:
            payload = build_case_report_payload(db=self.db, case=case, viewer=current_user)
            pdf_bytes = report_service.generate_case_report_pdf(payload)
            generated_path = persist_generated_report(case=case, report_scope=report_scope, pdf_bytes=pdf_bytes)
        except AppError:
            if latest_report is not None:
                return render_case_report_response(latest_report)
            raise

        return render_case_report_response(generated_path)
