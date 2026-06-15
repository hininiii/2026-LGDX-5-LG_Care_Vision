from __future__ import annotations

from .services import CareShotBackendService, get_backend_service


def get_service() -> CareShotBackendService:
    return get_backend_service()
