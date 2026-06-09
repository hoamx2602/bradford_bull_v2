"""Health + readiness."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.models_zoo import registry

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "device": registry.device(),
        "modelPath": settings.resolved_model_path(),
        "sampleFps": settings.sample_fps,
        "poseEnabled": settings.enable_pose,
    }
