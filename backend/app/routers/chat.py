from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_service
from ..schemas import ChatMessageRequest
from ..services import CareShotBackendService


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages")
def create_chat_message(
    request: ChatMessageRequest,
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.process_chat_message(request.model_dump())
