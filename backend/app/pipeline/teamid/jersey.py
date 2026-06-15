"""Jersey-region extraction — which pixels belong to a player's shirt.

The reference builder (scripts/build_team_refs.py) and the runtime tracker
MUST look at the same pixels, so this is the single place that decides it.

Per detection:
    1. Take the upper-body band of the bbox (SHIRT_TOP .. SHIRT_BOTTOM).
    2. Drop grass-green and skin pixels.
Returns the band crop (BGR) plus a boolean mask of kept shirt pixels — used
both for the colour histogram and to black out the background before SigLIP.
"""
from __future__ import annotations

import cv2
import numpy as np

# Upper-body band of the bbox (skip head, stop before shorts). The FULL bbox
# width is intentional: rugby shirts carry big white numbers in the centre of
# the back, so centre-only sampling skews dark kits bright — sleeves and sides
# balance it out.
SHIRT_TOP = 0.15
SHIRT_BOTTOM = 0.45

# Minimum shirt pixels for a feature to be considered reliable.
MIN_SHIRT_PX = 25


def _green_mask(region_bgr: np.ndarray) -> np.ndarray:
    """Grass-green pixels (OpenCV HSV: H in [30,90], S > 40)."""
    hsv = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2HSV)
    h, s = hsv[:, :, 0], hsv[:, :, 1]
    return (h >= 30) & (h <= 90) & (s > 40)


def _skin_mask(region_bgr: np.ndarray) -> np.ndarray:
    """Skin pixels via YCrCb thresholds (face / arms)."""
    ycrcb = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    return (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)


def box_iou(b1, b2) -> float:
    xa, ya = max(b1[0], b2[0]), max(b1[1], b2[1])
    xb, yb = min(b1[2], b2[2]), min(b1[3], b2[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    if inter <= 0:
        return 0.0
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    return float(inter / (a1 + a2 - inter + 1e-6))


def boxes_contested(boxes, iou_thr: float = 0.40) -> list[bool]:
    """Per-box flag: True when another person box overlaps it heavily — the
    jersey band there mixes two players' kits (tackles, mauls)."""
    n = len(boxes)
    out = [False] * n
    for i in range(n):
        for j in range(i + 1, n):
            if box_iou(boxes[i], boxes[j]) > iou_thr:
                out[i] = out[j] = True
    return out


def box_trustworthy(box, frame_h: int) -> bool:
    """False when the bbox cannot contain a readable jersey band.

    A box clipped at the TOP of the frame has lost head+shoulders, so the
    "shirt band" of what remains is some other body part (a touchline
    official's trousers classified an entire track wrong this way). Squat
    boxes (h/w too low) are partial bodies or merged players. Bottom/side
    clipping is fine — the band sits in the upper-centre of the box.
    """
    x1, y1, x2, y2 = (float(v) for v in box)
    w, h = x2 - x1, y2 - y1
    if y1 <= 2:                      # clipped at frame top
        return False
    if h < 28 or w < 8:              # too small to read a kit colour
        return False
    return h / max(w, 1.0) >= 1.15   # upright-person aspect


def get_jersey_region(frame_bgr: np.ndarray, box) -> tuple[np.ndarray | None, np.ndarray | None]:
    """Extract the shirt band and a bool mask of kept shirt pixels.

    Returns (region_bgr, pixel_mask) or (None, None) if the crop is degenerate.
    """
    H, W = frame_bgr.shape[:2]
    x1, y1, x2, y2 = (int(v) for v in box)
    x1, x2 = max(0, x1), min(W, x2)
    y1, y2 = max(0, y1), min(H, y2)
    if x2 - x1 < 3 or y2 - y1 < 6:
        return None, None

    h = y2 - y1
    sy1 = y1 + int(SHIRT_TOP * h)
    sy2 = y1 + int(SHIRT_BOTTOM * h)
    if sy2 <= sy1 + 4:
        return None, None

    region = frame_bgr[sy1:sy2, x1:x2]
    if region.size == 0:
        return None, None

    keep = ~_green_mask(region) & ~_skin_mask(region)

    # Fallbacks so we never return an all-False mask on a real player.
    if keep.sum() < MIN_SHIRT_PX:
        alt = ~_green_mask(region)  # drop only grass
        keep = alt if alt.sum() >= MIN_SHIRT_PX else np.ones(region.shape[:2], dtype=bool)

    return region, keep


def jersey_quality(region_bgr: np.ndarray | None, pixel_mask: np.ndarray | None) -> float:
    """Soft reliability weight in [0.2, 1.0] for one shirt crop.

    Combines shirt-pixel coverage with sharpness (variance of Laplacian).
    Used to weight temporal votes and to filter reference crops.
    """
    if region_bgr is None or pixel_mask is None or region_bgr.size == 0:
        return 0.0
    coverage = float(pixel_mask.mean())
    gray = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    q_cov = min(coverage / 0.25, 1.0)
    q_sharp = min(sharp / 150.0, 1.0)
    return 0.2 + 0.8 * q_cov * q_sharp
