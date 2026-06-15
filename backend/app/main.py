from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import get_service
from .routers import ai, ar, care, chat, devices, environment, evaluation, frontend_compat, guides, rag
from .schemas import HealthResponse
from .services import CareShotBackendService


app = FastAPI(
    title="CareShot AR Guide Engine API",
    description="FastAPI backend for ThinQ-context appliance care, official RAG evidence, and AR guide plans.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(rag.router, prefix="/api/v1")
app.include_router(ar.router, prefix="/api/v1")
app.include_router(environment.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")
app.include_router(care.router, prefix="/api/v1")
app.include_router(guides.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(frontend_compat.router, prefix="/api")


@app.get("/api/v1/health", response_model=HealthResponse)
def health(service: CareShotBackendService = Depends(get_service)) -> dict:
    return service.health()


@app.get("/api/v1/demo/context")
def demo_context(
    user_id: str = "U001",
    device_id: str = "D001",
    service: CareShotBackendService = Depends(get_service),
) -> dict:
    return service.demo_context(user_id=user_id, device_id=device_id)
