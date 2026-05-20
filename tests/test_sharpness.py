import cv2
import numpy as np
import pytest

from frame_selector.sharpness import (
    fft_score,
    laplacian_score,
    score_torso_sharpness,
    tenengrad_score,
)


# ---------------------------------------------------------------------------
# Fixtures: synthetic sharp vs blurry images
# ---------------------------------------------------------------------------

@pytest.fixture
def sharp_gray():
    img = np.zeros((200, 200), dtype=np.uint8)
    img[::4, :] = 255  # high-frequency horizontal lines
    return img


@pytest.fixture
def blur_gray(sharp_gray):
    blurred = cv2.GaussianBlur(sharp_gray, (21, 21), 0)
    return blurred


@pytest.fixture
def sharp_bgr(sharp_gray):
    return cv2.cvtColor(sharp_gray, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# Per-method: sharp must score higher than blurry
# ---------------------------------------------------------------------------

def test_laplacian_sharp_beats_blur(sharp_gray, blur_gray):
    assert laplacian_score(sharp_gray) > laplacian_score(blur_gray)


def test_tenengrad_sharp_beats_blur(sharp_gray, blur_gray):
    assert tenengrad_score(sharp_gray) > tenengrad_score(blur_gray)


def test_fft_sharp_beats_blur(sharp_gray, blur_gray):
    assert fft_score(sharp_gray) > fft_score(blur_gray)


@pytest.mark.parametrize("method", ["laplacian", "tenengrad", "fft"])
def test_all_methods_non_negative(sharp_gray, method):
    from frame_selector.sharpness import SCORERS
    assert SCORERS[method](sharp_gray) >= 0.0


# ---------------------------------------------------------------------------
# score_torso_sharpness
# ---------------------------------------------------------------------------

def test_score_torso_returns_float(sharp_bgr):
    score = score_torso_sharpness(sharp_bgr, [(10, 10, 90, 190)], method='tenengrad')
    assert isinstance(score, float)
    assert score >= 0.0


def test_score_torso_empty_boxes_returns_zero(sharp_bgr):
    score = score_torso_sharpness(sharp_bgr, [], method='tenengrad')
    assert score == 0.0


def test_score_torso_sharp_beats_blur(sharp_bgr):
    blur_bgr = cv2.GaussianBlur(sharp_bgr, (21, 21), 0)
    bbox = (0, 0, 200, 200)
    s_sharp = score_torso_sharpness(sharp_bgr, [bbox], method='tenengrad')
    s_blur  = score_torso_sharpness(blur_bgr,  [bbox], method='tenengrad')
    assert s_sharp > s_blur


def test_score_torso_out_of_bounds_bbox(sharp_bgr):
    # bbox larger than frame should not crash
    score = score_torso_sharpness(sharp_bgr, [(-10, -10, 500, 500)], method='tenengrad')
    assert isinstance(score, float)


@pytest.mark.parametrize("method", ["laplacian", "tenengrad", "fft"])
def test_all_methods_via_torso_scorer(sharp_bgr, method):
    score = score_torso_sharpness(sharp_bgr, [(0, 0, 200, 200)], method=method)
    assert score >= 0.0
