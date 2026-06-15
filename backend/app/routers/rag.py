from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_service
from ..schemas import RAGSearchRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search")
def search_rag(
    request: RAGSearchRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.search_rag(request.model_dump())
