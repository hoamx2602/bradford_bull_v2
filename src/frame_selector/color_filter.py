import cv2
import numpy as np

# HSV ranges (OpenCV: H 0-179, S 0-255, V 0-255). Calibrated for broadcast footage.
COLOR_PRESETS: dict[str, list[tuple]] = {
    'white':  [((0,   0, 180), (179,  55, 255))],
    'black':  [((0,   0,   0), (179, 110,  65))],
    'red':    [((0,  90,  60), ( 10, 255, 255)),
               ((168, 90,  60), (179, 255, 255))],
    'blue':   [((95,  80,  50), (130, 255, 255))],
    'yellow': [((18,  90, 100), ( 35, 255, 255))],
    'orange': [((8,  120, 120), ( 20, 255, 255))],
    'claret': [((160, 80,  40), (179, 255, 170)),
               ((0,   80,  40), (  8, 255, 170))],
    'green':  [((35, 100,  40), ( 85, 255, 200))],
}

_GRASS_LOW  = np.array([30,  35, 25], dtype=np.uint8)
_GRASS_HIGH = np.array([90, 255, 230], dtype=np.uint8)


def color_mask(hsv: np.ndarray, color: str) -> np.ndarray:
    """Return uint8 0/255 mask for pixels matching a named color in HSV space."""
    if color not in COLOR_PRESETS:
        raise ValueError(f'Unknown color "{color}". Available: {list(COLOR_PRESETS)}')
    out = None
    for lo, hi in COLOR_PRESETS[color]:
        m = cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8))
        out = m if out is None else cv2.bitwise_or(out, m)
    return out


def grass_ratio(frame_bgr: np.ndarray, overlay_mask: np.ndarray | None = None) -> float:
    """Fraction of frame pixels that are pitch grass (green HSV band)."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, _GRASS_LOW, _GRASS_HIGH)
    if overlay_mask is not None:
        m[overlay_mask > 0] = 0
    return float((m > 0).mean())


# Dark target colors that should be discriminated from striped opponents (e.g. Hull FC black-white hoops).
_DARK_TARGETS = {'black', 'claret', 'red', 'blue'}


def classify_bbox(
    frame_bgr: np.ndarray,
    bbox: tuple,
    target_color: str,
    overlay_mask: np.ndarray | None = None,
    threshold: float = 0.28,
) -> bool:
    """Return True if the jersey ROI of this bbox matches the target color.

    Robust to non-standard postures: samples 3 overlapping vertical torso bands
    so bent/diving/kneeling players are still classified correctly.
    Includes an anti-stripe guard against teams wearing the target color mixed
    with white (e.g. Hull FC's black-and-white hoops vs Bradford's solid black).
    """
    H, W = frame_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    bh, bw = y2 - y1, x2 - x1
    if bh < 20 or bw < 8:
        return False

    jx1 = x1 + int(0.15 * bw); jx2 = x2 - int(0.15 * bw)
    if jx2 <= jx1:
        return False

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    # Fix 1 — adaptive threshold: wide aspect = bent/diving player → lower bar
    aspect = bw / max(bh, 1)
    eff_thr = threshold * 0.7 if aspect > 0.6 else threshold

    # Fix 3 — anti-stripe guard: distinguish solid-dark target (Bradford)
    # from dark-with-white-stripes opponents (Hull FC hoops).
    # Use the UPPER torso only (avoids legs/shorts which can be white) and
    # compare target-vs-white ratios so jersey numbers/text don't false-reject.
    if target_color in _DARK_TARGETS:
        fy1 = y1 + int(0.15 * bh); fy2 = y1 + int(0.50 * bh)
        if fy2 > fy1:
            full_hsv = hsv[fy1:fy2, jx1:jx2]
            white_m = color_mask(full_hsv, 'white')
            tgt_m  = color_mask(full_hsv, target_color)
            if overlay_mask is not None:
                ov = overlay_mask[fy1:fy2, jx1:jx2]
                white_m[ov > 0] = 0
                tgt_m[ov > 0] = 0
            white_ratio = float((white_m > 0).sum() / max(1, white_m.size))
            tgt_ratio   = float((tgt_m  > 0).sum() / max(1, tgt_m.size))
            # Striped opponent only if white is high AND target is not dominant.
            # Bradford has ~5-15% white (numbers, sponsor) but ~50%+ black.
            # Hull has ~30-50% white hoops, similar amount of black.
            if white_ratio > 0.25 and tgt_ratio < 2.0 * white_ratio:
                return False

    # Fix 2 — multi-ROI sampling: try 3 overlapping bands so jersey is found
    # whether the player is standing (15-45%), bent (35-65%), or diving (50-80%).
    bands = [(0.15, 0.45), (0.35, 0.65), (0.50, 0.80)]
    best_ratio = 0.0
    for ylo, yhi in bands:
        jy1 = y1 + int(ylo * bh)
        jy2 = y1 + int(yhi * bh)
        if jy2 <= jy1:
            continue
        roi_hsv = hsv[jy1:jy2, jx1:jx2]
        m = color_mask(roi_hsv, target_color)
        if overlay_mask is not None:
            m[overlay_mask[jy1:jy2, jx1:jx2] > 0] = 0
        ratio = float((m > 0).sum() / max(1, m.size))
        if ratio > best_ratio:
            best_ratio = ratio

    return best_ratio >= eff_thr
