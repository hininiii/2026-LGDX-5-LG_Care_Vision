from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencies import get_service
from ..schemas import DeviceCareHistoryResponse
from ..services import CareShotBackendService


router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("/{device_id}/care-history", response_model=DeviceCareHistoryResponse)
def get_device_care_history(
    device_id: str,
    user_id: str = Query(...),
    service_flow_type: Literal["self_care", "self_as", "expert_as"] | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    result = service.get_device_care_history(
        user_id=user_id,
        device_id=device_id,
        service_flow_type=service_flow_type,
        limit=limit,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device not found: {device_id}")
    return result
