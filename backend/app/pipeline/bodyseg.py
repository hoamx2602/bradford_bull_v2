"""Body-part segmentation overlay video (DensePose).

Runs DensePose (detectron2) on sampled frames, colours each player's pixels by
body-part group, blends the overlay onto the frame and writes an MP4 for the
dashboard's body-segmentation view. Mirrors scene-solution/Body_Part_Visibility.ipynb.

DensePose is heavy and has no Apple-MPS path (runs CPU on Mac, CUDA in prod), so
this is sampled (BODYSEG_FPS) and capped (BODYSEG_MAX_FRAMES). The whole stage is
optional: the orchestrator skips it when detectron2/densepose aren't importable.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("app.pipeline")

# DensePose fine-part id (1..24) -> body-part group
GROUP_OF: dict[int, str] = {
    1: "torso", 2: "torso", 3: "hand", 4: "hand", 5: "foot", 6: "foot",
    7: "upper_leg", 8: "upper_leg", 9: "upper_leg", 10: "upper_leg",
    11: "lower_leg", 12: "lower_leg", 13: "lower_leg", 14: "lower_leg",
    15: "upper_arm", 16: "upper_arm", 17: "upper_arm", 18: "upper_arm",
    19: "lower_arm", 20: "lower_arm", 21: "lower_arm", 22: "lower_arm",
    23: "head", 24: "head",
}

GROUP_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "head": (255, 99, 71), "torso": (60, 180, 75), "upper_arm": (0, 130, 200),
    "lower_arm": (145, 30, 180), "hand": (245, 130, 48), "upper_leg": (255, 225, 25),
    "lower_leg": (70, 240, 240), "foot": (240, 50, 230),
}
GROUP_LABEL = {
    "head": "Head", "torso": "Torso", "upper_arm": "Upper Arm", "lower_arm": "Lower Arm",
    "hand": "Hands", "upper_leg": "Upper Leg", "lower_leg": "Lower Leg", "foot": "Feet",
}
# BGR lookup per fine-part id (for fast assignment)
_PART_BGR = {
    pid: GROUP_COLOR_RGB[g][::-1] for pid, g in GROUP_OF.items()
}


def _open_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
    for codec in ("avc1", "mp4v"):
        w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if w.isOpened():
            if codec != "avc1":
                log.warning("bodyseg: H.264 unavailable, using %s", codec)
            return w
    return None


def _segment_frame(frame_bgr, predictor, counts: np.ndarray) -> np.ndarray:
    """Return a BGR overlay (0 where no person) for one frame."""
    import torch

    h, w = frame_bgr.shape[:2]
    overlay = np.zeros((h, w, 3), dtype=np.uint8)
    with torch.no_grad():
        outputs = predictor(frame_bgr)
    inst = outputs["instances"].to("cpu")
    if not inst.has("pred_densepose") or len(inst) == 0:
        return overlay

    dp = inst.pred_densepose
    boxes = inst.pred_boxes.tensor.numpy().astype(int)
    part_labels = dp.fine_segm.argmax(dim=1).numpy()    # (N, h_roi, w_roi)
    fg_masks = dp.coarse_segm.argmax(dim=1).numpy()     # (N, h_roi, w_roi)

    for lmap, fg, box in zip(part_labels, fg_masks, boxes):
        x1, y1 = max(0, box[0]), max(0, box[1])
        x2, y2 = min(w, box[2]), min(h, box[3])
        if x2 <= x1 or y2 <= y1:
            continue
        bw, bh = x2 - x1, y2 - y1
        lr = cv2.resize(lmap.astype(np.uint8), (bw, bh), interpolation=cv2.INTER_NEAREST)
        fr = cv2.resize(fg.astype(np.uint8), (bw, bh), interpolation=cv2.INTER_NEAREST)
        region = overlay[y1:y2, x1:x2]
        for pid in range(1, 25):
            m = (lr == pid) & (fr > 0)
            if m.any():
                region[m] = _PART_BGR[pid]
                counts[pid] += int(m.sum())
    return overlay


def render_bodyseg_video(
    video_path: Path,
    predictor,
    src_fps: float,
    width: int,
    height: int,
    out_path: Path,
    *,
    sample_fps: float,
    max_frames: int,
    max_width: int,
    alpha: float,
) -> tuple[Path | None, dict[str, float]]:
    """Write the segmentation overlay video. Returns (path, group_pct)."""
    if src_fps <= 0 or width <= 0 or height <= 0:
        return None, {}

    scale = min(1.0, max_width / width)
    ow, oh = int(round(width * scale)), int(round(height * scale))
    ow -= ow % 2
    oh -= oh % 2
    size = (max(2, ow), max(2, oh))

    # Write at the video's NATIVE fps so playback is smooth. DensePose is far too
    # slow to run every frame on CPU, so we segment every `step` frames and HOLD
    # the overlay for the frames in between (it refreshes `sample_fps` times/sec).
    writer = _open_writer(out_path, max(1.0, src_fps), size)
    if writer is None:
        return None, {}

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        writer.release()
        return None, {}

    step = max(1, round(src_fps / max(0.1, sample_fps)))
    counts = np.zeros(25, dtype=np.int64)
    last_overlay = None  # full-res held overlay
    idx = written = 0
    try:
        while written < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0 or last_overlay is None:
                last_overlay = _segment_frame(frame, predictor, counts)
            mask = last_overlay.any(axis=2, keepdims=True)
            blended = np.where(
                mask, (frame * (1 - alpha) + last_overlay * alpha).astype(np.uint8), frame
            )
            img = cv2.resize(blended, size) if scale != 1.0 else blended
            writer.write(img)
            written += 1
            idx += 1
    finally:
        cap.release()
        writer.release()

    if written == 0:
        out_path.unlink(missing_ok=True)
        return None, {}

    # Aggregate group percentages over person pixels (diagnostic / future use).
    group_px: dict[str, float] = {}
    for pid in range(1, 25):
        group_px[GROUP_OF[pid]] = group_px.get(GROUP_OF[pid], 0) + int(counts[pid])
    total = sum(group_px.values()) or 1
    group_pct = {GROUP_LABEL[g]: round(100 * px / total, 1) for g, px in group_px.items()}
    return out_path, group_pct
