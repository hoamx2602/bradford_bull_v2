import cv2
import numpy as np
import pytest

from frame_selector.color_filter import (
    COLOR_PRESETS,
    classify_bbox,
    color_mask,
    grass_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def solid_bgr(h: int, s: int, v: int, size: int = 100) -> np.ndarray:
    """Solid frame from HSV values (OpenCV convention)."""
    hsv = np.full((size, size, 3), [h, s, v], dtype=np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def solid_hsv(h: int, s: int, v: int, size: int = 100) -> np.ndarray:
    return np.full((size, size, 3), [h, s, v], dtype=np.uint8)


# ---------------------------------------------------------------------------
# color_mask
# ---------------------------------------------------------------------------

def test_color_mask_white_detects_white():
    hsv = solid_hsv(0, 10, 230)
    m = color_mask(hsv, 'white')
    assert (m > 0).mean() > 0.9


def test_color_mask_blue_detects_blue():
    hsv = solid_hsv(110, 200, 180)
    m = color_mask(hsv, 'blue')
    assert (m > 0).mean() > 0.9


def test_color_mask_no_cross_match():
    # red should not match blue
    hsv = solid_hsv(0, 200, 200)
    m = color_mask(hsv, 'blue')
    assert (m > 0).mean() < 0.05


def test_color_mask_unknown_color_raises():
    hsv = solid_hsv(0, 0, 200)
    with pytest.raises(ValueError):
        color_mask(hsv, 'purple')


@pytest.mark.parametrize("color", list(COLOR_PRESETS.keys()))
def test_all_presets_callable(color):
    hsv = solid_hsv(0, 0, 200)
    m = color_mask(hsv, color)
    assert m.dtype == np.uint8


# ---------------------------------------------------------------------------
# grass_ratio
# ---------------------------------------------------------------------------

def test_grass_ratio_green_pitch():
    frame = solid_bgr(60, 180, 120)  # HSV grass green
    r = grass_ratio(frame)
    assert r > 0.8


def test_grass_ratio_white_is_low():
    frame = solid_bgr(0, 0, 230)
    r = grass_ratio(frame)
    assert r < 0.1


def test_grass_ratio_overlay_excluded():
    frame = solid_bgr(60, 180, 120)  # fully green
    overlay = np.full(frame.shape[:2], 255, dtype=np.uint8)  # fully masked
    r = grass_ratio(frame, overlay_mask=overlay)
    assert r == 0.0


# ---------------------------------------------------------------------------
# classify_bbox
# ---------------------------------------------------------------------------

def test_classify_bbox_white_player():
    frame = np.full((300, 200, 3), [230, 230, 230], dtype=np.uint8)  # white
    bbox = (0, 0, 200, 300)
    assert classify_bbox(frame, bbox, 'white', threshold=0.20) is True


def test_classify_bbox_wrong_color_rejected():
    frame = np.full((300, 200, 3), [230, 230, 230], dtype=np.uint8)  # white
    bbox = (0, 0, 200, 300)
    assert classify_bbox(frame, bbox, 'blue', threshold=0.20) is False


def test_classify_bbox_too_small_returns_false():
    frame = np.full((300, 200, 3), [230, 230, 230], dtype=np.uint8)
    # bbox too small (bh < 20)
    assert classify_bbox(frame, (0, 0, 5, 10), 'white') is False


# ---------------------------------------------------------------------------
# COLOR_PRESETS completeness
# ---------------------------------------------------------------------------

def test_preset_colors_complete():
    expected = {'white', 'black', 'red', 'blue', 'yellow', 'orange', 'claret', 'green'}
    assert set(COLOR_PRESETS.keys()) == expected
