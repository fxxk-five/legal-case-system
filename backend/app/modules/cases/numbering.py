from __future__ import annotations

from datetime import datetime, timezone
import re

from sqlalchemy.orm import Session

from app.core.legal_types import legal_type_case_code
from app.modules.cases.repository import CasesRepository

_DEFAULT_CASE_PREFIX = "CASE"
_CASE_NUMBER_PADDING = 5


def normalize_case_number(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_prefix(tenant_code: str | None) -> str:
    raw = (tenant_code or "").strip().upper()
    normalized = re.sub(r"[^A-Z0-9]+", "", raw)
    return normalized[:12] or _DEFAULT_CASE_PREFIX


def generate_case_number(*, db: Session, tenant_id: int, tenant_code: str | None, legal_type: str | None) -> str:
    now = datetime.now(timezone.utc)
    year = now.year
    repo = CasesRepository(db)
    sequence = repo.get_case_number_sequence_for_update(tenant_id=tenant_id, year=year)

    if sequence is None:
        sequence = repo.create_case_number_sequence(tenant_id=tenant_id, year=year, next_value=1)

    current_value = int(sequence.next_value)
    sequence.next_value = current_value + 1
    repo.save_case_number_sequence(sequence)

    return f"{_normalize_prefix(tenant_code)}-{year}-{legal_type_case_code(legal_type)}-{current_value:0{_CASE_NUMBER_PADDING}d}"
