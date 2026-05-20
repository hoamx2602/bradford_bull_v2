import cv2
import imagehash
import numpy as np
from PIL import Image


def compute_phash(frame_bgr: np.ndarray, hash_size: int = 16) -> imagehash.ImageHash:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return imagehash.phash(Image.fromarray(rgb), hash_size=hash_size)


class Deduplicator:
    """Stateful deduplicator: rejects frames too close in time or too visually similar."""

    def __init__(self, ham_threshold: int = 10, temporal_window_s: float = 2.0) -> None:
        self.ham_thr = ham_threshold
        self.temporal_s = temporal_window_s
        self._hashes: list[imagehash.ImageHash] = []
        self._times: list[float] = []

    def is_duplicate(self, frame_bgr: np.ndarray, time_s: float) -> bool:
        if any(abs(time_s - t) < self.temporal_s for t in self._times):
            return True
        h = compute_phash(frame_bgr)
        return any((h - prev) < self.ham_thr for prev in self._hashes)

    def register(self, frame_bgr: np.ndarray, time_s: float) -> None:
        """Call after accepting a frame so future frames are compared against it."""
        self._hashes.append(compute_phash(frame_bgr))
        self._times.append(time_s)

    def reset(self) -> None:
        self._hashes.clear()
        self._times.clear()
