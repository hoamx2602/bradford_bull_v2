"""
Deep analysis script: extract diverse frames from a 1080p rugby video,
compute every relevant metric, save annotated images + CSV.

Goal: understand what makes a frame GOOD or BAD for annotation on Roboflow,
and derive optimal pipeline parameters from real data.

Usage:
    python scripts/analyze_video.py --video videos/M06_black_1080p.mp4 --color black
    python scripts/analyze_video.py --video videos/M01_white_1080p.mp4 --color white
"""
import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.color_filter import classify_bbox, grass_ratio, COLOR_PRESETS
from frame_selector.person_detect import PersonDetector
from frame_selector.sharpness import tenengrad_score, laplacian_score

OUT_DIR = Path('analyze_output')


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def inter_frame_diff(prev_gray, curr_gray):
    """Mean absolute pixel difference between consecutive frames (motion proxy)."""
    if prev_gray is None:
        return 0.0
    return float(np.mean(np.abs(curr_gray.astype(np.float32) - prev_gray.astype(np.float32))))


def global_sharpness(frame_bgr):
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return tenengrad_score(gray), laplacian_score(gray)


def bbox_metrics(frame_bgr, bbox, target_color, overlay_mask=None):
    """Per-detection metrics: size, sharpness, color match, aspect ratio."""
    x1, y1, x2, y2 = bbox
    H, W = frame_bgr.shape[:2]
    bh = y2 - y1
    bw = x2 - x1
    height_frac = bh / H
    width_frac = bw / W
    aspect = bh / max(bw, 1)

    # Torso ROI (same as pipeline: 15%-70% of bbox height)
    ty1 = y1 + int(bh * 0.15)
    ty2 = y1 + int(bh * 0.70)
    tx1 = x1 + int(bw * 0.15)
    tx2 = x1 + int(bw * 0.85)
    torso = frame_bgr[ty1:ty2, tx1:tx2]

    torso_sharp_t, torso_sharp_l = 0.0, 0.0
    color_match_ratio = 0.0
    if torso.size > 0:
        tg = cv2.cvtColor(torso, cv2.COLOR_BGR2GRAY)
        torso_sharp_t = tenengrad_score(tg)
        torso_sharp_l = laplacian_score(tg)

        # Color match fraction — presets is a list of (lo, hi) ranges
        hsv = cv2.cvtColor(torso, cv2.COLOR_BGR2HSV)
        if target_color in COLOR_PRESETS:
            combined = np.zeros(torso.shape[:2], dtype=np.uint8)
            for lo, hi in COLOR_PRESETS[target_color]:
                combined |= cv2.inRange(hsv, np.array(lo), np.array(hi))
            color_match_ratio = float(combined.mean() / 255.0)

    is_target = classify_bbox(frame_bgr, bbox, target_color, overlay_mask)

    return {
        'height_frac': height_frac,
        'width_frac': width_frac,
        'aspect': aspect,
        'torso_sharp_t': torso_sharp_t,
        'torso_sharp_l': torso_sharp_l,
        'color_match': color_match_ratio,
        'is_target': is_target,
    }


def crowd_and_grass(frame_bgr, overlay_mask=None):
    H, W = frame_bgr.shape[:2]
    gr = grass_ratio(frame_bgr, overlay_mask)

    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    grass_m = cv2.inRange(hsv, np.array([30, 35, 25]), np.array([90, 255, 230]))
    om = overlay_mask if overlay_mask is not None else np.zeros((H, W), np.uint8)
    not_grass_not_overlay = (grass_m == 0) & (om == 0)
    crowd = float(not_grass_not_overlay[:H // 2, :].mean())
    return gr, crowd


def estimate_camera_motion(prev_gray, curr_gray, sample=8):
    """Estimate camera motion via sparse Lucas-Kanade on grid points."""
    if prev_gray is None:
        return 0.0, 0.0
    h, w = prev_gray.shape
    # sample grid points
    ys = np.linspace(h * 0.1, h * 0.9, sample).astype(np.float32)
    xs = np.linspace(w * 0.1, w * 0.9, sample).astype(np.float32)
    pts = np.array([[x, y] for y in ys for x in xs], dtype=np.float32).reshape(-1, 1, 2)

    next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, pts, None,
                                                     winSize=(21, 21), maxLevel=3)
    good = status.ravel() == 1
    if good.sum() < 4:
        return 0.0, 0.0
    flow = next_pts[good] - pts[good]
    flow_x = float(np.median(flow[:, 0, 0]))
    flow_y = float(np.median(flow[:, 0, 1]))
    return flow_x, flow_y


# ---------------------------------------------------------------------------
# Annotation drawing
# ---------------------------------------------------------------------------

def draw_annotations(frame, boxes_data, metrics, frame_idx, time_s):
    vis = frame.copy()
    H, W = vis.shape[:2]

    # top bar
    cv2.rectangle(vis, (0, 0), (W, 56), (20, 20, 20), -1)
    txt1 = f'f={frame_idx}  t={time_s:.1f}s  grass={metrics["grass_ratio"]:.2f}  crowd={metrics["crowd_score"]:.2f}'
    txt2 = (f'global_sharp_t={metrics["global_sharp_t"]:.1f}  '
            f'global_sharp_l={metrics["global_sharp_l"]:.1f}  '
            f'ifdiff={metrics["ifdiff"]:.1f}  '
            f'cam_flow=({metrics["flow_x"]:.1f},{metrics["flow_y"]:.1f})')
    cv2.putText(vis, txt1, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 100), 1)
    cv2.putText(vis, txt2, (6, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 255, 180), 1)

    for bd in boxes_data:
        x1, y1, x2, y2 = bd['bbox']
        color = (0, 255, 0) if bd['is_target'] else (0, 80, 255)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

        # label inside bbox
        bh = y2 - y1
        lbl = (f"h={bd['height_frac']:.2f} "
               f"st={bd['torso_sharp_t']:.1f} "
               f"cm={bd['color_match']:.2f}")
        fy = max(y1 + 14, 60)
        cv2.putText(vis, lbl, (x1 + 2, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    (255, 255, 255), 1)

        # torso ROI overlay
        bw = x2 - x1
        ty1 = y1 + int(bh * 0.15)
        ty2 = y1 + int(bh * 0.70)
        tx1 = x1 + int(bw * 0.15)
        tx2 = x1 + int(bw * 0.85)
        cv2.rectangle(vis, (tx1, ty1), (tx2, ty2), (0, 255, 255), 1)

    # sharpness bar
    t_score = metrics['global_sharp_t']
    bar_w = int(min(1.0, t_score / 200.0) * (W - 20))
    bar_col = (0, 60, 220) if t_score < 30 else (0, 200, 220) if t_score < 80 else (0, 200, 80)
    cv2.rectangle(vis, (10, H - 8), (10 + bar_w, H - 2), bar_col, -1)

    return vis


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, required=True)
    ap.add_argument('--color', default='black')
    ap.add_argument('--n-samples', type=int, default=120,
                    help='Number of frames to sample uniformly')
    ap.add_argument('--dense-every', type=int, default=0,
                    help='Also sample every N frames in first 2 min for temporal study')
    args = ap.parse_args()

    out = OUT_DIR / args.video.stem
    out.mkdir(parents=True, exist_ok=True)
    (out / 'frames').mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f'\nVideo: {args.video.name}  {W}x{H}  {fps:.0f}fps  {total} frames  '
          f'{total/fps/60:.1f} min')

    # Build sample indices: uniform across full video
    uniform_idx = np.linspace(0, total - 1, args.n_samples).astype(int).tolist()

    # Dense sampling of first 2 minutes for temporal analysis
    dense_idx = []
    if args.dense_every > 0:
        end_dense = min(total, int(fps * 120))
        dense_idx = list(range(0, end_dense, args.dense_every))

    sample_idx = sorted(set(uniform_idx + dense_idx))
    print(f'Sampling {len(sample_idx)} frames total')

    print('Loading YOLO detector …')
    detector = PersonDetector()

    csv_path = out / 'metrics.csv'
    fieldnames = [
        'frame_idx', 'time_s', 'minute',
        'grass_ratio', 'crowd_score',
        'global_sharp_t', 'global_sharp_l',
        'ifdiff', 'flow_x', 'flow_y', 'flow_mag',
        'n_persons', 'n_target', 'n_other',
        'max_target_h', 'avg_target_h', 'min_target_h',
        'max_target_sharp_t', 'avg_target_sharp_t',
        'max_target_color_match', 'avg_target_color_match',
        'has_closeup',       # any target player h > 0.40
        'has_medium',        # any target player h > 0.18
        'pipeline_pass',     # would pass current pipeline filters
        'pipeline_reason',   # reason for fail (if any)
    ]

    prev_gray = None
    results = []

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, idx in enumerate(sample_idx):
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok:
                continue

            time_s = idx / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Global metrics
            sharp_t, sharp_l = global_sharpness(frame)
            ifdiff = inter_frame_diff(prev_gray, gray)
            flow_x, flow_y = estimate_camera_motion(prev_gray, gray)
            flow_mag = (flow_x**2 + flow_y**2) ** 0.5
            gr, crowd = crowd_and_grass(frame)

            # Detection
            all_boxes = detector.detect(frame, min_height_frac=0.05)  # lower threshold to see more
            boxes_data = []
            for b in all_boxes:
                bm = bbox_metrics(frame, b, args.color)
                bm['bbox'] = b
                boxes_data.append(bm)

            target_bd = [bd for bd in boxes_data if bd['is_target']]
            other_bd  = [bd for bd in boxes_data if not bd['is_target']]

            n_target = len(target_bd)
            n_other  = len(other_bd)

            max_tgt_h = max((bd['height_frac'] for bd in target_bd), default=0.0)
            avg_tgt_h = float(np.mean([bd['height_frac'] for bd in target_bd])) if target_bd else 0.0
            min_tgt_h = min((bd['height_frac'] for bd in target_bd), default=0.0)

            max_tgt_st = max((bd['torso_sharp_t'] for bd in target_bd), default=0.0)
            avg_tgt_st = float(np.mean([bd['torso_sharp_t'] for bd in target_bd])) if target_bd else 0.0

            max_tgt_cm = max((bd['color_match'] for bd in target_bd), default=0.0)
            avg_tgt_cm = float(np.mean([bd['color_match'] for bd in target_bd])) if target_bd else 0.0

            has_closeup = max_tgt_h >= 0.40
            has_medium  = max_tgt_h >= 0.18

            # Pipeline pass/fail audit
            reason = 'ok'
            if not (0.18 <= gr <= 0.92):
                reason = f'grass_ratio={gr:.2f}'
            elif crowd > 0.85:
                reason = f'crowd={crowd:.2f}'
            elif len(all_boxes) < 2:
                reason = f'n_persons={len(all_boxes)}'
            elif n_target < 1:
                reason = 'no_target_player'
            elif max_tgt_h < 0.18:
                reason = f'max_tgt_h={max_tgt_h:.2f}<0.18'
            pipeline_pass = (reason == 'ok')

            row = {
                'frame_idx': idx,
                'time_s': round(time_s, 2),
                'minute': round(time_s / 60, 2),
                'grass_ratio': round(gr, 3),
                'crowd_score': round(crowd, 3),
                'global_sharp_t': round(sharp_t, 2),
                'global_sharp_l': round(sharp_l, 2),
                'ifdiff': round(ifdiff, 2),
                'flow_x': round(flow_x, 2),
                'flow_y': round(flow_y, 2),
                'flow_mag': round(flow_mag, 2),
                'n_persons': len(all_boxes),
                'n_target': n_target,
                'n_other': n_other,
                'max_target_h': round(max_tgt_h, 3),
                'avg_target_h': round(avg_tgt_h, 3),
                'min_target_h': round(min_tgt_h, 3),
                'max_target_sharp_t': round(max_tgt_st, 2),
                'avg_target_sharp_t': round(avg_tgt_st, 2),
                'max_target_color_match': round(max_tgt_cm, 3),
                'avg_target_color_match': round(avg_tgt_cm, 3),
                'has_closeup': int(has_closeup),
                'has_medium': int(has_medium),
                'pipeline_pass': int(pipeline_pass),
                'pipeline_reason': reason,
            }
            writer.writerow(row)
            results.append(row)

            # Save annotated frame
            vis = draw_annotations(frame, boxes_data, {
                'grass_ratio': gr, 'crowd_score': crowd,
                'global_sharp_t': sharp_t, 'global_sharp_l': sharp_l,
                'ifdiff': ifdiff, 'flow_x': flow_x, 'flow_y': flow_y,
            }, idx, time_s)

            # Resize to 960-wide for manageable file size
            scale = 960 / W
            vis_sm = cv2.resize(vis, (960, int(H * scale)))

            status_tag = 'PASS' if pipeline_pass else f'FAIL_{reason[:12]}'
            fname = f'{idx:06d}_t{time_s:.0f}s_{status_tag}_st{sharp_t:.0f}.jpg'
            cv2.imwrite(str(out / 'frames' / fname), vis_sm, [cv2.IMWRITE_JPEG_QUALITY, 88])

            prev_gray = gray

            if (i + 1) % 20 == 0:
                print(f'  {i+1}/{len(sample_idx)}  frame {idx}  t={time_s:.0f}s  '
                      f'sharp_t={sharp_t:.1f}  n_target={n_target}  pass={pipeline_pass}')

    cap.release()

    # ── Summary statistics ───────────────────────────────────────────────────
    import json

    passing = [r for r in results if r['pipeline_pass']]
    failing = [r for r in results if not r['pipeline_pass']]

    fail_reasons = {}
    for r in failing:
        reason = r['pipeline_reason'].split('=')[0]
        fail_reasons[reason] = fail_reasons.get(reason, 0) + 1

    def stats(vals, key):
        v = [r[key] for r in vals if r[key] is not None]
        if not v:
            return {}
        return {
            'min': round(min(v), 3), 'max': round(max(v), 3),
            'mean': round(float(np.mean(v)), 3), 'p25': round(float(np.percentile(v, 25)), 3),
            'p50': round(float(np.percentile(v, 50)), 3), 'p75': round(float(np.percentile(v, 75)), 3),
        }

    summary = {
        'video': args.video.name,
        'target_color': args.color,
        'total_sampled': len(results),
        'pipeline_pass': len(passing),
        'pipeline_fail': len(failing),
        'pass_rate_pct': round(100 * len(passing) / max(len(results), 1), 1),
        'fail_reasons': fail_reasons,
        'passing_frames': {
            'global_sharp_t': stats(passing, 'global_sharp_t'),
            'max_target_h': stats(passing, 'max_target_h'),
            'avg_target_sharp_t': stats(passing, 'avg_target_sharp_t'),
            'n_target': stats(passing, 'n_target'),
            'grass_ratio': stats(passing, 'grass_ratio'),
            'crowd_score': stats(passing, 'crowd_score'),
            'ifdiff': stats(passing, 'ifdiff'),
            'flow_mag': stats(passing, 'flow_mag'),
        },
        'blurry_passing': {
            'count': sum(1 for r in passing if r['global_sharp_t'] < 30),
            'pct': round(100 * sum(1 for r in passing if r['global_sharp_t'] < 30) / max(len(passing), 1), 1),
        },
        'closeup_frames': {
            'count': sum(1 for r in results if r['has_closeup']),
            'pct_of_all': round(100 * sum(1 for r in results if r['has_closeup']) / max(len(results), 1), 1),
            'pct_of_passing': round(100 * sum(1 for r in passing if r['has_closeup']) / max(len(passing), 1), 1),
        },
    }

    summary_path = out / 'summary.json'
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f'\n{"="*60}')
    print(f'SUMMARY: {args.video.name}')
    print(f'{"="*60}')
    print(f'Sampled: {len(results)} frames')
    print(f'Pass: {len(passing)} ({summary["pass_rate_pct"]}%)   Fail: {len(failing)}')
    print(f'Fail reasons: {fail_reasons}')
    print(f'\nPassing frames — global sharpness (Tenengrad):')
    st = summary['passing_frames']['global_sharp_t']
    if st:
        print(f'  min={st["min"]}  p25={st["p25"]}  median={st["p50"]}  p75={st["p75"]}  max={st["max"]}')
    print(f'\nPassing frames — max target player height fraction:')
    mh = summary['passing_frames']['max_target_h']
    if mh:
        print(f'  min={mh["min"]}  p25={mh["p25"]}  median={mh["p50"]}  p75={mh["p75"]}  max={mh["max"]}')
    print(f'\nBlurry-but-passing (sharp_t < 30): {summary["blurry_passing"]["count"]} '
          f'({summary["blurry_passing"]["pct"]}% of passing)')
    print(f'Close-up frames (target h>0.40): {summary["closeup_frames"]["count"]} '
          f'({summary["closeup_frames"]["pct_of_passing"]}% of passing)')
    print(f'\nOutputs saved to: {out}/')
    print(f'  metrics.csv   — full data for all {len(results)} frames')
    print(f'  summary.json  — aggregated statistics')
    print(f'  frames/       — annotated JPEGs ({len(results)} files)')


if __name__ == '__main__':
    main()
