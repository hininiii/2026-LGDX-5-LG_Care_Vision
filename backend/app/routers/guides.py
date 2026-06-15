from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_service
from ..schemas import GuideCompleteRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/guides", tags=["guides"])


@router.get("/options")
def get_guide_options(
    user_id: str = Query(default="U001"),
    device_id: str = Query(default="D001"),
    procedure_type: str | None = None,
    service_flow_type: Literal["self_care", "self_as"] = "self_care",
    language_code: str = "en",
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    result = service.get_guide_options(
        user_id=user_id,
        device_id=device_id,
        procedure_type=procedure_type,
        service_flow_type=service_flow_type,
        language_code=language_code,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device not found: {device_id}")
    return result


@router.post("/{guide_id}/complete")
def complete_guide(
    guide_id: str,
    request: GuideCompleteRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    result = service.complete_guide(guide_id, request.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guide not found: {guide_id}")
    return result
