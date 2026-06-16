from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_service
from ..schemas import (
    ARFilterDetectionRequest,
    ARFilterDetectionResponse,
    ARPlanRequest,
    ARSessionCreateRequest,
    ARSessionUpdateRequest,
)
from ..services import CareShotBackendService
from ..yolo_filter_service import FilterDetectionService, get_filter_detection_service


router = APIRouter(prefix="/ar", tags=["ar"])


@router.post("/plans")
def create_ar_plan(
    request: ARPlanRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    payload = request.model_dump()
    analysis = payload.get("analysis") or service.analyze(payload)
    return service.plan_from_analysis(analysis)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_ar_session(
    request: ARSessionCreateRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.create_session(request.model_dump())


@router.get("/sessions/{session_id}")
def get_ar_session(
    session_id: str,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
    return session


@router.patch("/sessions/{session_id}")
def update_ar_session(
    session_id: str,
    request: ARSessionUpdateRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    session = service.update_session(session_id, request.model_dump(exclude_unset=True))
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")
    return session


@router.post("/filter-detect", response_model=ARFilterDetectionResponse)
def detect_filter_bbox(
    request: ARFilterDetectionRequest,
    detector: FilterDetectionService = Depends(get_filter_detection_service),
) -> dict:
    image_payload = request.image_data_url or request.image_base64
    return detector.detect(
        image_payload=image_payload,
        image_width=request.image_width,
        image_height=request.image_height,
        confidence_threshold=request.confidence_threshold,
        mock_fallback=request.mock_fallback,
    )
