import json
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
from tqdm.auto import tqdm

from .color_filter import grass_ratio, classify_bbox
from .dedup import compute_phash, Deduplicator
from .person_detect import PersonDetector
from .sharpness import score_torso_sharpness, max_torso_sharpness


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

    # Pitch presence gates
    # Data analysis: pure crowd/stands shots (players walking off pitch) have grass_ratio 0.22-0.25.
    # Video Ref Replay frames have grass_ratio 0.26+ (part of inset is pitch) → still pass.
    grass_ratio_min: float = 0.25
    # Data analysis: pure crowd shots reach crowd 0.87+; Video Ref Replay is 0.82.
    # Keep 0.85 to allow replay frames (which the user wants for annotation diversity).
    crowd_score_max: float = 0.85

    # Target filter
    min_target_players: int = 1
    max_target_h_req: float = 0.18
    # Data analysis: true target players have color_match median=0.36, min=0.28 → raise threshold
    jersey_match_thr: float = 0.35
    close_up_h: float = 0.40

    # Sharpness
    sharpness_method: str = 'tenengrad'
    # Data analysis: frames with max_torso_sharp < 15 are not annotatable
    min_torso_sharp: float = 15.0

    # Composite weights — w_sharp now applies to torso sharpness, not global
    w_sharp: float = 0.7
    w_ntarget: float = 1.0
    w_tgt_h: float = 8.0
    w_crowd: float = 2.0
    w_closeup: float = 3.0
    # Penalise frames where player is moving very fast relative to camera
    w_motion: float = 0.015

    # Dedup
    phash_ham_thr: int = 10
    temporal_window_s: float = 2.0

    # Output
    # target_k is a maximum cap; actual k is computed adaptively from video duration.
    # Set to 0 to use fully adaptive mode (recommended).
    target_k: int = 0
    min_output: int = 80
    # Frames per minute target for annotation diversity
    frames_per_minute: float = 10.0
    # Hard cap regardless of video length
    max_output: int = 500

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

    # Stage 1a: pitch presence — grass ratio
    gr = grass_ratio(frame_bgr, overlay_mask)
    if gr < cfg.grass_ratio_min or gr > 0.92:
        return None

    # Stage 1b: crowd and TV overlay detection
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    grass_m = cv2.inRange(hsv, np.array([30, 35, 25]), np.array([90, 255, 230]))
    om = overlay_mask if overlay_mask is not None else np.zeros((H, W), np.uint8)
    not_grass_not_overlay = (grass_m == 0) & (om == 0)
    crowd_score = float(not_grass_not_overlay[:H // 2, :].mean())
    if crowd_score > cfg.crowd_score_max:
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

    # Stage 5: torso sharpness — use MAX across players, not global frame sharpness.
    # Global Tenengrad is suppressed by smooth backgrounds (LED boards, flat grass at night)
    # even when the player's jersey is perfectly readable. Max torso targets the best player.
    sharp_avg = score_torso_sharpness(frame_bgr, target_boxes, cfg.sharpness_method)
    sharp_max = max_torso_sharpness(frame_bgr, target_boxes, cfg.sharpness_method)
    if sharp_max < cfg.min_torso_sharp:
        return None

    avg_target_h = float(np.mean([(b[3] - b[1]) / H for b in target_boxes]))
    is_closeup = max_target_h >= cfg.close_up_h

    # Composite score uses avg torso sharpness (avg across all target players).
    # w_motion penalises high player motion (large inter-frame diff not explained by camera pan).
    # player_motion_excess is computed externally and stored in FrameScore for downstream use;
    # the pipeline doesn't have access to prev_frame here, so we omit that term —
    # it can be applied in post-processing if needed.
    composite = (
        cfg.w_sharp   * np.log1p(sharp_avg) +
        cfg.w_ntarget * len(target_boxes) +
        cfg.w_tgt_h   * avg_target_h +
        (cfg.w_closeup if is_closeup else 0.0) -
        cfg.w_crowd   * crowd_score
    )

    return FrameScore(
        frame_idx=0,
        time_s=0.0,
        composite=float(composite),
        sharp=float(sharp_avg),
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


def adaptive_target_k(duration_s: float, cfg: Config) -> int:
    """Compute how many frames to select based on video length."""
    duration_min = duration_s / 60.0
    k = int(round(duration_min * cfg.frames_per_minute))
    k = max(cfg.min_output, min(cfg.max_output, k))
    # Manual override: if target_k > 0 it acts as a hard cap
    if cfg.target_k > 0:
        k = min(k, cfg.target_k)
    return k


def _size_bucket(max_h: float) -> str:
    if max_h >= 0.50:
        return 'closeup'
    if max_h >= 0.30:
        return 'medium'
    return 'wide'


def select_top_k(
    candidates: list[FrameScore],
    k: int,
    ham_thr: int = 10,
    temporal_s: float = 2.0,
) -> list[FrameScore]:
    """Diversity-aware greedy selection with dedup constraints.

    Two-pass strategy:
      Pass 1 – fill per-bucket quotas (size × player-count buckets) to guarantee variety.
      Pass 2 – fill remaining slots with highest-scoring survivors.
    This ensures a 60-frame highlight reel isn't all close-ups, and a full-match
    output isn't all crowd-free mid-shots.
    """
    import imagehash

    if not candidates:
        return []

    # --- bucket quotas ---
    # Size buckets: closeup / medium / wide  (≈40% / 40% / 20%)
    size_quota = {
        'closeup': max(1, int(k * 0.40)),
        'medium':  max(1, int(k * 0.40)),
        'wide':    max(1, int(k * 0.20)),
    }
    bucket_counts: dict[str, int] = {b: 0 for b in size_quota}

    sorted_cands = sorted(candidates, key=lambda c: c.composite, reverse=True)
    chosen: list[FrameScore] = []
    chosen_hashes: list = []
    chosen_times: list[float] = []
    used_indices: set[int] = set()

    def _try_add(c: FrameScore) -> bool:
        if any(abs(c.time_s - t) < temporal_s for t in chosen_times):
            return False
        h = None
        if c.phash:
            h = imagehash.hex_to_hash(c.phash)
            if any((h - prev) < ham_thr for prev in chosen_hashes):
                return False
        chosen.append(c)
        chosen_times.append(c.time_s)
        used_indices.add(c.frame_idx)
        if h is not None:
            chosen_hashes.append(h)
        return True

    # Pass 1: fill buckets
    for c in sorted_cands:
        if len(chosen) >= k:
            break
        sb = _size_bucket(c.max_target_h)
        if bucket_counts[sb] < size_quota[sb]:
            if _try_add(c):
                bucket_counts[sb] += 1

    # Pass 2: fill remaining slots with any survivors
    for c in sorted_cands:
        if len(chosen) >= k:
            break
        if c.frame_idx in used_indices:
            continue
        _try_add(c)

    return sorted(chosen, key=lambda c: c.frame_idx)


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(
    video_paths: list[Path],
    target_color: str,
    cfg: Config,
    out_dir: Path,
    cache_dir: Path | None = None,
    save_frames: bool = True,
    display_scale: float = 0.5,
) -> dict[str, list[FrameScore]]:
    """Full pipeline: mask → score → adaptive select → save.

    Returns a dict mapping video stem → selected FrameScores.
    """
    from .person_detect import PersonDetector

    detector = PersonDetector(cfg.yolo_weights, cfg.yolo_conf)
    results: dict[str, list[FrameScore]] = {}

    for video_path in video_paths:
        print(f'\n{"─"*60}')
        print(f'Video : {video_path.name}  |  color={target_color}')

        # --- overlay mask ---
        mask = build_overlay_mask(video_path, cfg.mask_n_samples, cfg.mask_std_thr)

        # --- score all sampled frames ---
        candidates = process_video(video_path, mask, target_color, detector, cfg, cache_dir)
        print(f'  Candidates: {len(candidates)}')

        if not candidates:
            results[video_path.stem] = []
            continue

        # --- adaptive k ---
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        duration_s = total / fps
        k = adaptive_target_k(duration_s, cfg)
        duration_min = duration_s / 60.0
        print(f'  Duration: {duration_min:.1f} min  →  target_k={k}')

        # --- diversity-aware selection ---
        chosen = select_top_k(
            candidates, k,
            ham_thr=cfg.phash_ham_thr,
            temporal_s=cfg.temporal_window_s,
        )
        print(f'  Selected: {len(chosen)} frames')

        # --- size bucket summary ---
        buckets: dict[str, int] = {'closeup': 0, 'medium': 0, 'wide': 0}
        for c in chosen:
            buckets[_size_bucket(c.max_target_h)] += 1
        print(f'  Buckets  → close-up: {buckets["closeup"]}  '
              f'medium: {buckets["medium"]}  wide: {buckets["wide"]}')

        results[video_path.stem] = chosen

        if not save_frames:
            continue

        # --- save selected frames as JPEG ---
        video_out = out_dir / video_path.stem
        video_out.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video_path))
        for rank, sc in enumerate(tqdm(chosen, desc='saving', leave=False), start=1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(sc.frame_idx))
            ok, frame = cap.read()
            if not ok:
                continue
            # draw bboxes
            vis = frame.copy()
            for x1, y1, x2, y2 in sc.target_boxes:
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
            for x1, y1, x2, y2 in sc.other_boxes:
                cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
            sb = _size_bucket(sc.max_target_h)
            mm, ss_ = divmod(int(sc.time_s), 60)
            label = (f'#{rank:03d} {mm:02d}:{ss_:02d} '
                     f'sharp={sc.sharp:.1f} {sb} nt={sc.n_target}')
            H, W = vis.shape[:2]
            cv2.rectangle(vis, (0, 0), (W, 32), (0, 0, 0), -1)
            cv2.putText(vis, label, (8, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
            if display_scale != 1.0:
                vis = cv2.resize(vis, (int(W * display_scale), int(H * display_scale)))
            fname = f'{rank:03d}_t{mm:02d}{ss_:02d}_{sb}_s{sc.sharp:.0f}_f{sc.frame_idx:07d}.jpg'
            cv2.imwrite(str(video_out / fname), vis, [cv2.IMWRITE_JPEG_QUALITY, 88])
        cap.release()

        # --- save JSON manifest ---
        manifest = [c.to_dict() for c in chosen]
        (video_out / 'selected.json').write_text(json.dumps(manifest, indent=2))
        print(f'  Saved → {video_out}/')

    return results
