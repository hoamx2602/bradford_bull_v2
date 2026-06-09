"""Stage 2 — frame sampling.

Sample uniformly at SAMPLE_FPS. Deliberately NO quality filtering: per
Production-System-Design.MD §3, blurry/wide/action frames are exactly when
sponsors are most visible, and the model learns to discount them via low scores
rather than being pre-filtered out.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import cv2

from app.pipeline.datatypes import VideoMeta


def iter_sampled_frames(
    video_path: Path, meta: VideoMeta, sample_fps: float
) -> Iterator[tuple[float, "cv2.typing.MatLike"]]:
    """Yield (timestamp_seconds, BGR frame) at approximately `sample_fps`.

    We seek by timestamp (CAP_PROP_POS_MSEC-driven index) so the cadence is
    independent of the source fps and robust to variable frame rates.
    """
    sample_fps = max(0.1, sample_fps)
    step = max(1, round(meta.fps / sample_fps))

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video for sampling: {video_path.name}")
    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                t = idx / meta.fps if meta.fps > 0 else 0.0
                yield round(t, 3), frame
            idx += 1
    finally:
        cap.release()


def expected_sample_count(meta: VideoMeta, sample_fps: float) -> int:
    sample_fps = max(0.1, sample_fps)
    step = max(1, round(meta.fps / sample_fps))
    if meta.frame_count > 0:
        return max(1, meta.frame_count // step)
    return max(1, int(meta.duration_seconds * sample_fps))
