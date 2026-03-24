from __future__ import annotations

DEFAULT_LEGAL_TYPE = "other"

LEGAL_TYPE_CODES: dict[str, str] = {
    "civil_loan": "LOAN",
    "labor_dispute": "LABOR",
    "contract_dispute": "CONTRACT",
    "marriage_family": "FAMILY",
    "traffic_accident": "TRAFFIC",
    "criminal_defense": "CRIMINAL",
    "other": "OTHER",
}

ALLOWED_LEGAL_TYPES: set[str] = set(LEGAL_TYPE_CODES.keys())


def normalize_legal_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return DEFAULT_LEGAL_TYPE
    return normalized


def is_valid_legal_type(value: str | None) -> bool:
    return normalize_legal_type(value) in ALLOWED_LEGAL_TYPES


def legal_type_case_code(value: str | None) -> str:
    return LEGAL_TYPE_CODES.get(normalize_legal_type(value), LEGAL_TYPE_CODES[DEFAULT_LEGAL_TYPE])
