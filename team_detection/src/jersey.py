"""
Unified jersey-region extraction — shared by ref_build.py and process_video.py.

The single most important consistency fix: BOTH the reference builder and the
inference pipeline must look at the *same* pixels.  This module is the one place
that decides "which pixels belong to a player's shirt".

Pipeline per detection:
    1. Take the upper-body band of the bbox  (SHIRT_TOP .. SHIRT_BOTTOM).
    2. Drop grass-green pixels and skin pixels.
    3. If a segmentation mask is supplied (SAM2), intersect with it so the
       background is removed exactly.
Returns the band crop (BGR) plus a boolean `pixel_mask` of the kept shirt
pixels — used both for the colour histogram and to black-out the background
before SigLIP.
"""
import cv2
import numpy as np

# Upper-body band of the bbox (skip head, stop before shorts).
SHIRT_TOP    = 0.15
SHIRT_BOTTOM = 0.45

# Minimum shirt pixels for a feature to be considered reliable.
MIN_SHIRT_PX = 25


def _green_mask(region_bgr: np.ndarray) -> np.ndarray:
    """Grass-green pixels (OpenCV HSV: H in [30,90], S > 40)."""
    hsv = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2HSV)
    h, s = hsv[:, :, 0], hsv[:, :, 1]
    return (h >= 30) & (h <= 90) & (s > 40)


def _skin_mask(region_bgr: np.ndarray) -> np.ndarray:
    """Skin pixels via YCrCb thresholds (face / arms / legs)."""
    ycrcb = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2YCrCb)
    cr, cb = ycrcb[:, :, 1], ycrcb[:, :, 2]
    return (cr >= 133) & (cr <= 173) & (cb >= 77) & (cb <= 127)


def get_jersey_region(frame_bgr: np.ndarray, box, mask: np.ndarray | None = None):
    """
    Extract the shirt band and a boolean mask of kept shirt pixels.

    Parameters
    ----------
    frame_bgr : full frame, BGR (H, W, 3)
    box       : (x1, y1, x2, y2) player bbox
    mask      : optional full-frame bool mask (H, W) for this player (SAM2)

    Returns
    -------
    (region_bgr, pixel_mask) or (None, None) if the crop is degenerate.
    region_bgr : (h, w, 3) BGR band crop
    pixel_mask : (h, w) bool — True where a shirt pixel was kept
    """
    H, W = frame_bgr.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, x2 = max(0, x1), min(W, x2)
    y1, y2 = max(0, y1), min(H, y2)
    if x2 - x1 < 3 or y2 - y1 < 6:
        return None, None

    h   = y2 - y1
    sy1 = y1 + int(SHIRT_TOP    * h)
    sy2 = y1 + int(SHIRT_BOTTOM * h)
    if sy2 <= sy1 + 4:
        return None, None

    region = frame_bgr[sy1:sy2, x1:x2]
    if region.size == 0:
        return None, None

    keep = ~_green_mask(region) & ~_skin_mask(region)

    if mask is not None:
        sub = mask[sy1:sy2, x1:x2]
        if sub.shape == keep.shape:
            keep &= sub.astype(bool)

    # Fallbacks so we never return an all-False mask on a real player.
    if keep.sum() < MIN_SHIRT_PX:
        alt = ~_green_mask(region)          # drop only grass
        if alt.sum() >= MIN_SHIRT_PX:
            keep = alt
        else:
            keep = np.ones(region.shape[:2], dtype=bool)

    return region, keep


def jersey_quality(region_bgr: np.ndarray, pixel_mask: np.ndarray) -> float:
    """
    Soft reliability weight in [0.2, 1.0] for one detection's shirt crop.

    Combines shirt-pixel coverage with image sharpness (variance of
    Laplacian).  Used to weight temporal votes and to filter reference crops.
    """
    if region_bgr is None or pixel_mask is None or region_bgr.size == 0:
        return 0.0
    coverage = float(pixel_mask.mean())
    gray     = cv2.cvtColor(region_bgr, cv2.COLOR_BGR2GRAY)
    sharp    = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    q_cov   = min(coverage / 0.25, 1.0)
    q_sharp = min(sharp / 150.0,  1.0)
    return 0.2 + 0.8 * q_cov * q_sharp
