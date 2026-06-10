"""Annotated preview video.

Goal: a preview that looks like the *original* uploaded video — full frame rate,
boxes glued to the logos on every frame. Like the reference YOLO notebook
(`model.predict(source=video, save=True, stream=True)`), we run detection on
EVERY frame for the preview, rather than sampling. That's what makes it smooth.

This is deliberately separate from the analytics pass (which samples at
SAMPLE_FPS for cheap EMV/exposure): the preview is capped at `max_frames` so a
long match doesn't trigger full-fps inference over hours of footage. Detection
here can run at a smaller `detect_imgsz` for speed since boxes don't need 1280px
precision.

'avc1' (H.264) is browser-friendly; falls back to mp4v if a build lacks it.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import cv2

from app.pipeline.colors import brand_bgr
from app.pipeline.datatypes import Detection

log = logging.getLogger("app.pipeline")

# detect_fn(frame, t, imgsz) -> detections in that frame
DetectFn = Callable[[object, float, int], list[Detection]]


def _open_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
    for codec in ("avc1", "mp4v"):
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if writer.isOpened():
            if codec != "avc1":
                log.warning("preview: H.264 unavailable, using %s (may not play in all browsers)", codec)
            return writer
    log.error("preview: no usable video codec; preview skipped")
    return None


def _draw(img, dets: list[Detection], scale: float) -> None:
    for d in dets:
        x1, y1, x2, y2 = (int(v * scale) for v in d.xyxy)
        color = brand_bgr(d.brand_key)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{d.brand_name} {d.conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(img, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)


def render_preview(
    video_path: Path,
    fps: float,
    width: int,
    height: int,
    detect_fn: DetectFn,
    out_path: Path,
    *,
    max_width: int,
    max_frames: int,
    detect_imgsz: int,
) -> tuple[Path | None, list[Detection]]:
    """Detect + draw on every frame at native fps. Returns (path, all detections).

    The returned detections (with timestamps) drive the per-brand timeline so it
    matches the boxes exactly.
    """
    if fps <= 0 or width <= 0 or height <= 0:
        return None, []

    scale = min(1.0, max_width / width)
    ow, oh = int(round(width * scale)), int(round(height * scale))
    ow -= ow % 2  # H.264 wants even dimensions
    oh -= oh % 2
    size = (max(2, ow), max(2, oh))

    writer = _open_writer(out_path, max(1.0, fps), size)
    if writer is None:
        return None, []

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        writer.release()
        return None, []

    all_dets: list[Detection] = []
    written = 0
    try:
        i = 0
        while written < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            t = i / fps
            i += 1

            dets = detect_fn(frame, t, detect_imgsz)
            all_dets.extend(dets)

            img = cv2.resize(frame, size) if scale != 1.0 else frame
            _draw(img, dets, scale)
            writer.write(img)
            written += 1
    finally:
        cap.release()
        writer.release()

    if written == 0:
        out_path.unlink(missing_ok=True)
        return None, []
    return out_path, all_dets
