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
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import cv2

from app.config import display_name
from app.pipeline.colors import brand_bgr
from app.pipeline.datatypes import Detection

log = logging.getLogger("app.pipeline")

# detect_fn(frame, t, imgsz) -> detections in that frame
DetectFn = Callable[[object, float, int], list[Detection]]


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    aa = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    ab = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    return inter / (aa + ab - inter + 1e-9)


class _PreviewStabilizer:
    """Temporal smoother for the full-fps preview.

    The preview detects per frame, so RF-DETR's low-confidence boxes blink on/off
    and occasionally flip brand between frames. This tracks boxes by IoU across
    frames and:
      * votes each box's brand over its life (stops label flipping),
      * holds ("coasts") a box for `coast` frames after its detection drops
        (stops blinking), and
      * waits `min_hits` frames before drawing a new box (suppresses 1-frame
        false positives).
    Backend-agnostic: operates on the Detection list, so YOLO and RF-DETR
    previews both get the same smoothing.
    """

    def __init__(self, iou_thr: float = 0.3, coast: int = 4, min_hits: int = 2):
        self.iou_thr = iou_thr
        self.coast = coast
        self.min_hits = min_hits
        self._tracks: list[dict] = []
        self._next_id = 1

    def step(self, dets: list[Detection], t: float) -> list[Detection]:
        # Greedy IoU match: highest-overlap (detection, track) pairs first.
        pairs = []
        for di, d in enumerate(dets):
            for ti, tr in enumerate(self._tracks):
                iou = _iou(d.xyxy, tr["box"])
                if iou >= self.iou_thr:
                    pairs.append((iou, di, ti))
        pairs.sort(reverse=True)
        md: set[int] = set()
        mt: set[int] = set()
        for _, di, ti in pairs:
            if di in md or ti in mt:
                continue
            d, tr = dets[di], self._tracks[ti]
            tr["box"] = d.xyxy
            tr["missed"] = 0
            tr["hits"] += 1
            tr["votes"][d.brand_key] += 1
            tr["last"] = d
            md.add(di)
            mt.add(ti)
        # Age unmatched tracks; evict once past the coast window.
        survivors = []
        for ti, tr in enumerate(self._tracks):
            if ti not in mt:
                tr["missed"] += 1
                if tr["missed"] > self.coast:
                    continue
            survivors.append(tr)
        self._tracks = survivors
        # New tracks for unmatched detections.
        for di, d in enumerate(dets):
            if di not in md:
                self._tracks.append({"id": self._next_id, "box": d.xyxy, "missed": 0,
                                     "hits": 1, "votes": Counter({d.brand_key: 1}), "last": d})
                self._next_id += 1
        # Emit confirmed tracks (incl. coasted ones) with the voted brand.
        out: list[Detection] = []
        for tr in self._tracks:
            if tr["hits"] < self.min_hits:
                continue
            brand = tr["votes"].most_common(1)[0][0]
            out.append(replace(tr["last"], t=t, xyxy=tr["box"],
                               brand_key=brand, brand_name=display_name(brand),
                               track_id=tr["id"]))
        return out


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
    stabilize: bool = False,
    coast: int = 4,
    min_hits: int = 2,
) -> tuple[Path | None, list[Detection]]:
    """Detect + draw on every frame at native fps. Returns (path, all detections).

    The returned detections (with timestamps) drive the per-brand timeline so it
    matches the boxes exactly. When `stabilize` is set, boxes are temporally
    smoothed (tracked + brand-voted + coasted) so they don't flicker.
    """
    if fps <= 0 or width <= 0 or height <= 0:
        return None, []

    stab = _PreviewStabilizer(coast=coast, min_hits=min_hits) if stabilize else None

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
            if stab is not None:
                dets = stab.step(dets, t)
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
