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
def get_person_model():
    """Stock person detector for the team filter (tracking + ref bootstrap)."""
    from ultralytics import YOLO

    settings = get_settings()
    log.info("loading person model: %s", settings.team_person_model)
    return YOLO(settings.team_person_model)


@lru_cache
def get_seg_model():
    """YOLO11 instance-segmentation model (person silhouettes) for the MPS
    body-seg engine."""
    from ultralytics import YOLO

    settings = get_settings()
    log.info("loading seg model: %s", settings.bodyseg_seg_model)
    return YOLO(settings.bodyseg_seg_model)


@lru_cache
def device() -> str:
    d = resolve_device(get_settings().device)
    log.info("inference device: %s", d)
    return d


# ── DensePose (body-part segmentation) ───────────────────────────────────
from pathlib import Path  # noqa: E402

_DENSEPOSE_CONFIGS = Path(__file__).resolve().parent / "densepose_configs"


def densepose_available() -> bool:
    """True if detectron2 + densepose are importable (heavy, often CUDA-only)."""
    try:
        import detectron2  # noqa: F401
        import densepose  # noqa: F401

        return True
    except Exception:
        return False


def _densepose_config_path() -> str:
    s = get_settings()
    if s.bodyseg_config:
        return s.bodyseg_config
    return str(_DENSEPOSE_CONFIGS / "densepose_rcnn_R_50_FPN_s1x.yaml")


@lru_cache
def get_densepose_predictor():
    """Load the DensePose predictor once. detectron2 has no MPS path, so it runs
    on CUDA when present else CPU (slow)."""
    import torch
    from detectron2.config import get_cfg
    from detectron2.engine import DefaultPredictor
    from densepose import add_densepose_config

    s = get_settings()
    cfg = get_cfg()
    add_densepose_config(cfg)
    cfg.merge_from_file(_densepose_config_path())
    cfg.MODEL.WEIGHTS = s.bodyseg_weights
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = s.bodyseg_conf
    cfg.MODEL.DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("loading DensePose predictor on %s", cfg.MODEL.DEVICE)
    return DefaultPredictor(cfg)
