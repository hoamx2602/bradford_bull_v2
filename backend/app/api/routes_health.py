"""Health + readiness."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.models_zoo import registry

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    backend = (settings.logo_backend or "yolo").lower()
    model_path = (
        settings.resolved_rfdetr_model_path()
        if backend == "rfdetr"
        else settings.resolved_model_path()
    )
    return {
        "status": "ok",
        "device": registry.device(),
        "detectorBackend": backend,
        "modelPath": model_path,
        "sampleFps": settings.sample_fps,
        "poseEnabled": settings.enable_pose,
    }
