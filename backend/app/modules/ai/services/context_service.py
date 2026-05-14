from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.modules.cases.models.case import Case

if TYPE_CHECKING:
    from app.modules.ai.service import AIService


def build_case_context(service: AIService, *, case: Case) -> dict[str, object]:
    client_remark = sanitize_case_context_text(service, case.client_remark, max_length=1200)
    lawyer_remark = sanitize_case_context_text(service, case.lawyer_remark, max_length=2000)
    return {
        "case_number": case.case_number,
        "case_title": case.title,
        "legal_type": case.legal_type,
        "client_remark": client_remark or None,
        "lawyer_remark": lawyer_remark or None,
        "has_client_remark": bool(client_remark),
        "has_lawyer_remark": bool(lawyer_remark),
    }


def build_case_context_notes(case_context: dict[str, object] | None) -> list[str]:
    if not case_context:
        return []

    notes: list[str] = []
    client_remark = str(case_context.get("client_remark") or "").strip()
    lawyer_remark = str(case_context.get("lawyer_remark") or "").strip()
    if client_remark:
        notes.append(f"当事人补充说明（{client_remark[:40]}{'…' if len(client_remark) > 40 else ''}）")
    if lawyer_remark:
        notes.append(f"律师内部备注（{lawyer_remark[:40]}{'…' if len(lawyer_remark) > 40 else ''}）")
    return notes


def sanitize_case_context_text(service: AIService, value: str | None, *, max_length: int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    masked = mask_sensitive(text)
    if len(masked) <= max_length:
        return masked
    return f"{masked[:max_length].rstrip()}…"


def mask_sensitive(text: str) -> str:
    text = re.sub(r"(?<!\d)(1\d{2})[\s-]*\d{4}[\s-]*(\d{4})(?!\d)", r"\1****\2", text)
    text = re.sub(r"(?<![\dA-Za-z])(\d{6})[\s-]*\d{8}[\s-]*([0-9Xx]{4})(?![\dA-Za-z])", r"\1********\2", text)
    return text
