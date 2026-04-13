from __future__ import annotations


def normalize_win_rate(value: object, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, round(parsed, 2)))


def normalize_str_list(value: object, *, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    normalized = [str(item).strip() for item in value if str(item).strip()]
    return normalized[:8] if normalized else fallback


def estimate_win_rate(*, case_facts_count: int, offset: int) -> float:
    base = 0.55 + min(case_facts_count, 20) * 0.01 - offset * 0.03
    if case_facts_count == 0:
        base = 0.42
    return max(0.2, min(0.95, round(base, 2)))
