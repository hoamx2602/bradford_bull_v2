import cv2
import numpy as np

SHIRT_TOP    = 0.15   # skip head (top 15% of bbox)
SHIRT_BOTTOM = 0.40   # stop before shorts (bottom 60% of bbox)


def get_shirt_color(frame_rgb: np.ndarray, box: tuple) -> np.ndarray | None:
    """
    Crop the shirt/chest region, remove grass-green pixels,
    return median Lab colour [L, a, b] as float32 (3,) array.
    Returns None if the crop is too small or fully green.
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    h = y2 - y1

    sy1 = y1 + int(SHIRT_TOP    * h)
    sy2 = y1 + int(SHIRT_BOTTOM * h)
    if sy2 <= sy1 + 4:
        return None

    crop = frame_rgb[sy1:sy2, x1:x2]
    if crop.size == 0:
        return None

    # Remove grass-green pixels (H in [30,90] OpenCV scale, S > 40)
    hsv        = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    green_mask = (
        (hsv[:, :, 0] >= 30) & (hsv[:, :, 0] <= 90) &
        (hsv[:, :, 1] > 40)
    )
    lab = cv2.cvtColor(crop, cv2.COLOR_RGB2LAB).astype(np.float32)
    px  = lab.reshape(-1, 3)
    keep = ~green_mask.flatten()
    px  = px[keep] if keep.sum() >= 10 else px
    if len(px) == 0:
        return None

    return np.median(px, axis=0)   # [L, a, b]


def lab_to_rgb(lab_vec: np.ndarray) -> tuple:
    """Convert a Lab triplet (OpenCV scale 0-255) to an RGB tuple for display."""
    arr = np.array([[[int(lab_vec[0]), int(lab_vec[1]), int(lab_vec[2])]]], dtype=np.uint8)
    rgb = cv2.cvtColor(arr, cv2.COLOR_LAB2RGB)
    return tuple(int(v) for v in rgb[0, 0])
