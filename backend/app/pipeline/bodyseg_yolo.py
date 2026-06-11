"""Body-part segmentation overlay — YOLO11-seg + pose engine (MPS/GPU friendly).

Unlike DensePose (CPU-only on Mac), this runs entirely in torch so it uses Apple
MPS / CUDA and is fast enough to segment EVERY frame → a smooth overlay that
follows motion. Per frame:

  1. YOLO11-seg  → person instance masks (pixel silhouettes)
  2. YOLO11-pose → 17 keypoints per person
  3. match mask↔pose by box IoU, then label each mask pixel by the nearest
     skeleton "bone" → one of the 8 body-part groups (same colours as DensePose).

Part boundaries are skeleton-derived (not pixel-perfect like DensePose) but it's
multi-person, fast, and smooth.
"""
from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from app.pipeline.bodyseg import GROUP_COLOR_RGB, GROUP_LABEL

log = logging.getLogger("app.pipeline")

_GROUP_BGR = {g: np.array(rgb[::-1], dtype=np.uint8) for g, rgb in GROUP_COLOR_RGB.items()}

# COCO-17 keypoint indices
NOSE = 0
L_EYE, R_EYE, L_EAR, R_EAR = 1, 2, 3, 4
L_SHO, R_SHO, L_ELB, R_ELB, L_WRI, R_WRI = 5, 6, 7, 8, 9, 10
L_HIP, R_HIP, L_KNE, R_KNE, L_ANK, R_ANK = 11, 12, 13, 14, 15, 16
KP_CONF = 0.3


def _open_writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter | None:
    for codec in ("avc1", "mp4v"):
        w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if w.isOpened():
            if codec != "avc1":
                log.warning("bodyseg: H.264 unavailable, using %s", codec)
            return w
    return None


def _kp(kpts, idx):
    x, y, c = kpts[idx]
    return np.array([x, y], dtype=np.float32) if c >= KP_CONF else None


def _bones(kpts) -> list[tuple[np.ndarray, np.ndarray, str]]:
    """Skeleton segments (a, b, group) from one person's keypoints."""
    out: list[tuple[np.ndarray, np.ndarray, str]] = []

    def seg(i, j, g):
        a, b = _kp(kpts, i), _kp(kpts, j)
        if a is not None and b is not None:
            out.append((a, b, g))

    def pt(i, g):  # degenerate segment = a point
        a = _kp(kpts, i)
        if a is not None:
            out.append((a, a, g))

    # Head: centroid of available face points
    face = [p for p in (_kp(kpts, NOSE), _kp(kpts, L_EYE), _kp(kpts, R_EYE),
                         _kp(kpts, L_EAR), _kp(kpts, R_EAR)) if p is not None]
    if face:
        h = np.mean(face, axis=0)
        out.append((h, h, "head"))
    # Torso: spine line shoulder-centre → hip-centre. Hips are often missing
    # (occluded / cropped); when they are, estimate the hip downward from the
    # shoulders so torso pixels don't get misassigned to head/arms.
    l_sho, r_sho = _kp(kpts, L_SHO), _kp(kpts, R_SHO)
    sho = [p for p in (l_sho, r_sho) if p is not None]
    hip = [p for p in (_kp(kpts, L_HIP), _kp(kpts, R_HIP)) if p is not None]
    if sho:
        sho_c = np.mean(sho, axis=0)
        if hip:
            hip_c = np.mean(hip, axis=0)
        else:
            # torso length ≈ 1.8× shoulder width (fallback to head distance)
            if l_sho is not None and r_sho is not None:
                tlen = np.linalg.norm(l_sho - r_sho) * 1.8
            elif face:
                tlen = np.linalg.norm(sho_c - h) * 2.0
            else:
                tlen = 60.0
            hip_c = sho_c + np.array([0.0, max(20.0, tlen)], dtype=np.float32)
        out.append((sho_c, hip_c, "torso"))
    # Arms
    seg(L_SHO, L_ELB, "upper_arm"); seg(R_SHO, R_ELB, "upper_arm")
    seg(L_ELB, L_WRI, "lower_arm"); seg(R_ELB, R_WRI, "lower_arm")
    pt(L_WRI, "hand"); pt(R_WRI, "hand")
    # Legs
    seg(L_HIP, L_KNE, "upper_leg"); seg(R_HIP, R_KNE, "upper_leg")
    seg(L_KNE, L_ANK, "lower_leg"); seg(R_KNE, R_ANK, "lower_leg")
    pt(L_ANK, "foot"); pt(R_ANK, "foot")
    return out


def _pt_seg_dist(pts: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    L2 = float(ab.dot(ab))
    if L2 < 1e-6:
        return np.linalg.norm(pts - a, axis=1)
    t = np.clip((pts - a) @ ab / L2, 0.0, 1.0)
    proj = a + t[:, None] * ab
    return np.linalg.norm(pts - proj, axis=1)


def _iou(b1, b2) -> float:
    xa, ya = max(b1[0], b2[0]), max(b1[1], b2[1])
    xb, yb = min(b1[2], b2[2]), min(b1[3], b2[3])
    iw, ih = max(0, xb - xa), max(0, yb - ya)
    inter = iw * ih
    if inter == 0:
        return 0.0
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    return inter / (a1 + a2 - inter + 1e-6)


def _segment_frame(img, seg_model, pose_model, device, imgsz, conf, counts):
    """Return BGR overlay (0 where no person) for one frame at img's size."""
    h, w = img.shape[:2]
    overlay = np.zeros((h, w, 3), dtype=np.uint8)

    seg_res = seg_model.predict(img, imgsz=imgsz, conf=conf, classes=[0],
                                device=device, retina_masks=True, verbose=False)
    if not seg_res or seg_res[0].masks is None:
        return overlay
    masks = seg_res[0].masks.data.cpu().numpy()          # (N, h, w) in img size
    seg_boxes = seg_res[0].boxes.xyxy.cpu().numpy()

    pose_res = pose_model.predict(img, imgsz=imgsz, conf=conf, device=device, verbose=False)
    pose_kp = (pose_res[0].keypoints.data.cpu().numpy()
               if pose_res and pose_res[0].keypoints is not None else np.empty((0, 17, 3)))
    pose_boxes = (pose_res[0].boxes.xyxy.cpu().numpy()
                  if pose_res and pose_res[0].boxes is not None else np.empty((0, 4)))

    for mi in range(masks.shape[0]):
        mask = masks[mi] > 0.5
        ys, xs = np.where(mask)
        if len(xs) == 0:
            continue
        # match this mask to the best-overlapping pose person
        best_j, best_iou = -1, 0.2
        for pj in range(pose_boxes.shape[0]):
            i = _iou(seg_boxes[mi], pose_boxes[pj])
            if i > best_iou:
                best_iou, best_j = i, pj

        pts = np.stack([xs, ys], axis=1).astype(np.float32)
        bones = _bones(pose_kp[best_j]) if best_j >= 0 else []
        if not bones:
            overlay[ys, xs] = _GROUP_BGR["torso"]    # no pose → flat silhouette
            counts["torso"] = counts.get("torso", 0) + len(xs)
            continue
        D = np.stack([_pt_seg_dist(pts, a, b) for a, b, _ in bones])  # (B, P)
        best = D.argmin(0)
        for bi, (_, _, g) in enumerate(bones):
            sel = best == bi
            if sel.any():
                overlay[ys[sel], xs[sel]] = _GROUP_BGR[g]
                counts[g] = counts.get(g, 0) + int(sel.sum())
    return overlay


def render_bodyseg_yolo_video(
    video_path: Path, seg_model, pose_model, device, src_fps: float,
    width: int, height: int, out_path: Path, *, max_frames: int, max_width: int,
    alpha: float, imgsz: int, conf: float,
) -> tuple[Path | None, dict[str, float]]:
    if src_fps <= 0 or width <= 0 or height <= 0:
        return None, {}

    scale = min(1.0, max_width / width)
    ow, oh = int(round(width * scale)), int(round(height * scale))
    ow -= ow % 2
    oh -= oh % 2
    size = (max(2, ow), max(2, oh))

    writer = _open_writer(out_path, max(1.0, src_fps), size)
    if writer is None:
        return None, {}
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        writer.release()
        return None, {}

    counts: dict[str, int] = {}
    written = 0
    try:
        while written < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            img = cv2.resize(frame, size) if scale != 1.0 else frame.copy()
            overlay = _segment_frame(img, seg_model, pose_model, device, imgsz, conf, counts)
            mask = overlay.any(axis=2, keepdims=True)
            blended = np.where(mask, (img * (1 - alpha) + overlay * alpha).astype(np.uint8), img)
            writer.write(blended)
            written += 1
    finally:
        cap.release()
        writer.release()

    if written == 0:
        out_path.unlink(missing_ok=True)
        return None, {}

    total = sum(counts.values()) or 1
    group_pct = {GROUP_LABEL[g]: round(100 * px / total, 1) for g, px in counts.items()}
    return out_path, group_pct
