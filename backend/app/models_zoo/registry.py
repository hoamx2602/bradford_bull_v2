"""Model loading + device resolution.

Models are heavyweight; load each once and cache. The logo detector is the
fine-tuned YOLO26m; the pose model is a stock ultralytics checkpoint that is
auto-downloaded on first use.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings

log = logging.getLogger("app.models")


def resolve_device(requested: str) -> str:
    """Map 'auto' to the best available backend: CUDA > MPS (Apple) > CPU."""
    if requested and requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "0"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except Exception:  # pragma: no cover - torch always present with ultralytics
        pass
    return "cpu"


@lru_cache
def get_logo_model():
    from ultralytics import YOLO

    settings = get_settings()
    path = settings.resolved_model_path()
    log.info("loading logo model: %s", path)
    return YOLO(path)


@lru_cache
def get_pose_model():
    from ultralytics import YOLO

    settings = get_settings()
    log.info("loading pose model: %s", settings.pose_model)
    return YOLO(settings.pose_model)


@lru_cache
def device() -> str:
    d = resolve_device(get_settings().device)
    log.info("inference device: %s", d)
    return d
