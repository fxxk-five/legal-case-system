from __future__ import annotations

from datetime import datetime, timezone

from app.core.roles import normalize_role
from app.models.user import User
from app.modules.cases.helpers import build_case_timeline
from app.modules.cases.models.case import Case
from app.modules.cases.repository import CasesRepository
from app.modules.files.repository import FilesRepository


def build_case_report_payload(*, db, case: Case, viewer: User) -> dict:
    viewer_scope = normalize_role(viewer.role)
    timeline = build_case_timeline(db, case, viewer_role=viewer.role)
    files = FilesRepository(db).list_case_files(case_id=case.id, tenant_id=case.tenant_id)
    analyses = CasesRepository(db).list_report_analysis_results(
        case_id=case.id,
        tenant_id=case.tenant_id,
        limit=20,
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": viewer_scope,
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "title": case.title,
            "legal_type": case.legal_type,
            "status": case.status,
            "analysis_status": case.analysis_status,
            "analysis_progress": case.analysis_progress,
            "deadline": case.deadline.isoformat() if case.deadline else None,
            "client_name": case.client.real_name if case.client else None,
            "lawyer_name": case.assigned_lawyer.real_name if case.assigned_lawyer else None,
        },
        "timeline": [
            {
                "event_type": item.event_type,
                "title": item.title,
                "description": item.description,
                "occurred_at": item.occurred_at.isoformat(),
            }
            for item in timeline
        ],
        "files": [
            {
                "id": item.id,
                "file_name": item.file_name,
                "file_type": item.file_type,
                "description": None if viewer_scope == "client" else item.description,
                "parse_status": item.parse_status,
                "uploader_role": item.uploader_role,
            }
            for item in files
        ],
        "analyses": [
            {
                "analysis_type": row.analysis_type,
                "summary": str((row.result_data or {}).get("summary") or ""),
                "applicable_laws": list(row.applicable_laws or []),
                "related_cases": list(row.related_cases or []),
                "strengths": list(row.strengths or []),
                "weaknesses": list(row.weaknesses or []),
                "recommendations": list(row.recommendations or []),
                "created_at": row.created_at.isoformat(),
            }
            for row in analyses
        ],
    }
