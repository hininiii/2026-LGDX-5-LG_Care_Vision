from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_service
from ..schemas import AnalyzeRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/analyze")
def analyze_message(
    request: AnalyzeRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.analyze(request.model_dump())
