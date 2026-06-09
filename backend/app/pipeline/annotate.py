"""Annotated preview video.

Goal: a preview that looks like the *original* uploaded video (full frame rate,
same duration), just with detected logo boxes drawn on top.

Detection only runs on sampled frames (SAMPLE_FPS, e.g. 2/s), so to avoid a
choppy 2-fps montage we do a second pass over EVERY frame at native fps and, for
each frame, **interpolate** each logo's box between the two surrounding sampled
detections (matched by ByteTrack id). Boxes therefore glide smoothly with the
player instead of jumping twice a second. Tracks without a match are held.

'avc1' (H.264) is browser-friendly; falls back to mp4v if a build lacks it.
"""
from __future__ import annotations

import bisect
import colorsys
import logging
from pathlib import Path

import cv2

from app.pipeline.datatypes import Detection

log = logging.getLogger("app.pipeline")


def _brand_color(key: str) -> tuple[int, int, int]:
    """Stable vivid BGR colour per brand key."""
    h = (hash(key) % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return (int(b * 255), int(g * 255), int(r * 255))


def _open_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
    for codec in ("avc1", "mp4v"):
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if writer.isOpened():
            if codec != "avc1":
                log.warning("preview: H.264 unavailable, using %s (may not play in all browsers)", codec)
            return writer
    log.error("preview: no usable video codec; preview skipped")
    return None


def _lerp(a: float, b: float, f: float) -> float:
    return a + (b - a) * f


# A box ready to draw: (xyxy, brand_key, brand_name, conf)
_DrawBox = tuple[tuple[float, float, float, float], str, str, float]


def _boxes_at(t: float, t_a: float, dets_a: list[Detection],
              t_b: float | None, dets_b: list[Detection]) -> list[_DrawBox]:
    """Interpolate the boxes visible at time `t` from the bracketing samples."""
    if t_b is None or t_b <= t_a:
        return [(d.xyxy, d.brand_key, d.brand_name, d.conf) for d in dets_a]
    frac = max(0.0, min(1.0, (t - t_a) / (t_b - t_a)))
    b_by_track = {d.track_id: d for d in dets_b if d.track_id != -1}
    out: list[_DrawBox] = []
    for d in dets_a:
        db = b_by_track.get(d.track_id) if d.track_id != -1 else None
        if db is not None:
            box = (
                _lerp(d.xyxy[0], db.xyxy[0], frac), _lerp(d.xyxy[1], db.xyxy[1], frac),
                _lerp(d.xyxy[2], db.xyxy[2], frac), _lerp(d.xyxy[3], db.xyxy[3], frac),
            )
            out.append((box, d.brand_key, d.brand_name, _lerp(d.conf, db.conf, frac)))
        else:
            out.append((d.xyxy, d.brand_key, d.brand_name, d.conf))  # held
    return out


def _draw(img, boxes: list[_DrawBox], scale: float) -> None:
    for xyxy, key, name, conf in boxes:
        x1, y1, x2, y2 = (int(v * scale) for v in xyxy)
        color = _brand_color(key)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = f"{name} {conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(img, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
        cv2.putText(img, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)


def render_preview(
    video_path: Path,
    fps: float,
    width: int,
    height: int,
    frames_data: list[tuple[float, list[Detection]]],
    out_path: Path,
    *,
    max_width: int,
    max_frames: int,
) -> Path | None:
    """Second pass: re-decode every frame at native fps, draw interpolated boxes.

    `frames_data` is one (timestamp, detections) entry per *sampled* frame, in
    order — these bracket the native frames for interpolation.
    """
    if not frames_data or fps <= 0 or width <= 0 or height <= 0:
        return None

    scale = min(1.0, max_width / width)
    ow, oh = int(round(width * scale)), int(round(height * scale))
    ow -= ow % 2  # H.264 wants even dimensions
    oh -= oh % 2
    size = (max(2, ow), max(2, oh))

    writer = _open_writer(out_path, max(1.0, fps), size)
    if writer is None:
        return None

    times = [t for t, _ in frames_data]
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        writer.release()
        return None

    written = 0
    try:
        i = 0
        while written < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            t = i / fps
            i += 1

            k = bisect.bisect_right(times, t) - 1
            boxes: list[_DrawBox] = []
            if k >= 0:
                t_a, dets_a = frames_data[k]
                if k + 1 < len(frames_data):
                    t_b, dets_b = frames_data[k + 1]
                else:
                    t_b, dets_b = None, []
                boxes = _boxes_at(t, t_a, dets_a, t_b, dets_b)

            img = cv2.resize(frame, size) if scale != 1.0 else frame
            _draw(img, boxes, scale)
            writer.write(img)
            written += 1
    finally:
        cap.release()
        writer.release()

    if written == 0:
        out_path.unlink(missing_ok=True)
        return None
    return out_path
