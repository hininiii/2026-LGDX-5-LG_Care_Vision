from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_service
from ..schemas import CareRiskEvaluateRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/care", tags=["care"])


@router.post("/risk/evaluate")
def evaluate_care_risk(
    request: CareRiskEvaluateRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.evaluate_care_risk(request.model_dump())
