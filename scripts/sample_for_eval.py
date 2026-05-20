"""
Extract frames from videos, run the full pipeline, and save passing frames
sorted by sharpness score (ascending) so blur-but-pass frames rise to the top.

Usage:
    python scripts/sample_for_eval.py
    python scripts/sample_for_eval.py --n-frames 150 --out-dir my_eval_frames
    python scripts/sample_for_eval.py --video videos/M01_white_1080p.mp4 --n-frames 80

Output per video:
    eval_frames/<stem>/
        ├── passing/          ← all frames that pass the pipeline (sorted blur→sharp)
        │   ├── 001_t=0042s_sharp=12.3_<idx>.jpg   ← low sharp = suspicious blur
        │   └── ...
        └── passing_scores.csv
"""
import argparse
import csv
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.color_filter import COLOR_PRESETS, classify_bbox, grass_ratio
from frame_selector.person_detect import PersonDetector
from frame_selector.sharpness import score_torso_sharpness


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_color(filename: str) -> str:
    name = Path(filename).stem.lower()
    m = re.match(r'^m\d+_([a-z]+)_', name)
    if m and m.group(1) in COLOR_PRESETS:
        return m.group(1)
    for c in COLOR_PRESETS:
        if c in name:
            return c
    raise ValueError(
        f'Cannot parse color from "{filename}". '
        f'Rename to M01_white_1080p.mp4 or pass --color explicitly.'
    )


def burn_label(img: np.ndarray, text: str, sharp: float) -> np.ndarray:
    """Overlay score text and sharpness bar onto the image."""
    vis = img.copy()
    h, w = vis.shape[:2]

    # background strip
    cv2.rectangle(vis, (0, 0), (w, 36), (0, 0, 0), -1)
    cv2.putText(vis, text, (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 1, cv2.LINE_AA)

    # sharpness bar (maps 0–300 tenengrad to bar width)
    bar_w = int(min(1.0, sharp / 300.0) * (w - 16))
    color = (0, 80, 255) if sharp < 30 else (0, 200, 100) if sharp > 80 else (0, 200, 255)
    cv2.rectangle(vis, (8, 28), (8 + bar_w, 34), color, -1)
    return vis


def sample_frames(
    video_path: Path,
    n_frames: int,
    detector: PersonDetector,
    target_color: str,
    out_dir: Path,
    sharpness_method: str = 'tenengrad',
    display_scale: float = 0.5,
) -> list[dict]:
    cap = cv2.VideoCapture(str(video_path))
    fps  = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        raise RuntimeError(f'Cannot read frame count from {video_path}')

    # uniform sample across 5%–95% of the video
    indices = np.linspace(int(total * 0.05), int(total * 0.95), n_frames).astype(int)

    passing_dir = out_dir / 'passing'
    passing_dir.mkdir(parents=True, exist_ok=True)

    passed: list[dict] = []
    H_frame = W_frame = None

    for idx in tqdm(indices, desc=f'{video_path.name} → scoring'):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        if H_frame is None:
            H_frame, W_frame = frame.shape[:2]

        H, W = frame.shape[:2]
        time_s = idx / fps

        # ── Stage 1: grass gate ──────────────────────────────────────────
        gr = grass_ratio(frame)
        if gr < 0.18 or gr > 0.92:
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        grass_m = cv2.inRange(hsv, np.array([30, 35, 25]), np.array([90, 255, 230]))
        crowd = float(((grass_m == 0))[:H // 2, :].mean())
        if crowd > 0.85:
            continue

        # ── Stage 2: YOLO detection ──────────────────────────────────────
        all_boxes = detector.detect(frame, min_height_frac=0.08)
        if len(all_boxes) < 2:
            continue

        # ── Stage 3: target color ────────────────────────────────────────
        target_boxes = [b for b in all_boxes if classify_bbox(frame, b, target_color)]
        other_boxes  = [b for b in all_boxes if b not in target_boxes]
        if not target_boxes:
            continue
        max_h = max((b[3] - b[1]) / H for b in target_boxes)
        if max_h < 0.18:
            continue

        # ── Stage 4: sharpness ───────────────────────────────────────────
        sharp = score_torso_sharpness(frame, target_boxes, method=sharpness_method)
        is_closeup = max_h >= 0.40
        mm, ss = divmod(int(time_s), 60)

        record = dict(
            idx=int(idx),
            time_s=round(time_s, 2),
            sharp=round(sharp, 2),
            n_target=len(target_boxes),
            max_target_h=round(max_h, 3),
            is_closeup=is_closeup,
            grass_ratio=round(gr, 3),
            crowd_score=round(crowd, 3),
            target_boxes=[list(b) for b in target_boxes],
            other_boxes=[list(b) for b in other_boxes],
        )
        passed.append(record)

    cap.release()

    if not passed:
        print(f'  No passing frames found for {video_path.name}')
        return []

    # ── sort ascending by sharpness (blur-but-pass at the top) ──────────
    passed.sort(key=lambda r: r['sharp'])

    # ── re-read and save frames with score overlay ────────────────────────
    print(f'  Saving {len(passed)} passing frames …')
    cap = cv2.VideoCapture(str(video_path))
    for rank, rec in enumerate(tqdm(passed, desc='saving', leave=False), start=1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, rec['idx'])
        ok, frame = cap.read()
        if not ok:
            continue
        H, W = frame.shape[:2]

        # draw bboxes
        vis = frame.copy()
        for x1, y1, x2, y2 in rec['target_boxes']:
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
        for x1, y1, x2, y2 in rec['other_boxes']:
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)

        t = rec['time_s']
        mm, ss = divmod(int(t), 60)
        label = (f'#{rank:03d}  t={mm:02d}:{ss:02d}  sharp={rec["sharp"]:.1f}'
                 f'  max_h={rec["max_target_h"]:.2f}  {"CLOSE-UP" if rec["is_closeup"] else ""}')
        vis = burn_label(vis, label, rec['sharp'])

        # save at display_scale (full-res is too heavy to open 150 images)
        small = cv2.resize(vis, (int(W * display_scale), int(H * display_scale)))
        fname = (f'{rank:03d}_t={mm:02d}{ss:02d}s'
                 f'_sharp={rec["sharp"]:.1f}'
                 f'_f{rec["idx"]:07d}.jpg')
        cv2.imwrite(str(passing_dir / fname), small, [cv2.IMWRITE_JPEG_QUALITY, 88])
        rec['saved_as'] = fname
    cap.release()

    # ── write CSV ────────────────────────────────────────────────────────
    csv_path = out_dir / 'passing_scores.csv'
    with open(csv_path, 'w', newline='') as f:
        keys = ['saved_as', 'idx', 'time_s', 'sharp', 'n_target',
                'max_target_h', 'is_closeup', 'grass_ratio', 'crowd_score']
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore')
        w.writeheader()
        w.writerows(passed)

    # ── print distribution summary ────────────────────────────────────────
    sharps = [r['sharp'] for r in passed]
    p25, p50, p75 = np.percentile(sharps, [25, 50, 75])
    blur_count = sum(1 for s in sharps if s < 30)
    print(f'\n  Sharpness distribution (n={len(passed)}):')
    print(f'    min={min(sharps):.1f}  p25={p25:.1f}  median={p50:.1f}'
          f'  p75={p75:.1f}  max={max(sharps):.1f}')
    print(f'    Suspicious blur (sharp < 30): {blur_count} frames')
    print(f'    → Low-sharp frames are ranked #001 … look at those first')
    print(f'    → {passing_dir}')
    print(f'    → {csv_path}')

    return passed


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, default=None,
                    help='Single video path. Omit to process all videos/ *.mp4')
    ap.add_argument('--color', default=None,
                    help='Target jersey color. Auto-parsed from filename if omitted.')
    ap.add_argument('--n-frames', type=int, default=120,
                    help='Number of frames to sample per video (default 120)')
    ap.add_argument('--out-dir', type=Path, default=Path('eval_frames'),
                    help='Root output directory (default: eval_frames/)')
    ap.add_argument('--scale', type=float, default=0.5,
                    help='Saved image scale factor (default 0.5)')
    ap.add_argument('--method', default='tenengrad',
                    choices=['laplacian', 'tenengrad', 'fft'],
                    help='Sharpness method (default: tenengrad)')
    args = ap.parse_args()

    video_dir = Path('videos')
    if args.video:
        videos = [args.video]
    else:
        videos = sorted(video_dir.glob('*.mp4'))

    if not videos:
        print('No videos found. Pass --video or put .mp4 files in videos/')
        return

    print(f'Loading YOLO detector …')
    detector = PersonDetector()

    for vpath in videos:
        color = args.color or parse_color(vpath.name)
        out_dir = args.out_dir / vpath.stem
        print(f'\n{"─"*60}')
        print(f'Video : {vpath.name}')
        print(f'Color : {color}  |  Sampling {args.n_frames} frames')
        sample_frames(
            video_path=vpath,
            n_frames=args.n_frames,
            detector=detector,
            target_color=color,
            out_dir=out_dir,
            sharpness_method=args.method,
            display_scale=args.scale,
        )

    print(f'\nDone. Open eval_frames/ and look at #001 … for suspicious blur.')
    print('Next step: python eval/label_frames.py --frames-dir eval_frames/ --output labels.csv')


if __name__ == '__main__':
    main()
