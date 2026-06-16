from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import get_service
from .routers import ai, ar, care, chat, devices, environment, evaluation, frontend_compat, guides, rag
from .schemas import HealthResponse
from .services import CareShotBackendService


def environment_auto_refresh_enabled() -> bool:
    return os.getenv("CARESHOT_ENV_AUTO_REFRESH_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}


async def environment_auto_refresh_loop() -> None:
    initial_delay_seconds = int(os.getenv("CARESHOT_ENV_AUTO_REFRESH_INITIAL_DELAY_SECONDS", "5"))
    interval_minutes = int(os.getenv("CARESHOT_ENV_AUTO_REFRESH_INTERVAL_MINUTES", "60"))
    provider_id = os.getenv("CARESHOT_ENV_AUTO_REFRESH_PROVIDER", "ENV_PROVIDER_OPENMETEO")
    target_limit = int(os.getenv("CARESHOT_ENV_AUTO_REFRESH_TARGET_LIMIT", "20"))
    await asyncio.sleep(max(0, initial_delay_seconds))
    while True:
        try:
            service = get_service()
            result = await asyncio.to_thread(
                service.refresh_scheduled_environment_targets,
                provider_id=provider_id,
                limit=target_limit,
            )
            app.state.last_environment_auto_refresh = result
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            app.state.last_environment_auto_refresh = {"failed_count": 1, "error": str(exc)}
        await asyncio.sleep(max(1, interval_minutes) * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task: asyncio.Task | None = None
    if environment_auto_refresh_enabled():
        task = asyncio.create_task(environment_auto_refresh_loop())
    app.state.environment_auto_refresh_task = task
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="CareShot AR Guide Engine API",
    description="FastAPI backend for ThinQ-context appliance care, official RAG evidence, and AR guide plans.",
    version="0.2.0",
    lifespan=lifespan,
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
