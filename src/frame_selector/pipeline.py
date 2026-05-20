import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
from tqdm.auto import tqdm

from .color_filter import grass_ratio, classify_bbox
from .dedup import compute_phash, Deduplicator
from .person_detect import PersonDetector
from .sharpness import score_torso_sharpness


@dataclass
class Config:
    # Sampling
    sample_fps_override: float | None = None

    # Overlay mask
    mask_n_samples: int = 300
    mask_std_thr: float = 8.0

    # Person detection
    yolo_weights: str = 'yolov8n.pt'
    yolo_conf: float = 0.35
    min_bbox_h: float = 0.08
    min_persons: int = 2

    # Target filter
    min_target_players: int = 1
    max_target_h_req: float = 0.18
    jersey_match_thr: float = 0.28
    close_up_h: float = 0.40

    # Sharpness
    sharpness_method: str = 'tenengrad'

    # Composite weights
    w_sharp: float = 0.7
    w_ntarget: float = 1.0
    w_tgt_h: float = 8.0
    w_crowd: float = 2.0
    w_closeup: float = 3.0

    # Dedup
    phash_ham_thr: int = 10
    temporal_window_s: float = 2.0

    # Output
    target_k: int = 250
    min_output: int = 150

    # Debug
    max_frames_debug: int | None = None


@dataclass
class FrameScore:
    frame_idx: int
    time_s: float
    composite: float
    sharp: float
    n_target: int
    n_other: int
    avg_target_h: float
    max_target_h: float
    is_closeup: bool
    crowd_score: float
    grass_ratio: float
    target_boxes: list
    other_boxes: list
    phash: str = ''
    source_video: str = ''

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Overlay mask builder
# ---------------------------------------------------------------------------

def build_overlay_mask(
    video_path: Path,
    n_samples: int = 300,
    std_thr: float = 8.0,
) -> np.ndarray:
    """Build a static-overlay mask by finding low-std pixels across time."""
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        raise RuntimeError(f'Cannot read frame count from {video_path}')

    indices = np.linspace(int(total * 0.05), int(total * 0.95), n_samples).astype(int)
    samples = []
    for idx in tqdm(indices, desc=f'mask {video_path.name}', leave=False):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, f = cap.read()
        if not ok:
            continue
        samples.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32))
    cap.release()

    if len(samples) < 30:
        raise RuntimeError('Too few samples to build overlay mask')

    std_map = np.stack(samples, axis=0).std(axis=0)
    mask = (std_map < std_thr).astype(np.uint8) * 255
    k1 = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    k2 = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k2)

    n, lbl, stats, _ = cv2.connectedComponentsWithStats(mask)
    keep = np.zeros_like(mask)
    min_area = int(0.003 * mask.size)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[lbl == i] = 255
    return keep


# ---------------------------------------------------------------------------
# Per-frame scoring
# ---------------------------------------------------------------------------

def score_frame(
    frame_bgr: np.ndarray,
    overlay_mask: np.ndarray,
    target_color: str,
    detector: PersonDetector,
    cfg: Config,
) -> FrameScore | None:
    H, W = frame_bgr.shape[:2]

    # Stage 1: pitch presence
    gr = grass_ratio(frame_bgr, overlay_mask)
    if gr < 0.18 or gr > 0.92:
        return None

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    grass_m = cv2.inRange(hsv, np.array([30, 35, 25]), np.array([90, 255, 230]))
    not_grass_not_overlay = (grass_m == 0) & (overlay_mask == 0)
    crowd_score = float(not_grass_not_overlay[:H // 2, :].mean())
    if crowd_score > 0.85:
        return None

    # Stage 2: person detection
    all_boxes = detector.detect(frame_bgr, cfg.min_bbox_h)
    if len(all_boxes) < cfg.min_persons:
        return None

    # Stage 3: target vs other classification
    target_boxes, other_boxes = [], []
    for bbox in all_boxes:
        if classify_bbox(frame_bgr, bbox, target_color, overlay_mask, cfg.jersey_match_thr):
            target_boxes.append(bbox)
        else:
            other_boxes.append(bbox)
    if len(target_boxes) < cfg.min_target_players:
        return None

    # Stage 4: size gate (reject wide shots where logo is invisible)
    max_target_h = max((b[3] - b[1]) / H for b in target_boxes)
    if max_target_h < cfg.max_target_h_req:
        return None

    # Stage 5: sharpness on jersey torso ROI
    sharp = score_torso_sharpness(frame_bgr, target_boxes, cfg.sharpness_method)

    avg_target_h = float(np.mean([(b[3] - b[1]) / H for b in target_boxes]))
    is_closeup = max_target_h >= cfg.close_up_h
    composite = (
        cfg.w_sharp   * np.log1p(sharp) +
        cfg.w_ntarget * len(target_boxes) +
        cfg.w_tgt_h   * avg_target_h +
        (cfg.w_closeup if is_closeup else 0.0) -
        cfg.w_crowd   * crowd_score
    )

    return FrameScore(
        frame_idx=0,
        time_s=0.0,
        composite=float(composite),
        sharp=float(sharp),
        n_target=len(target_boxes),
        n_other=len(other_boxes),
        avg_target_h=avg_target_h,
        max_target_h=float(max_target_h),
        is_closeup=is_closeup,
        crowd_score=crowd_score,
        grass_ratio=gr,
        target_boxes=[list(b) for b in target_boxes],
        other_boxes=[list(b) for b in other_boxes],
    )


# ---------------------------------------------------------------------------
# Video processing
# ---------------------------------------------------------------------------

def _adaptive_sample_fps(duration_s: float) -> float:
    if duration_s < 1200:   return 2.0   # highlight < 20min
    elif duration_s < 3600: return 1.0   # match 20-60min
    elif duration_s < 7200: return 0.5   # match 1-2h
    else:                   return 0.33  # full match 2h+


def process_video(
    video_path: Path,
    overlay_mask: np.ndarray,
    target_color: str,
    detector: PersonDetector,
    cfg: Config,
    cache_dir: Path | None = None,
) -> list[FrameScore]:
    """Score every sampled frame in video_path. Returns all candidates (pre-dedup)."""
    if cache_dir:
        cache_file = cache_dir / f'{video_path.stem}_candidates.json'
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return [FrameScore(**d) for d in data]

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total / fps
    target_fps = cfg.sample_fps_override or _adaptive_sample_fps(duration_s)
    step = max(1, int(round(fps / target_fps)))
    indices = list(range(0, total, step))
    if cfg.max_frames_debug:
        indices = indices[:cfg.max_frames_debug]

    candidates: list[FrameScore] = []
    for idx in tqdm(indices, desc=video_path.name):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        sc = score_frame(frame, overlay_mask, target_color, detector, cfg)
        if sc is None:
            continue
        sc.frame_idx = int(idx)
        sc.time_s = float(idx) / fps
        sc.phash = str(compute_phash(frame))
        sc.source_video = video_path.name
        candidates.append(sc)
    cap.release()

    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps([c.to_dict() for c in candidates]))

    return candidates


def select_top_k(
    candidates: list[FrameScore],
    k: int,
    ham_thr: int = 10,
    temporal_s: float = 2.0,
) -> list[FrameScore]:
    """Greedy selection by composite score with dedup constraints."""
    import imagehash
    sorted_cands = sorted(candidates, key=lambda c: c.composite, reverse=True)
    chosen: list[FrameScore] = []
    chosen_hashes: list = []
    chosen_times: list[float] = []

    for c in sorted_cands:
        if any(abs(c.time_s - t) < temporal_s for t in chosen_times):
            continue
        h = imagehash.hex_to_hash(c.phash)
        if any((h - prev) < ham_thr for prev in chosen_hashes):
            continue
        chosen.append(c)
        chosen_hashes.append(h)
        chosen_times.append(c.time_s)
        if len(chosen) >= k:
            break

    return sorted(chosen, key=lambda c: c.frame_idx)
