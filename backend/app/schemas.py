from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ChatMessageRequest(APIModel):
    user_id: str = "U001"
    device_id: str = "D001"
    message: str = "Please help me clean the AC filter."
    request_id: str | None = None
    session_id: str | None = None
    include_rag_evidence: bool = True
    rag_limit: int = Field(default=3, ge=1, le=10)


class AnalyzeRequest(ChatMessageRequest):
    pass


class RAGSearchRequest(APIModel):
    query: str
    product_type: str
    model_name: str | None = None
    procedure_type: str | None = None
    language: str = "en"
    session_id: str | None = None
    official_asset_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)


class ARPlanRequest(APIModel):
    analysis: dict[str, Any] | None = None
    user_id: str = "U001"
    device_id: str = "D001"
    message: str = "Please help me clean the AC filter."
    request_id: str | None = None
    session_id: str | None = None
    include_rag_evidence: bool = True
    rag_limit: int = Field(default=3, ge=1, le=10)


class ARSessionCreateRequest(APIModel):
    guide_id: str
    user_id: str = "U001"
    device_id: str = "D001"
    session_id: str | None = None
    guide_type: Literal["preventive_care", "self_check"] = "preventive_care"
    structure_type: str = "wall_ac_type_a"
    completed_steps: list[int | str] = Field(default_factory=list)
    completed: bool = False
    solved: bool | None = None
    clicked_as: bool = False


class ARSessionUpdateRequest(APIModel):
    completed_steps: list[int | str] | None = None
    completed: bool | None = None
    solved: bool | None = None
    clicked_as: bool | None = None


class EnvironmentRefreshRequest(APIModel):
    provider_id: str = "ENV_PROVIDER_OPENWEATHER"
    user_id: str | None = "U001"
    region: str = "Gujarat"
    city: str | None = "Ahmedabad"
    product_type: str | None = None
    requested_metrics: list[str] = Field(
        default_factory=lambda: [
            "temperature",
            "humidity",
            "aqi",
            "pm25",
            "pm10",
            "rain_monsoon_intensity",
            "water_hardness",
        ]
    )
    force_refresh: bool = True
    cache_ttl_minutes: int = Field(default=180, ge=0, le=1440)


class CareRiskEvaluateRequest(APIModel):
    user_id: str = "U001"
    device_id: str = "D001"
    procedure_type: str | None = None
    region: str | None = None
    city: str | None = None
    cache_ttl_minutes: int = Field(default=180, ge=0, le=1440)
    force_environment_refresh: bool = False


class IntentRiskEvaluationRequest(APIModel):
    product_type: str | None = None
    limit: int | None = Field(default=None, ge=1)
    run_id: str | None = None


class GuideCompleteRequest(APIModel):
    user_id: str = "U001"
    device_id: str = "D001"
    service_flow_type: Literal["self_care", "self_as"] = "self_care"
    procedure_type: str | None = None
    source_chat_session_id: str | None = None
    language_code: str = "en-IN"


class DeviceCareSummary(APIModel):
    summary_id: str | None = None
    user_id: str
    device_id: str
    self_care_count: int = 0
    self_as_count: int = 0
    total_care_count: int = 0
    care_score: float | None = 0
    last_self_care_at: str | None = None
    last_self_as_at: str | None = None
    updated_at: str | None = None


class CareHistoryItem(APIModel):
    history_id: str
    service_flow_type: Literal["self_care", "self_as", "expert_as"]
    activity_channel: Literal["official_content", "ar_guide", "chatbot", "expert_as"]
    procedure_type: str | None = None
    title: str | None = None
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    source_content_view_id: str | None = None
    source_ar_session_id: str | None = None
    source_route_log_id: str | None = None
    source_expert_as_request_id: str | None = None
    step_log_count: int | None = None


class DeviceCareHistoryResponse(APIModel):
    user_id: str
    device_id: str
    summary: DeviceCareSummary
    items: list[CareHistoryItem]


class HealthResponse(APIModel):
    ok: bool
    service: str
    version: str


class DictResponse(APIModel):
    data: dict[str, Any]
