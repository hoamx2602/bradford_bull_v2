"""Stage 1 — ingest: validate the upload and read video metadata."""
from __future__ import annotations

from pathlib import Path

import cv2

from app.config import get_settings
from app.pipeline.datatypes import VideoMeta


class IngestError(ValueError):
    pass


def validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    allowed = get_settings().allowed_ext_set
    if ext not in allowed:
        raise IngestError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(allowed))}"
        )


def probe(video_path: Path) -> VideoMeta:
    """Read duration/fps/resolution with OpenCV (no ffprobe dependency)."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise IngestError(f"Could not open video: {video_path.name}")
    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        cap.release()

    if fps <= 0:
        fps = 25.0  # sane default for broken headers
    duration = frame_count / fps if frame_count > 0 else 0.0
    if duration <= 0:
        raise IngestError("Video appears to have zero duration or is corrupt.")

    return VideoMeta(
        duration_seconds=round(duration, 3),
        fps=round(fps, 3),
        width=width,
        height=height,
        frame_count=frame_count,
    )
