#!/usr/bin/env python3
"""
Step 1 — Warm-up: sample frames, fit K-means on shirt colours, save model.

Usage:
    conda activate <your_env>
    python warmup.py --video /path/to/video.mp4
    python warmup.py --video /path/to/video.mp4 --output_dir output/M02 --n_clusters 3

After running, open output/shirt_clusters.png and note which cluster = which team.
Then run: bash run.sh --video ... --team_a <n> --team_b <n>
"""
import argparse
import pickle
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from tqdm import tqdm
from ultralytics import YOLO

from src.shirt_color import get_shirt_color, lab_to_rgb, SHIRT_TOP, SHIRT_BOTTOM


def collect_shirt_colors(video_path, model, warmup_frames, conf_thresh, min_height_frac):
    cap      = cv2.VideoCapture(video_path)
    fps      = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total    = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    h_frame  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total / fps
    cap.release()

    min_h_px = int(min_height_frac * h_frame)
    indices  = np.linspace(0, total - 1, min(warmup_frames, total), dtype=int)

    print(f"Video    : {video_path}")
    print(f"Duration : {duration:.1f}s  ({total} frames @ {fps:.0f} fps)")
    print(f"Sampling : {len(indices)} frames")

    all_colors, all_crops = [], []

    cap = cv2.VideoCapture(video_path)
    for fidx in tqdm(indices, desc='Collecting shirt colours'):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fidx))
        ok, frame = cap.read()
        if not ok:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        for box in model(frame, verbose=False, conf=conf_thresh, classes=[0])[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            if (y2 - y1) < min_h_px:
                continue
            color = get_shirt_color(frame_rgb, (x1, y1, x2, y2))
            if color is not None:
                all_colors.append(color)
                h = y2 - y1
                sy1 = y1 + int(SHIRT_TOP * h)
                sy2 = y1 + int(SHIRT_BOTTOM * h)
                crop = frame_rgb[sy1:sy2, x1:x2]
                all_crops.append(crop.copy() if crop.size > 0 else np.zeros((20, 20, 3), np.uint8))
    cap.release()

    return all_colors, all_crops


def save_cluster_image(kmeans, color_arr, all_crops, output_dir, n_crops=5):
    labels   = kmeans.labels_
    centers  = kmeans.cluster_centers_
    n_k      = len(centers)
    col_list = ['#FF6600', '#3399FF', '#33CC33', '#CC33FF'][:n_k]

    fig, axes = plt.subplots(n_k, n_crops + 1, figsize=(3 * (n_crops + 1), 3.5 * n_k))
    if n_k == 1:
        axes = [axes]

    for cid in range(n_k):
        rgb  = lab_to_rgb(centers[cid])
        cnt  = (labels == cid).sum()
        col  = col_list[cid]

        # Column 0: colour swatch
        ax0 = axes[cid][0]
        ax0.add_patch(plt.Rectangle((0, 0), 1, 1, color=[v / 255 for v in rgb]))
        ax0.set_xlim(0, 1); ax0.set_ylim(0, 1)
        ax0.set_title(f'CLUSTER {cid}\nRGB{rgb}\n{cnt} samples',
                      fontsize=9, fontweight='bold', color=col)
        ax0.axis('off')

        # Columns 1-N: closest-to-centroid shirt crops
        idxs  = np.where(labels == cid)[0]
        dists = np.linalg.norm(color_arr[idxs] - centers[cid], axis=1)
        best  = idxs[np.argsort(dists)[:n_crops]]
        for j, idx in enumerate(best):
            axes[cid][j + 1].imshow(all_crops[idx])
            axes[cid][j + 1].axis('off')
        for j in range(len(best), n_crops):
            axes[cid][j + 1].axis('off')

        fig.text(0.005, 1 - (cid + 0.5) / n_k, f'CLUSTER {cid}',
                 fontsize=11, fontweight='bold', color=col,
                 va='center', rotation=90)

    plt.suptitle(
        'Shirt colour clusters — left: colour swatch  right: sample crops\n'
        '→ Note cluster numbers, then: bash run.sh --team_a N --team_b N',
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout(rect=[0.03, 0, 1, 0.95])

    out = output_dir / 'shirt_clusters.png'
    plt.savefig(out, dpi=130, bbox_inches='tight')
    plt.close()
    return out


def main(args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading YOLO26n...")
    model = YOLO('yolo26n.pt')

    all_colors, all_crops = collect_shirt_colors(
        args.video, model, args.warmup_frames, args.conf, args.min_height
    )

    if len(all_colors) < args.n_clusters:
        print(f"\nERROR: Only {len(all_colors)} detections — need at least {args.n_clusters}.")
        print("Try: lower --conf or --min_height, or use a longer/better video for warmup.")
        return

    print(f"\nFitting K-means (k={args.n_clusters}) on {len(all_colors)} samples...")
    color_arr = np.array(all_colors)
    kmeans    = KMeans(n_clusters=args.n_clusters, random_state=42, n_init=20)
    kmeans.fit(color_arr)

    model_path = output_dir / 'kmeans_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(kmeans, f)
    print(f"K-means model saved → {model_path}")

    img_path = save_cluster_image(kmeans, color_arr, all_crops, output_dir)
    print(f"Cluster image saved → {img_path}")

    print("\n── Cluster summary ──────────────────────────────────")
    for cid in range(args.n_clusters):
        rgb = lab_to_rgb(kmeans.cluster_centers_[cid])
        cnt = (kmeans.labels_ == cid).sum()
        print(f"  Cluster {cid}: {cnt:4d} samples  colour RGB{rgb}")

    print(f"""
Next steps:
  1. Open {img_path}
  2. Identify which cluster = Bradford / Opponent / Other
  3. Run:
       bash run.sh --video {args.video} \\
                   --team_a <cluster_num> \\
                   --team_b <cluster_num> \\
                   --other <cluster_num>  # optional
""")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Warm-up: fit K-means on player shirt colours')
    p.add_argument('--video',         required=True,          help='Input video path')
    p.add_argument('--output_dir',    default='output',       help='Output directory')
    p.add_argument('--n_clusters',    type=int, default=3,    help='K-means clusters (default 3)')
    p.add_argument('--warmup_frames', type=int, default=50,   help='Frames to sample (default 50)')
    p.add_argument('--conf',          type=float, default=0.50, help='YOLO confidence (default 0.50)')
    p.add_argument('--min_height',    type=float, default=0.07, help='Min player height / frame (default 0.07)')
    main(p.parse_args())
