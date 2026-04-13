from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.core.roles import normalize_role
from app.integrations.storage.service import StorageObjectInfo, get_storage_backend
from app.modules.cases.models.case import Case
from app.modules.cases.schemas import CaseReportVersionRead


REPORT_FILE_PATTERN = re.compile(r"^report-(client|lawyer)-(\d{14})\.pdf$")
REPORT_CONTENT_TYPE = "application/pdf"


@dataclass
class CaseReportObject:
    file_name: str
    storage_key: str
    report_scope: str
    generated_at: datetime


def resolve_report_scope(viewer_role: str) -> str:
    return "client" if normalize_role(viewer_role) == "client" else "lawyer"


def get_case_report_prefix(case: Case) -> str:
    return (Path(f"tenant_{case.tenant_id}") / f"case_{case.id}" / "reports").as_posix().rstrip("/") + "/"


def parse_report_file_metadata(file_name: str, *, modified_at: datetime | None = None) -> tuple[str, datetime]:
    match = REPORT_FILE_PATTERN.match(file_name)
    if match is None:
        return "unknown", modified_at or datetime.now(timezone.utc)
    report_scope = match.group(1)
    timestamp = datetime.strptime(match.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    return report_scope, timestamp


def to_case_report_object(item: StorageObjectInfo) -> CaseReportObject:
    report_scope, generated_at = parse_report_file_metadata(
        item.file_name,
        modified_at=item.modified_at,
    )
    return CaseReportObject(
        file_name=item.file_name,
        storage_key=item.storage_key,
        report_scope=report_scope,
        generated_at=generated_at,
    )


def list_case_reports(case: Case) -> list[CaseReportObject]:
    backend = get_storage_backend()
    reports = [
        to_case_report_object(item)
        for item in backend.list_objects(prefix=get_case_report_prefix(case), suffix=".pdf")
    ]
    reports.sort(key=lambda item: (item.generated_at, item.file_name), reverse=True)
    return reports


def resolve_latest_case_report(case: Case, *, report_scope: str) -> CaseReportObject | None:
    report_files = list_case_reports(case)
    if not report_files:
        return None

    scoped_files = [item for item in report_files if item.report_scope == report_scope]
    if scoped_files:
        return scoped_files[0]

    if report_scope == "lawyer":
        return report_files[0]
    return None


def build_case_report_versions(case: Case, *, viewer_role: str) -> list[CaseReportVersionRead]:
    report_files = list_case_reports(case)
    if not report_files:
        return []

    viewer_scope = resolve_report_scope(viewer_role)
    if viewer_scope == "client":
        latest_client_report = resolve_latest_case_report(case, report_scope="client")
        if latest_client_report is None:
            return []
        return [
            CaseReportVersionRead(
                file_name=latest_client_report.file_name,
                report_scope=latest_client_report.report_scope,
                generated_at=latest_client_report.generated_at,
                is_latest=True,
            )
        ]

    latest_by_scope: dict[str, CaseReportObject] = {}
    versions: list[CaseReportVersionRead] = []
    for file_path in report_files:
        scope = file_path.report_scope
        generated_at = file_path.generated_at
        if scope not in latest_by_scope:
            latest_by_scope[scope] = file_path
        versions.append(
            CaseReportVersionRead(
                file_name=file_path.file_name,
                report_scope=scope,
                generated_at=generated_at,
                is_latest=False,
            )
        )

    for row in versions:
        latest_path = latest_by_scope.get(row.report_scope)
        row.is_latest = latest_path is not None and latest_path.file_name == row.file_name
    return versions


def resolve_case_report_by_name(case: Case, *, report_name: str) -> CaseReportObject | None:
    if not report_name.endswith(".pdf"):
        return None
    safe_name = Path(report_name).name
    if safe_name != report_name:
        return None
    for item in list_case_reports(case):
        if item.file_name == safe_name:
            return item
    return None


def persist_generated_report(*, case: Case, report_scope: str, pdf_bytes: bytes) -> CaseReportObject:
    backend = get_storage_backend()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    file_name = f"report-{report_scope}-{ts}.pdf"
    storage_key = get_case_report_prefix(case) + file_name
    backend.save_bytes(
        data=pdf_bytes,
        storage_key=storage_key,
        content_type=REPORT_CONTENT_TYPE,
    )
    return CaseReportObject(
        file_name=file_name,
        storage_key=storage_key,
        report_scope=report_scope,
        generated_at=datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc),
    )
