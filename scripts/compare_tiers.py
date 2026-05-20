"""
So sánh frame gốc vs kết quả xử lý của tier hiện tại đang checkout.

Script tự phát hiện tier nào đang available dựa trên branch:
  main                    → chỉ hiện frame gốc (baseline)
  tier1/burst-selection   → burst selection
  tier2/single-image-deblur → NAFNet / Wiener deblur
  tier3/optical-flow-fusion → RAFT optical flow fusion

Usage:
  python scripts/compare_tiers.py \\
      --video videos/M06_black_1080p.mp4 \\
      --frame 5450 \\
      --color black

  # Tier 1: thêm --window (số frame hai bên cửa sổ burst)
  python scripts/compare_tiers.py --video ... --frame 5450 --color black --window 15

  # Tier 2: thêm --deblur
  python scripts/compare_tiers.py --video ... --frame 5450 --color black --deblur

  # Tier 3: thêm --fuse
  python scripts/compare_tiers.py --video ... --frame 5450 --color black --fuse

  # Lưu output thay vì hiện cửa sổ
  python scripts/compare_tiers.py ... --save compare_output/

Kết quả in ra:
  Tier            : tier1/burst-selection
  Original  sharp : 12.5  (tenengrad trên torso ROI)
  Processed sharp : 47.3  (+278%)  ← frame tốt hơn được tìm thấy
  Best frame idx  : 5463  (was 5450)
"""
import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.color_filter import classify_bbox, grass_ratio
from frame_selector.person_detect import PersonDetector
from frame_selector.sharpness import SCORERS, score_torso_sharpness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_branch() -> str:
    try:
        out = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return 'unknown'


def _read_frame(video_path: Path, idx: int) -> np.ndarray | None:
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def _detect_target_boxes(
    frame: np.ndarray,
    target_color: str,
    detector: PersonDetector,
) -> tuple[list, list]:
    all_boxes = detector.detect(frame, min_height_frac=0.08)
    target, other = [], []
    for b in all_boxes:
        (target if classify_bbox(frame, b, target_color) else other).append(b)
    return target, other


def _draw_boxes(frame: np.ndarray, target_boxes: list, other_boxes: list) -> np.ndarray:
    vis = frame.copy()
    for x1, y1, x2, y2 in target_boxes:
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 3)
    for x1, y1, x2, y2 in other_boxes:
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)
    return vis


def _burn_score(img: np.ndarray, label: str, sharp: float) -> np.ndarray:
    vis = img.copy()
    h, w = vis.shape[:2]
    cv2.rectangle(vis, (0, 0), (w, 40), (0, 0, 0), -1)
    cv2.putText(vis, label, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    bar_w = int(min(1.0, sharp / 200.0) * (w - 16))
    color = (0, 80, 255) if sharp < 30 else (0, 200, 255) if sharp < 80 else (0, 200, 100)
    cv2.rectangle(vis, (8, 32), (8 + bar_w, 38), color, -1)
    return vis


def _side_by_side(left: np.ndarray, right: np.ndarray, max_w: int = 1400) -> np.ndarray:
    h = max(left.shape[0], right.shape[0])
    total_w = left.shape[1] + right.shape[1]
    if total_w > max_w:
        scale = max_w / total_w
        left  = cv2.resize(left,  (int(left.shape[1]  * scale), int(left.shape[0]  * scale)))
        right = cv2.resize(right, (int(right.shape[1] * scale), int(right.shape[0] * scale)))
    # pad to same height
    def _pad(img, target_h):
        if img.shape[0] < target_h:
            pad = np.zeros((target_h - img.shape[0], img.shape[1], 3), dtype=np.uint8)
            return np.vstack([img, pad])
        return img
    h = max(left.shape[0], right.shape[0])
    return np.hstack([_pad(left, h), _pad(right, h)])


# ---------------------------------------------------------------------------
# Tier processors
# ---------------------------------------------------------------------------

def _run_tier1(
    video_path: Path, center_idx: int, target_boxes: list, window: int,
) -> tuple[np.ndarray, int, float]:
    from frame_selector.burst import find_sharpest_in_burst, read_frame_at
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    best_idx, best_sharp = find_sharpest_in_burst(
        cap, center_idx, total, target_boxes,
        window_frames=window, method='tenengrad',
    )
    frame = read_frame_at(cap, best_idx)
    cap.release()
    return frame, best_idx, best_sharp


def _run_tier2(frame: np.ndarray, target_boxes: list) -> tuple[np.ndarray, float]:
    from frame_selector.deblur_single import SingleFrameDeblurrer
    deblurrer = SingleFrameDeblurrer(backend='auto')
    out = deblurrer.deblur(frame)
    sharp = score_torso_sharpness(out, target_boxes, method='tenengrad')
    return out, sharp


def _run_tier3(
    video_path: Path, center_idx: int, target_boxes: list, window: int,
) -> tuple[np.ndarray, float]:
    from frame_selector.flow_fusion import TemporalFusion
    cap = cv2.VideoCapture(str(video_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fuser = TemporalFusion(window_frames=window)
    fused = fuser.fuse(cap, center_idx, total)
    cap.release()
    sharp = score_torso_sharpness(fused, target_boxes, method='tenengrad')
    return fused, sharp


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video',  type=Path, required=True)
    ap.add_argument('--frame',  type=int,  required=True, help='Frame index (from passing_scores.csv)')
    ap.add_argument('--color',  default='white', help='Target jersey color')
    ap.add_argument('--window', type=int, default=15,
                    help='Burst / fusion window size (used by tier1 and tier3)')
    ap.add_argument('--deblur', action='store_true', help='Force tier2 deblur mode')
    ap.add_argument('--fuse',   action='store_true', help='Force tier3 fusion mode')
    ap.add_argument('--save',   type=Path, default=None,
                    help='Directory to save output JPEGs instead of showing window')
    ap.add_argument('--no-show', action='store_true', help='Skip OpenCV display')
    args = ap.parse_args()

    branch = _current_branch()
    print(f'\nBranch : {branch}')

    # ── Read original frame ──────────────────────────────────────────────
    orig = _read_frame(args.video, args.frame)
    if orig is None:
        print(f'ERROR: cannot read frame {args.frame} from {args.video}')
        return

    # ── Detect target boxes (used by all tiers for sharpness ROI) ────────
    print('Loading YOLO for bbox detection …')
    detector = PersonDetector()
    target_boxes, other_boxes = _detect_target_boxes(orig, args.color, detector)
    orig_sharp = score_torso_sharpness(orig, target_boxes or [[0, 0, orig.shape[1], orig.shape[0]]])
    print(f'Target boxes : {len(target_boxes)}  |  Original sharp : {orig_sharp:.1f}')

    # ── Detect which tier is available ───────────────────────────────────
    tier_label = 'baseline (main)'
    processed = orig.copy()
    proc_sharp = orig_sharp
    extra_info = ''

    use_tier1 = 'tier1' in branch or (not args.deblur and not args.fuse and 'tier1' in branch)
    use_tier2 = args.deblur or 'tier2' in branch
    use_tier3 = args.fuse   or 'tier3' in branch

    if use_tier3:
        tier_label = 'Tier 3 — RAFT optical flow fusion'
        print(f'\nRunning {tier_label} …')
        try:
            processed, proc_sharp = _run_tier3(
                args.video, args.frame, target_boxes or [[0, 0, orig.shape[1], orig.shape[0]]],
                window=args.window,
            )
        except ImportError as e:
            print(f'  [!] {e}\n  → Make sure you are on tier3/optical-flow-fusion branch')

    elif use_tier2:
        tier_label = 'Tier 2 — NAFNet / Wiener deblur'
        print(f'\nRunning {tier_label} …')
        try:
            processed, proc_sharp = _run_tier2(
                orig, target_boxes or [[0, 0, orig.shape[1], orig.shape[0]]],
            )
        except ImportError as e:
            print(f'  [!] {e}\n  → Make sure you are on tier2/single-image-deblur branch')

    elif 'tier1' in branch or (not args.deblur and not args.fuse):
        if 'tier1' in branch:
            tier_label = 'Tier 1 — temporal burst selection'
            print(f'\nRunning {tier_label} (window=±{args.window}) …')
            try:
                processed, best_idx, proc_sharp = _run_tier1(
                    args.video, args.frame,
                    target_boxes or [[0, 0, orig.shape[1], orig.shape[0]]],
                    window=args.window,
                )
                extra_info = f'  Best frame idx : {best_idx}  (was {args.frame})'
            except ImportError as e:
                print(f'  [!] {e}\n  → Make sure you are on tier1/burst-selection branch')

    # ── Print results ─────────────────────────────────────────────────────
    delta = proc_sharp - orig_sharp
    sign  = '+' if delta >= 0 else ''
    pct   = (delta / max(orig_sharp, 1e-6)) * 100
    print(f'\n{"─"*50}')
    print(f'Tier            : {tier_label}')
    print(f'Original  sharp : {orig_sharp:.1f}')
    print(f'Processed sharp : {proc_sharp:.1f}  ({sign}{delta:.1f}, {sign}{pct:.0f}%)')
    if extra_info:
        print(extra_info)
    print(f'{"─"*50}')

    # ── Build side-by-side visual ─────────────────────────────────────────
    orig_vis = _draw_boxes(orig, target_boxes, other_boxes)
    proc_vis = _draw_boxes(processed, target_boxes, other_boxes)

    orig_vis = _burn_score(orig_vis,
                           f'ORIGINAL  sharp={orig_sharp:.1f}  f={args.frame}', orig_sharp)
    proc_vis = _burn_score(proc_vis,
                           f'{tier_label}  sharp={proc_sharp:.1f}  ({sign}{pct:.0f}%)', proc_sharp)

    canvas = _side_by_side(orig_vis, proc_vis)

    if args.save:
        args.save.mkdir(parents=True, exist_ok=True)
        stem = f'{args.video.stem}_f{args.frame}_{branch.replace("/", "-")}'
        cv2.imwrite(str(args.save / f'{stem}_original.jpg'),  orig_vis,  [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(args.save / f'{stem}_processed.jpg'), proc_vis,  [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str(args.save / f'{stem}_comparison.jpg'), canvas,   [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f'\nSaved → {args.save}/')

    if not args.no_show:
        cv2.imshow(f'[{branch}]  original (left)  vs  {tier_label} (right)', canvas)
        print('\nPress any key to close …')
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
