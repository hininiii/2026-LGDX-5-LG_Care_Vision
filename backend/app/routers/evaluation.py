from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_service
from ..schemas import IntentRiskEvaluationRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/intent-risk/run")
def run_intent_risk_evaluation(
    request: IntentRiskEvaluationRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.run_intent_risk_evaluation(request.model_dump())
