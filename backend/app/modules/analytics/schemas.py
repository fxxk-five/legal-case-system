from __future__ import annotations

from pydantic import ConfigDict
from pydantic import BaseModel, Field


class AIUsageWindowRead(BaseModel):
    task_count: int = 0
    token_usage: int = 0
    cost_total: float = 0.0


class AIUsageBreakdownItem(BaseModel):
    key: str
    label: str
    count: int = 0


class AIModelBreakdownItem(BaseModel):
    model: str
    result_count: int = 0
    token_usage: int = 0
    cost_total: float = 0.0


class AIUsageRead(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    day: AIUsageWindowRead
    week: AIUsageWindowRead
    month: AIUsageWindowRead
    task_type_breakdown: list[AIUsageBreakdownItem] = Field(default_factory=list)
    status_breakdown: list[AIUsageBreakdownItem] = Field(default_factory=list)
    model_breakdown: list[AIModelBreakdownItem] = Field(default_factory=list)


class PromptSettingsRead(BaseModel):
    parse_prompt: str = ""
    analyze_prompt: str = ""
    falsify_prompt: str = ""


class PromptSettingsUpdate(BaseModel):
    parse_prompt: str = Field(default="", max_length=20000)
    analyze_prompt: str = Field(default="", max_length=20000)
    falsify_prompt: str = Field(default="", max_length=20000)


class ProviderSettingsRead(BaseModel):
    provider_type: str = "openai_compatible"
    base_url: str = ""
    model: str = ""
    api_key_masked: str = ""
    editable: bool = True
    locked: bool = False


class ProviderSettingsUpdate(BaseModel):
    provider_type: str = Field(default="openai_compatible", max_length=50)
    base_url: str = Field(default="", max_length=500)
    model: str = Field(default="", max_length=100)
    api_key: str | None = Field(default=None, max_length=500)
