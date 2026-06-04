#!/usr/bin/env python3
"""
Step 2 — Process video: detect + classify teams → output video + timeline chart.

Usage:
    conda activate <your_env>
    python process_video.py --video /path/to/video.mp4 --team_a 0 --team_b 1
    python process_video.py --video /path/to/video.mp4 --team_a 1 --team_b 0 --referee 2 \
        --team_a_label Bradford --team_b_label HFC --output_dir output/M02

Run warmup.py first to generate the K-means model.
"""
import argparse
import pickle
import subprocess
from collections import Counter, deque
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm
from ultralytics import YOLO

from src.shirt_color import get_shirt_color
from src.visualizer import draw_label_box


def load_kmeans(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def build_centroids(kmeans, cluster_map):
    centers = kmeans.cluster_centers_
    return {team: centers[cid] for cid, team in cluster_map.items()}


def classify_shirt(color_lab, centroids):
    best_team, best_dist = list(centroids.keys())[0], float('inf')
    for team, c in centroids.items():
        d = float(np.linalg.norm(color_lab - c))
        if d < best_dist:
            best_dist, best_team = d, team
    return best_team


def process_video(args, centroids, label_map, output_dir):
    cap      = cv2.VideoCapture(args.video)
    src_fps  = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_f  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H_vid    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    MIN_H_PX = int(args.min_height * H_vid)

    stem      = Path(args.video).stem
    tmp_path  = '/tmp/_team_detect_raw.mp4'
    out_video = output_dir / f'{stem}_team_detection.mp4'

    writer = cv2.VideoWriter(
        tmp_path, cv2.VideoWriter_fourcc(*'mp4v'), src_fps, (W, H_vid)
    )

    model         = YOLO('yolo26n.pt')
    track_history = {}
    timeline      = []

    for fidx in tqdm(range(total_f), desc='Processing frames'):
        ok, frame = cap.read()
        if not ok:
            break

        output    = frame.copy()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        counts    = {t: 0 for t in ['Team A', 'Team B', 'Referee']}

        results = model.track(
            frame, persist=True, verbose=False,
            conf=args.conf, classes=[0],
            tracker='bytetrack.yaml'
        )

        if results[0].boxes.id is not None:
            for box, tid in zip(results[0].boxes,
                                results[0].boxes.id.int().tolist()):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if (y2 - y1) < MIN_H_PX:
                    continue

                color = get_shirt_color(frame_rgb, (x1, y1, x2, y2))
                if color is None:
                    continue

                raw_team = classify_shirt(color, centroids)

                if tid not in track_history:
                    track_history[tid] = deque(maxlen=args.smoothing)
                track_history[tid].append(raw_team)
                stable = Counter(track_history[tid]).most_common(1)[0][0]

                label = label_map.get(stable, stable)
                draw_label_box(output, (x1, y1, x2, y2), label, stable)
                if stable in counts:
                    counts[stable] += 1

        writer.write(output)
        timeline.append({
            'frame':   fidx,
            'sec':     round(fidx / src_fps, 2),
            'Team A':  counts['Team A'],
            'Team B':  counts['Team B'],
            'Referee': counts['Referee'],
        })

    cap.release()
    writer.release()

    # Re-encode to H.264 for broad compatibility
    subprocess.run(
        ['ffmpeg', '-y', '-i', tmp_path,
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', str(out_video)],
        check=True, capture_output=True
    )

    mb = out_video.stat().st_size / 1e6
    print(f"\nVideo saved  → {out_video}  ({mb:.1f} MB)")
    print(f"Track IDs seen: {len(track_history)}")

    return pd.DataFrame(timeline), src_fps, stem


def save_timeline(df, src_fps, stem, label_map, output_dir):
    w = max(1, int(src_fps))
    for col in ['Team A', 'Team B', 'Referee']:
        df[f'{col}_s'] = df[col].rolling(w, min_periods=1).mean()

    a_lbl = label_map.get('Team A',  'Team A')
    b_lbl = label_map.get('Team B',  'Team B')
    r_lbl = label_map.get('Referee', 'Referee')

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    axes[0].plot(df['sec'], df['Team A_s'],  color='#5050FF', label=a_lbl,  lw=1.5)
    axes[0].plot(df['sec'], df['Team B_s'],  color='#FF5050', label=b_lbl,  lw=1.5)
    axes[0].plot(df['sec'], df['Referee_s'], color='#00CCCC', label=r_lbl,  lw=1.0, ls='--')
    axes[0].set_ylabel('Players / frame'); axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].spines[['top', 'right']].set_visible(False)

    tot = df['Team A_s'] + df['Team B_s'] + 1e-9
    axes[1].stackplot(df['sec'],
                      df['Team A_s'] / tot * 100,
                      df['Team B_s'] / tot * 100,
                      colors=['#5050FF', '#FF5050'], alpha=0.6,
                      labels=[f'{a_lbl} %', f'{b_lbl} %'])
    axes[1].set_ylabel('Relative presence (%)')
    axes[1].set_xlabel('Time (seconds)')
    axes[1].set_ylim(0, 100)
    axes[1].legend(loc='upper right')
    axes[1].grid(alpha=0.3)
    axes[1].spines[['top', 'right']].set_visible(False)

    plt.suptitle(f'Team Presence — {stem}', fontsize=13, fontweight='bold')
    plt.tight_layout()

    chart = output_dir / f'{stem}_team_timeline.png'
    plt.savefig(chart, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Chart saved  → {chart}")

    csv = output_dir / f'{stem}_team_timeline.csv'
    df[['frame', 'sec', 'Team A', 'Team B', 'Referee']].to_csv(csv, index=False)
    print(f"CSV saved    → {csv}")

    print("\n── Summary ──────────────────────────────────")
    for team, label in label_map.items():
        print(f"  {label:12s}  avg {df[team].mean():.1f}/frame   max {int(df[team].max())}/frame")


def main(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading K-means model from {args.kmeans_model}...")
    kmeans = load_kmeans(args.kmeans_model)

    cluster_map = {args.team_a: 'Team A', args.team_b: 'Team B'}
    if args.referee is not None:
        cluster_map[args.referee] = 'Referee'

    label_map = {
        'Team A':  args.team_a_label,
        'Team B':  args.team_b_label,
        'Referee': args.ref_label,
    }
    centroids = build_centroids(kmeans, cluster_map)

    print("Cluster assignments:")
    for cid, team in cluster_map.items():
        print(f"  Cluster {cid} → {label_map[team]}")
    print()

    df, src_fps, stem = process_video(args, centroids, label_map, output_dir)
    save_timeline(df, src_fps, stem, label_map, output_dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Process video with team detection')
    p.add_argument('--video',          required=True,              help='Input video path')
    p.add_argument('--team_a',         type=int, required=True,    help='Cluster number for Team A')
    p.add_argument('--team_b',         type=int, required=True,    help='Cluster number for Team B')
    p.add_argument('--referee',        type=int, default=None,     help='Cluster number for Referee (optional)')
    p.add_argument('--team_a_label',   default='Bradford',         help='Label for Team A (default: Bradford)')
    p.add_argument('--team_b_label',   default='Opponent',         help='Label for Team B (default: Opponent)')
    p.add_argument('--ref_label',      default='Referee',          help='Label for Referee (default: Referee)')
    p.add_argument('--kmeans_model',   default='output/kmeans_model.pkl', help='Path to K-means model')
    p.add_argument('--output_dir',     default='output',           help='Output directory')
    p.add_argument('--conf',           type=float, default=0.50,   help='YOLO confidence threshold')
    p.add_argument('--min_height',     type=float, default=0.07,   help='Min player height / frame height')
    p.add_argument('--smoothing',      type=int,   default=20,     help='Majority-vote window in frames')
    main(p.parse_args())
