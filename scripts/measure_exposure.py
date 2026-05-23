"""
Production-style sponsor exposure measurement.

Unlike the frame-selection pipeline (which keeps only the best frames for
annotation), this samples the video at a FIXED rate and runs detection on
EVERY sampled frame — no quality gate. It then aggregates per-sponsor exposure
into the kind of report a sponsorship sales team actually wants.

Detection sources:
  • Player jerseys  — person detect → torso crop → OCR
  • Pitch-side / scoreboard — OCR on the full frame (optional, --boards)

Usage:
    python scripts/measure_exposure.py --video videos/M06_black_1080p.mp4
    python scripts/measure_exposure.py --video videos/M06_black_1080p.mp4 --fps 1 --max-seconds 120
    python scripts/measure_exposure.py --video videos/M06_black_1080p.mp4 --boards

Output:
    exposure_output/<stem>/
        ├── detections.csv      ← every sponsor detection (frame-level)
        └── exposure_report.csv ← per-sponsor aggregate (the deliverable)
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from frame_selector.person_detect import PersonDetector
from frame_selector.ocr_sponsor import SponsorOCR, Detection


# ── Aggregation ─────────────────────────────────────────────────────────────

def aggregate(
    per_frame: dict[float, list[Detection]],
    sample_dt: float,
    gap_merge_s: float = 2.0,
) -> list[dict]:
    """Turn frame-level detections into per-sponsor exposure metrics.

    Exposure event = a run of frames containing the sponsor with gaps <= gap_merge_s.
    """
    # sponsor -> list of (time, area_pct, cx, cy, conf)
    by_sponsor: dict[str, list[tuple]] = defaultdict(list)
    for t, dets in per_frame.items():
        # collapse multiple detections of same sponsor in one frame → take largest area
        best: dict[str, Detection] = {}
        for d in dets:
            if d.sponsor not in best or d.area_pct > best[d.sponsor].area_pct:
                best[d.sponsor] = d
        for sp, d in best.items():
            by_sponsor[sp].append((t, d.area_pct, d.cx, d.cy, d.conf))

    rows = []
    for sponsor, recs in by_sponsor.items():
        recs.sort()
        times     = [r[0] for r in recs]
        areas     = [r[1] for r in recs]
        confs     = [r[4] for r in recs]

        # Count distinct exposure events (gap > gap_merge_s starts a new one)
        events = 1
        for i in range(1, len(times)):
            if times[i] - times[i - 1] > gap_merge_s:
                events += 1

        # Each visible frame "owns" sample_dt seconds of screen time
        total_seconds = len(times) * sample_dt
        # Screen-area-seconds = sum(area_pct * dt) — the core AVE proxy
        area_seconds = sum(a * sample_dt for a in areas)

        rows.append(dict(
            sponsor=sponsor,
            total_seconds=round(total_seconds, 1),
            n_appearances=events,
            n_frames=len(times),
            avg_area_pct=round(float(np.mean(areas)), 3),
            peak_area_pct=round(float(np.max(areas)), 3),
            area_seconds=round(area_seconds, 2),
            avg_cx=round(float(np.mean([r[2] for r in recs])), 3),
            avg_cy=round(float(np.mean([r[3] for r in recs])), 3),
            avg_ocr_conf=round(float(np.mean(confs)), 3),
            first_seen_s=round(min(times), 1),
            last_seen_s=round(max(times), 1),
        ))

    rows.sort(key=lambda r: -r['area_seconds'])
    return rows


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, default=Path('exposure_output'))
    ap.add_argument('--fps', type=float, default=1.0,
                    help='Sampling rate (default 1fps — production standard)')
    ap.add_argument('--max-seconds', type=float, default=None,
                    help='Process only first N seconds (for quick demos)')
    ap.add_argument('--min-person-h', type=float, default=0.12,
                    help='Min person height frac to OCR (default 0.12)')
    ap.add_argument('--boards', action='store_true',
                    help='Also OCR full frame for pitch-side / scoreboard sponsors')
    ap.add_argument('--gap-merge', type=float, default=2.0,
                    help='Gap (s) below which detections merge into one appearance')
    args = ap.parse_args()

    if not args.video.exists():
        sys.exit(f'No video at {args.video}')

    out_dir = args.out_dir / args.video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(args.video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total / fps
    if args.max_seconds:
        total = min(total, int(args.max_seconds * fps))

    step = max(1, int(round(fps / args.fps)))
    sample_dt = step / fps
    indices = list(range(0, total, step))

    print(f'Video    : {args.video.name}')
    print(f'Duration : {duration_s/60:.1f} min  ({duration_s:.0f}s)')
    print(f'Sampling : {args.fps}fps → {len(indices)} frames (each = {sample_dt:.1f}s exposure)')
    print(f'Boards   : {"ON" if args.boards else "OFF (jerseys only)"}')

    print('\nLoading detectors...')
    detector = PersonDetector()
    sponsor_ocr = SponsorOCR()
    print('  done.\n')

    per_frame: dict[float, list[Detection]] = {}
    det_rows: list[dict] = []

    for idx in tqdm(indices, desc='measuring'):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        t = idx / fps
        H, W = frame.shape[:2]
        frame_dets: list[Detection] = []

        # --- jersey sponsors: per-person torso OCR ---
        persons = detector.detect(frame, args.min_person_h)
        for (x1, y1, x2, y2) in persons:
            bh = y2 - y1
            ty1 = max(0, y1 + int(0.10 * bh))
            ty2 = min(H, y1 + int(0.75 * bh))
            torso = frame[ty1:ty2, x1:x2]
            dets = sponsor_ocr.read(torso, frame.shape, offset=(x1, ty1))
            frame_dets.extend(dets)

        # --- board / scoreboard sponsors: full-frame OCR ---
        if args.boards:
            board_dets = sponsor_ocr.read(frame, frame.shape, offset=(0, 0),
                                          upscale_to=H)  # no upscale
            frame_dets.extend(board_dets)

        if frame_dets:
            per_frame[t] = frame_dets
            for d in frame_dets:
                det_rows.append(dict(
                    time_s=round(t, 2), sponsor=d.sponsor, text=d.text,
                    ocr_conf=round(d.conf, 3), fuzzy=d.fuzzy,
                    area_pct=round(d.area_pct, 3),
                    cx=round(d.cx, 3), cy=round(d.cy, 3),
                    bbox=','.join(map(str, d.bbox)),
                ))
    cap.release()

    # --- write detections.csv ---
    det_csv = out_dir / 'detections.csv'
    with open(det_csv, 'w', newline='') as f:
        if det_rows:
            w = csv.DictWriter(f, fieldnames=list(det_rows[0].keys()))
            w.writeheader(); w.writerows(det_rows)
        else:
            f.write('no detections\n')

    # --- aggregate + write report ---
    report = aggregate(per_frame, sample_dt, args.gap_merge)
    rep_csv = out_dir / 'exposure_report.csv'
    with open(rep_csv, 'w', newline='') as f:
        if report:
            w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
            w.writeheader(); w.writerows(report)
        else:
            f.write('no sponsors detected\n')

    # --- print report ---
    processed_s = len(indices) * sample_dt
    print(f'\n{"="*72}')
    print(f'SPONSOR EXPOSURE REPORT  —  {args.video.stem}')
    print(f'(measured over {processed_s:.0f}s of footage at {args.fps}fps)')
    print(f'{"="*72}')
    print(f'{"Sponsor":<10}{"Time(s)":>9}{"%match":>8}{"Appears":>9}'
          f'{"AvgArea%":>10}{"PeakArea%":>11}{"AreaSec":>9}{"Conf":>7}')
    print('-'*72)
    for r in report:
        pct = r['total_seconds'] / processed_s * 100 if processed_s else 0
        print(f'{r["sponsor"]:<10}{r["total_seconds"]:>9.1f}{pct:>7.1f}%'
              f'{r["n_appearances"]:>9}{r["avg_area_pct"]:>10.2f}'
              f'{r["peak_area_pct"]:>11.2f}{r["area_seconds"]:>9.1f}'
              f'{r["avg_ocr_conf"]:>7.2f}')
    print('-'*72)
    print('AreaSec = screen-area-seconds (Σ area% × dt) — the core AVE proxy.\n')
    print(f'Output → {out_dir}/')


if __name__ == '__main__':
    main()
