"""
Chạy một frame qua toàn bộ pipeline và in ra tất cả intermediate scores.
Giúp debug tại sao 1 frame bị reject hoặc có score thấp.

Usage:
    python scripts/debug_frame.py path/to/frame.jpg --color white
    python scripts/debug_frame.py path/to/frame.jpg --color white --overlay mask.png --no-show
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# allow running from project root without pip install
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.color_filter import classify_bbox, grass_ratio
from frame_selector.dedup import compute_phash
from frame_selector.person_detect import PersonDetector
from frame_selector.sharpness import SCORERS, score_torso_sharpness


def debug_frame(
    frame_path: Path,
    target_color: str,
    overlay_path: Path | None = None,
    show: bool = True,
) -> None:
    frame = cv2.imread(str(frame_path))
    if frame is None:
        print(f'ERROR: cannot read {frame_path}')
        return

    overlay = (cv2.imread(str(overlay_path), cv2.IMREAD_GRAYSCALE)
               if overlay_path else np.zeros(frame.shape[:2], dtype=np.uint8))
    H, W = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    sep = '=' * 58
    print(f'\n{sep}')
    print(f'  Frame : {frame_path.name}')
    print(f'  Size  : {W} x {H}')
    print(f'  Color : {target_color}')
    print(sep)

    # ── Stage 1: pitch presence ──────────────────────────────────────────
    gr = grass_ratio(frame, overlay)
    gate = 0.18 <= gr <= 0.92
    print(f'\n[1] Grass ratio     {gr:.3f}   {"✓ PASS" if gate else "✗ FAIL → REJECTED"}')
    if not gate:
        return

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    grass_m = cv2.inRange(hsv, np.array([30, 35, 25]), np.array([90, 255, 230]))
    crowd_score = float(((grass_m == 0) & (overlay == 0))[:H // 2, :].mean())
    gate = crowd_score <= 0.85
    print(f'[1] Crowd score     {crowd_score:.3f}   {"✓ PASS" if gate else "✗ FAIL → REJECTED"}')
    if not gate:
        return

    # ── Stage 2: person detection ────────────────────────────────────────
    print('\n[2] Person detection …')
    detector = PersonDetector()
    all_boxes = detector.detect(frame, min_height_frac=0.08)
    print(f'    Persons detected : {len(all_boxes)}')
    if len(all_boxes) < 2:
        print('    ✗ FAIL → REJECTED (< 2 persons)')
        return

    # ── Stage 3: color classification ────────────────────────────────────
    target_boxes = [b for b in all_boxes if classify_bbox(frame, b, target_color, overlay)]
    other_boxes  = [b for b in all_boxes if b not in target_boxes]
    gate = len(target_boxes) >= 1
    print(f'\n[3] Target players  {len(target_boxes)} / {len(all_boxes)}   {"✓ PASS" if gate else "✗ FAIL → REJECTED"}')
    if not gate:
        return

    max_h = max((b[3] - b[1]) / H for b in target_boxes)
    gate = max_h >= 0.18
    print(f'    max_target_h    {max_h:.3f}   {"✓ PASS (≥ 0.18)" if gate else "✗ FAIL → REJECTED (wide shot)"}')
    if not gate:
        return

    # ── Stage 4: sharpness comparison ────────────────────────────────────
    print('\n[4] Sharpness scores')
    print(f'    {"Method":<12} {"Full frame":>12}  {"Torso ROI":>10}')
    print(f'    {"─"*38}')
    for name, fn in SCORERS.items():
        full  = fn(gray)
        torso = score_torso_sharpness(frame, target_boxes, method=name)
        print(f'    {name:<12} {full:>12.2f}  {torso:>10.2f}')

    # ── Summary ───────────────────────────────────────────────────────────
    avg_h     = float(sum((b[3] - b[1]) / H for b in target_boxes) / len(target_boxes))
    is_closeup = max_h >= 0.40
    phash_val  = str(compute_phash(frame))

    print(f'\n[Summary]')
    print(f'    avg_target_h  : {avg_h:.3f}')
    print(f'    is_closeup    : {is_closeup}  (>= 0.40)')
    print(f'    pHash         : {phash_val}')
    print(f'    → VERDICT     : PASS — frame is a pipeline candidate\n')

    if not show:
        return

    vis = frame.copy()
    for x1, y1, x2, y2 in target_boxes:
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
        cv2.putText(vis, 'TARGET', (x1, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
    for x1, y1, x2, y2 in other_boxes:
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
    scale = min(1.0, 1280 / W)
    vis_small = cv2.resize(vis, (int(W * scale), int(H * scale)))
    cv2.imshow('debug — green=target  red=other  (any key to close)', vis_small)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('frame', type=Path, help='Path to the .jpg frame to debug')
    ap.add_argument('--color', default='white',
                    help='Target jersey color (default: white)')
    ap.add_argument('--overlay', type=Path, default=None,
                    help='Path to overlay mask .png for this video')
    ap.add_argument('--no-show', action='store_true',
                    help='Skip the OpenCV visualization window')
    args = ap.parse_args()
    debug_frame(args.frame, args.color, args.overlay, show=not args.no_show)
