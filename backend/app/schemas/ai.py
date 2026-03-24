from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ParseOptions(BaseModel):
    extract_parties: bool = True
    extract_timeline: bool = True
    extract_evidence: bool = True
    extract_laws: bool = True


class DocumentParseRequest(BaseModel):
    file_id: int = Field(gt=0)
    parse_options: ParseOptions = Field(default_factory=ParseOptions)


class DocumentParseResponse(BaseModel):
    task_id: str
    status: str
    message: str


class CaseFactRead(BaseModel):
    id: int
    case_id: int
    file_id: int | None
    fact_type: str
    content: str
    source_page: int | None
    confidence: float
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

    # Compatibility fields for existing frontend rendering.
    description: str
    occurrence_time: str | None = None
    evidence_id: int | None = None


class CaseFactListResponse(BaseModel):
    total: int
    items: list[CaseFactRead]


class AnalysisRequest(BaseModel):
    analysis_types: list[str] = Field(
        default_factory=lambda: ["legal_analysis", "case_strength", "strategy"]
    )
    include_precedents: bool = True
    focus_areas: list[str] = Field(default_factory=list)


class AnalysisStartResponse(BaseModel):
    task_id: str
    status: str
    estimated_time: int = 120


class AnalysisResultRead(BaseModel):
    id: int
    case_id: int
    analysis_type: str
    result_data: dict = Field(default_factory=dict)
    applicable_laws: list[str] = Field(default_factory=list)
    related_cases: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    ai_model: str
    token_usage: int
    cost: Decimal
    created_at: datetime

    # Compatibility fields for existing frontend rendering.
    summary: str = ""
    win_rate: float = 0.0


class AnalysisResultListResponse(BaseModel):
    items: list[AnalysisResultRead]


class FalsificationRequest(BaseModel):
    analysis_id: int = Field(gt=0)
    challenge_modes: list[str] = Field(default_factory=lambda: ["logic", "evidence", "law"])
    iteration_count: int = Field(default=3, ge=1, le=10)


class FalsificationStartResponse(BaseModel):
    task_id: str
    status: str


class FalsificationRecordRead(BaseModel):
    id: int
    case_id: int
    analysis_id: int | None
    challenge_type: str
    challenge_question: str
    response: str
    is_falsified: bool
    severity: str
    improvement_suggestion: str | None
    iteration: int
    ai_model: str
    created_at: datetime

    # Compatibility fields for existing frontend rendering.
    fact_description: str
    reason: str
    evidence_gap: str | None = None


class FalsificationSummary(BaseModel):
    total_challenges: int
    falsified_count: int
    critical_issues: int
    major_issues: int
    minor_issues: int


class FalsificationResultResponse(BaseModel):
    summary: FalsificationSummary
    items: list[FalsificationRecordRead]


class AITaskStatusRead(BaseModel):
    id: str
    task_id: str
    task_type: str
    status: str
    progress: int
    retry_count: int = 0
    next_retry_at: datetime | None = None
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    message: str | None = None
    started_at: datetime | None = None
    estimated_completion: datetime | None = None
    error_message: str | None = None


class AITaskListItem(BaseModel):
    id: str
    task_id: str
    case_id: int
    task_type: str
    status: str
    progress: int
    retry_count: int = 0
    next_retry_at: datetime | None = None
    worker_id: str | None = None
    message: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class AITaskListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AITaskListItem]


class AITaskRetryRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class AITaskRetryResponse(BaseModel):
    task_id: str
    source_task_id: str
    status: str
    message: str
