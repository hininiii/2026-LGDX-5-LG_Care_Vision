from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_service
from ..schemas import EnvironmentRefreshRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/environment", tags=["environment"])


@router.get("/current")
def get_current_environment(
    region: str = "Gujarat",
    city: str | None = "Ahmedabad",
    user_id: str | None = "U001",
    product_type: str | None = None,
    provider_id: str | None = None,
    requested_metrics: list[str] | None = Query(default=None),
    cache_ttl_minutes: int = 60,
    force_refresh: bool = False,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.get_current_environment(
        region=region,
        city=city,
        user_id=user_id,
        product_type=product_type,
        requested_metrics=requested_metrics,
        provider_id=provider_id,
        cache_ttl_minutes=cache_ttl_minutes,
        force_refresh=force_refresh,
    )


@router.post("/refresh")
def refresh_environment(
    request: EnvironmentRefreshRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.refresh_environment(request.model_dump())
