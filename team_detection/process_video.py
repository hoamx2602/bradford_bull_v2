#!/usr/bin/env python3
"""
Step 2 — Process video: detect + classify teams → output video + timeline chart.

Uses SigLIP embeddings + cosine similarity for team classification.
Build the refs file first with ref_build.py.

Usage:
    python process_video.py --video /path/to/video.mp4 --refs output/refs/team_refs.pkl
    python process_video.py --video /path/to/video.mp4 --refs output/refs/team_refs.pkl \\
        --team_a_label Bradford --team_b_label HFC --output_dir output/M02
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

from src.embedder    import load_siglip, encode_crops
from src.shirt_color import get_shirt_crop_bgr
from src.visualizer  import draw_label_box

TEAM_COLORS = {'Team A': '#5050FF', 'Team B': '#FF5050', 'Other': '#00CCCC'}

# Re-encode a track's shirt every this many frames.
# Smoothing window handles jitter between updates.
ENCODE_EVERY = 8


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_refs(path: str) -> dict:
    with open(path, 'rb') as f:
        return pickle.load(f)


def classify_shirt(embedding: np.ndarray, team_embeddings: dict) -> str:
    """Cosine similarity — both sides are L2-normalised → simple dot product."""
    return max(team_embeddings,
               key=lambda t: float(np.dot(embedding, team_embeddings[t])))


# ── Video processing ──────────────────────────────────────────────────────────

def process_video(args, team_embeddings, label_map, teams, siglip_proc, siglip_model, output_dir):
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
        tmp_path, cv2.VideoWriter_fourcc(*'mp4v'), src_fps, (W, H_vid))

    yolo_model    = YOLO('yolo26n.pt')
    track_history = {}
    emb_cache     = {}   # tid → last SigLIP embedding
    last_encoded  = {}   # tid → frame index of last encode
    timeline      = []

    for fidx in tqdm(range(total_f), desc='Processing frames'):
        ok, frame = cap.read()
        if not ok:
            break

        output = frame.copy()
        counts = {t: 0 for t in teams}

        results = yolo_model.track(
            frame, persist=True, verbose=False,
            conf=args.conf, classes=[0], tracker='bytetrack.yaml')

        if results[0].boxes.id is not None:
            tids  = results[0].boxes.id.int().tolist()
            boxes = results[0].boxes

            # ── Batch-encode crops that are due for an update ─────────────────
            to_encode = []   # list of (tid, crop_bgr)
            for box, tid in zip(boxes, tids):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if (y2 - y1) < MIN_H_PX:
                    continue
                needs = (tid not in last_encoded or
                         fidx - last_encoded[tid] >= ENCODE_EVERY)
                if needs:
                    crop = get_shirt_crop_bgr(frame, (x1, y1, x2, y2))
                    if crop is not None:
                        to_encode.append((tid, crop))

            if to_encode:
                tids_enc  = [t for t, _ in to_encode]
                crops_enc = [c for _, c in to_encode]
                embs      = encode_crops(crops_enc, siglip_proc, siglip_model)
                for tid, emb in zip(tids_enc, embs):
                    emb_cache[tid]    = emb
                    last_encoded[tid] = fidx

            # ── Classify + draw ───────────────────────────────────────────────
            for box, tid in zip(boxes, tids):
                if tid not in emb_cache:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                if (y2 - y1) < MIN_H_PX:
                    continue

                raw_team = classify_shirt(emb_cache[tid], team_embeddings)

                if tid not in track_history:
                    track_history[tid] = deque(maxlen=args.smoothing)
                track_history[tid].append(raw_team)
                stable = Counter(track_history[tid]).most_common(1)[0][0]

                label = label_map.get(stable, stable)
                draw_label_box(output, (x1, y1, x2, y2), label, stable)
                if stable in counts:
                    counts[stable] += 1

        writer.write(output)
        row = {'frame': fidx, 'sec': round(fidx / src_fps, 2)}
        row.update(counts)
        timeline.append(row)

    cap.release()
    writer.release()

    subprocess.run(
        ['ffmpeg', '-y', '-i', tmp_path,
         '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', str(out_video)],
        check=True, capture_output=True)

    mb = out_video.stat().st_size / 1e6
    print(f"\nVideo saved  → {out_video}  ({mb:.1f} MB)")
    print(f"Track IDs seen: {len(track_history)}")
    return pd.DataFrame(timeline), src_fps, stem


# ── Timeline chart ────────────────────────────────────────────────────────────

def save_timeline(df, src_fps, stem, label_map, teams, output_dir):
    w = max(1, int(src_fps))
    for t in teams:
        df[f'{t}_s'] = df[t].rolling(w, min_periods=1).mean()

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)

    for t in teams:
        ls  = '--' if t == 'Other' else '-'
        lw  = 1.0  if t == 'Other' else 1.5
        col = TEAM_COLORS.get(t, '#999999')
        axes[0].plot(df['sec'], df[f'{t}_s'],
                     color=col, label=label_map.get(t, t), lw=lw, ls=ls)
    axes[0].set_ylabel('Players / frame')
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[0].spines[['top', 'right']].set_visible(False)

    main_teams = [t for t in teams if t in ('Team A', 'Team B')]
    if len(main_teams) == 2:
        ta, tb = 'Team A', 'Team B'
        tot = df[f'{ta}_s'] + df[f'{tb}_s'] + 1e-9
        axes[1].stackplot(
            df['sec'],
            df[f'{ta}_s'] / tot * 100,
            df[f'{tb}_s'] / tot * 100,
            colors=[TEAM_COLORS[ta], TEAM_COLORS[tb]], alpha=0.6,
            labels=[f"{label_map.get(ta,ta)} %", f"{label_map.get(tb,tb)} %"])
        axes[1].set_ylabel('Relative presence (%)')
        axes[1].set_ylim(0, 100)
        axes[1].legend(loc='upper right')
    axes[1].set_xlabel('Time (seconds)')
    axes[1].grid(alpha=0.3)
    axes[1].spines[['top', 'right']].set_visible(False)

    plt.suptitle(f'Team Presence — {stem}', fontsize=13, fontweight='bold')
    plt.tight_layout()

    chart = output_dir / f'{stem}_team_timeline.png'
    plt.savefig(chart, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Chart saved  → {chart}")

    csv = output_dir / f'{stem}_team_timeline.csv'
    df[['frame', 'sec'] + list(teams)].to_csv(csv, index=False)
    print(f"CSV saved    → {csv}")

    print("\n── Summary ──────────────────────────────────")
    for team in teams:
        label = label_map.get(team, team)
        print(f"  {label:14s}  avg {df[team].mean():.1f}/frame   max {int(df[team].max())}/frame")


# ── Entry point ───────────────────────────────────────────────────────────────

def main(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading reference model from {args.refs}...")
    refs = load_refs(args.refs)

    team_embeddings = {team: data['embedding'] for team, data in refs.items()}
    label_map = {team: data['label'] for team, data in refs.items()}
    if args.team_a_label and 'Team A' in label_map: label_map['Team A'] = args.team_a_label
    if args.team_b_label and 'Team B' in label_map: label_map['Team B'] = args.team_b_label
    if args.other_label  and 'Other'  in label_map: label_map['Other']  = args.other_label

    teams = list(refs.keys())

    print("Reference teams:")
    for team in teams:
        print(f"  {label_map[team]:14s} ← {team}")

    siglip_proc, siglip_model = load_siglip(args.siglip_model)

    df, src_fps, stem = process_video(
        args, team_embeddings, label_map, teams,
        siglip_proc, siglip_model, output_dir)
    save_timeline(df, src_fps, stem, label_map, teams, output_dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Process video with SigLIP-based team detection')
    p.add_argument('--video',          required=True)
    p.add_argument('--refs',           required=True,              help='Path to team_refs.pkl')
    p.add_argument('--team_a_label',   default=None,               help='Override label for Team A')
    p.add_argument('--team_b_label',   default=None,               help='Override label for Team B')
    p.add_argument('--other_label',    default=None,               help='Override label for Other')
    p.add_argument('--siglip_model',   default='google/siglip-base-patch16-224')
    p.add_argument('--output_dir',     default='output')
    p.add_argument('--conf',           type=float, default=0.50)
    p.add_argument('--min_height',     type=float, default=0.07)
    p.add_argument('--smoothing',      type=int,   default=20,     help='Majority-vote window (frames)')
    main(p.parse_args())
