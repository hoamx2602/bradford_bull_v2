import cv2
import numpy as np


def laplacian_score(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def tenengrad_score(gray: np.ndarray) -> float:
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    return float(np.sqrt(gx**2 + gy**2).mean())


def fft_score(gray: np.ndarray) -> float:
    """Ratio of high-frequency energy to total energy. Higher = sharper."""
    f = np.fft.fft2(gray.astype(np.float32))
    fshift = np.fft.fftshift(f)
    mag = np.abs(fshift)
    h, w = gray.shape
    r = min(h, w) // 8  # low-freq exclusion radius
    # build circular mask in uint8 then apply to float mag
    lf_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(lf_mask, (w // 2, h // 2), r, 255, -1)
    hf_energy = mag[lf_mask == 0].sum()
    return float(hf_energy / (mag.sum() + 1e-9))


SCORERS = {
    'laplacian': laplacian_score,
    'tenengrad': tenengrad_score,
    'fft':       fft_score,
}


def _crop_torso(frame_bgr: np.ndarray, bbox: tuple) -> np.ndarray:
    """Extract torso ROI (y: 15%-70% of bbox height) — where jersey logos live."""
    x1, y1, x2, y2 = bbox
    H, W = frame_bgr.shape[:2]
    bh = y2 - y1
    ty1 = max(0, y1 + int(0.15 * bh))
    ty2 = min(H, y1 + int(0.70 * bh))
    tx1 = max(0, x1)
    tx2 = min(W, x2)
    return frame_bgr[ty1:ty2, tx1:tx2]


def score_torso_sharpness(
    frame_bgr: np.ndarray,
    target_bboxes: list,
    method: str = 'tenengrad',
) -> float:
    """Average sharpness across the torso ROI of each target-player bbox."""
    fn = SCORERS[method]
    scores = []
    for bbox in target_bboxes:
        roi = _crop_torso(frame_bgr, bbox)
        if roi.size == 0:
            continue
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        scores.append(fn(gray))
    return float(np.mean(scores)) if scores else 0.0


def max_torso_sharpness(
    frame_bgr: np.ndarray,
    target_bboxes: list,
    method: str = 'tenengrad',
) -> float:
    """Max sharpness across all target-player torso ROIs.

    Used for filtering: the frame is useful if at least ONE player is sharp,
    even if others are blurry (e.g. player in background is blurry but foreground player is sharp).
    """
    fn = SCORERS[method]
    scores = []
    for bbox in target_bboxes:
        roi = _crop_torso(frame_bgr, bbox)
        if roi.size == 0:
            continue
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        scores.append(fn(gray))
    return float(max(scores)) if scores else 0.0
