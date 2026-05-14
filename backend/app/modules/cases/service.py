from __future__ import annotations

import logging

from fastapi import Request, Response, status

from app.api.pagination import resolve_pagination_params
from app.core.errors import AppError, ErrorCode
from app.core.roles import normalize_role
from app.models.user import User
from app.modules.cases.command_service import CaseCommandService
from app.modules.cases.helpers import get_case_or_404, serialize_case_for_viewer
from app.modules.cases.models.case import Case
from app.modules.cases.remark_service import CaseRemarkService
from app.modules.cases.report_service import CaseReportService
from app.modules.cases.repository import CasesRepository
from app.modules.cases.schemas import (
    CaseClientRemarkUpdate,
    CaseCreate,
    CaseInviteRead,
    CaseLawyerRead,
    CaseLawyerRemarkUpdate,
    CaseRead,
    CaseReportAccessLinkRead,
    CaseReportVersionRead,
    CaseUpdate,
)


logger = logging.getLogger("app.modules.cases")


class CaseService:
    def __init__(self, db) -> None:
        self.db = db
        self.repo = CasesRepository(db)
        self.command_service = CaseCommandService(db)
        self.report_service = CaseReportService(db)
        self.remark_service = CaseRemarkService(db)

    def create_case(self, *, case_in: CaseCreate, current_user: User) -> CaseRead | CaseLawyerRead:
        return self.command_service.create_case(case_in=case_in, current_user=current_user)

    def list_cases(
        self,
        *,
        request: Request,
        response: Response,
        status_filter: str | None,
        legal_type: str | None,
        q: str | None,
        sort_by: str,
        sort_order: str,
        page: int | None,
        page_size: int | None,
        skip: int | None,
        limit: int | None,
        current_user: User,
    ) -> list[Case]:
        pagination = resolve_pagination_params(page=page, page_size=page_size, skip=skip, limit=limit)

        if pagination.source in {"legacy", "mixed"}:
            logger.info(
                "cases.pagination.legacy request_id=%s user_id=%s source=%s page=%s page_size=%s skip=%s limit=%s",
                getattr(request.state, "request_id", None),
                current_user.id,
                pagination.source,
                pagination.page,
                pagination.page_size,
                pagination.skip,
                pagination.limit,
            )

        total_count, cases = self.repo.list_visible_cases(
            current_user=current_user,
            status_filter=status_filter,
            legal_type=legal_type,
            keyword=q or "",
            sort_by=sort_by,
            sort_order=sort_order,
            skip=pagination.skip,
            limit=pagination.limit,
        )
        response.headers["X-Page"] = str(pagination.page)
        response.headers["X-Page-Size"] = str(pagination.page_size)
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Total-Pages"] = str((total_count + pagination.page_size - 1) // pagination.page_size)
        return cases

    def get_case(self, *, case_id: int, current_user: User) -> CaseRead | CaseLawyerRead:
        case = get_case_or_404(self.db, case_id=case_id, current_user=current_user)
        if normalize_role(current_user.role) == "client" and case.client_id != current_user.id:
            raise AppError(
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.CASE_ACCESS_DENIED,
                message="无权查看该案件。",
                detail="无权查看该案件。",
            )
        return serialize_case_for_viewer(db=self.db, case=case, current_user=current_user)

    def update_client_remark(
        self,
        *,
        case_id: int,
        payload: CaseClientRemarkUpdate,
        current_user: User,
    ) -> CaseRead:
        return self.remark_service.update_client_remark(
            case_id=case_id,
            payload=payload,
            current_user=current_user,
        )

    def update_lawyer_remark(
        self,
        *,
        case_id: int,
        payload: CaseLawyerRemarkUpdate,
        current_user: User,
    ) -> CaseLawyerRead:
        return self.remark_service.update_lawyer_remark(
            case_id=case_id,
            payload=payload,
            current_user=current_user,
        )

    def list_case_report_versions(self, *, case_id: int, current_user: User) -> list[CaseReportVersionRead]:
        return self.report_service.list_case_report_versions(case_id=case_id, current_user=current_user)

    def get_case_report_access_link(
        self,
        *,
        case_id: int,
        regenerate: bool,
        current_user: User,
    ) -> CaseReportAccessLinkRead:
        return self.report_service.get_case_report_access_link(
            case_id=case_id,
            regenerate=regenerate,
            current_user=current_user,
        )

    def get_case_report_version_access_link(
        self,
        *,
        case_id: int,
        report_name: str,
        current_user: User,
    ) -> CaseReportAccessLinkRead:
        return self.report_service.get_case_report_version_access_link(
            case_id=case_id,
            report_name=report_name,
            current_user=current_user,
        )

    def download_case_report_version(
        self,
        *,
        case_id: int,
        report_name: str,
        current_user: User,
    ) -> Response:
        return self.report_service.download_case_report_version(
            case_id=case_id,
            report_name=report_name,
            current_user=current_user,
        )

    def download_case_report(
        self,
        *,
        case_id: int,
        regenerate: bool,
        current_user: User,
    ) -> Response:
        return self.report_service.download_case_report(
            case_id=case_id,
            regenerate=regenerate,
            current_user=current_user,
        )

    def update_case(
        self,
        *,
        case_id: int,
        case_in: CaseUpdate,
        current_user: User,
    ) -> CaseLawyerRead:
        return self.command_service.update_case(
            case_id=case_id,
            case_in=case_in,
            current_user=current_user,
        )

    def get_case_invite_qrcode(self, *, case_id: int, current_user: User) -> CaseInviteRead:
        return self.command_service.get_case_invite_qrcode(case_id=case_id, current_user=current_user)
