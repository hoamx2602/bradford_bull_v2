"""Tier 1 — per-frame visibility score.

Implements LOGOS_Exposure_Pricing_Algorithm.md §Tầng 1:

    Visibility = Size x Position x Clarity x OBB_penalty

- Size     = sqrt(box_area / frame_area)        (sqrt so a huge logo can't dominate)
- Position = exp(-dist_from_center^2 / (0.3*W)^2)  (Gaussian: centre=1, corner~0.1)
- Clarity  = YOLO confidence
- OBB_pen. = 1.0 here (HBB model). When an OBB model is trained, set this to
             area_HBB / area_OBB to discount logos skewed by camera angle.
"""
from __future__ import annotations

import math

from app.pipeline.datatypes import Detection

OBB_PENALTY = 1.0  # horizontal-box model; see module docstring.


def size_score(det: Detection) -> float:
    frame_area = max(1.0, det.frame_w * det.frame_h)
    return math.sqrt(min(1.0, det.area / frame_area))


def position_score(det: Detection) -> float:
    cx0, cy0 = det.frame_w / 2, det.frame_h / 2
    dist2 = (det.cx - cx0) ** 2 + (det.cy - cy0) ** 2
    sigma = 0.3 * det.frame_w
    return math.exp(-dist2 / (sigma * sigma)) if sigma > 0 else 0.0


def visibility_score(det: Detection) -> float:
    v = size_score(det) * position_score(det) * det.conf * OBB_PENALTY
    return max(0.0, min(1.0, v))


def annotate(detections: list[Detection]) -> None:
    """Fill det.visibility and the individual factor components in place.

    The components (f_size/f_pos/f_clarity/f_obb) are stored so AI-percentage can
    later be recomputed under a different subset of enabled factors without
    re-running detection; visibility itself stays their clamped product.
    """
    for det in detections:
        det.f_size = size_score(det)
        det.f_pos = position_score(det)
        det.f_clarity = det.conf
        det.f_obb = OBB_PENALTY
        det.visibility = max(0.0, min(1.0, det.f_size * det.f_pos * det.f_clarity * det.f_obb))
