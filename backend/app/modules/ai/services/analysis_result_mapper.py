from __future__ import annotations

from app.modules.ai.models.ai_analysis import AIAnalysisResult
from app.modules.ai.schemas import AnalysisResultRead


def to_analysis_result_read(row: AIAnalysisResult) -> AnalysisResultRead:
    result_data = row.result_data or {}
    summary = str(result_data.get("summary") or result_data.get("legal_opinion") or "")
    win_rate_raw = result_data.get("win_rate", 0.0)
    try:
        win_rate = float(win_rate_raw)
    except (TypeError, ValueError):
        win_rate = 0.0
    win_rate = max(0.0, min(1.0, win_rate))

    return AnalysisResultRead(
        id=row.id,
        case_id=row.case_id,
        analysis_type=row.analysis_type,
        result_data=result_data,
        applicable_laws=list(row.applicable_laws or []),
        related_cases=list(row.related_cases or []),
        strengths=list(row.strengths or []),
        weaknesses=list(row.weaknesses or []),
        recommendations=list(row.recommendations or []),
        ai_model=row.ai_model,
        token_usage=row.token_usage,
        cost=row.cost,
        created_at=row.created_at,
        summary=summary,
        win_rate=win_rate,
    )
