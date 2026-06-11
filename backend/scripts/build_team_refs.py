#!/usr/bin/env python3
"""Build team kit references for the team filter (Windows/CUDA friendly).

Two modes:

1. Auto-cluster from a video clip (recommended — builds target AND other refs):

       python scripts/build_team_refs.py --video path\\to\\clip.mp4

   Detects players, clusters their jersey crops (KMeans on SigLIP embeddings,
   colour-only fallback), and writes one collage image per cluster into
   data/team_refs_review/. Look at the collages, then either type the target
   cluster id at the prompt or re-run non-interactively with --pick N.

2. From folders of pre-cropped player images (full-person crops):

       python scripts/build_team_refs.py --target-dir crops\\bradford --other-dir crops\\rest

Output: data/team_refs.pkl (override with --out). Point TEAM_REFS_PATH at it
(or keep the default location) and set TEAM_FILTER_ENABLED=true in .env.

Build refs once per kit (home/away) and switch the file per match, e.g.
data/team_refs_home.pkl / data/team_refs_away.pkl + TEAM_REFS_PATH env.
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow running from the backend/ directory: python scripts/build_team_refs.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models_zoo.registry import resolve_device                      # noqa: E402
from app.pipeline.teamid.classifier import OTHER, TARGET, learn_weights  # noqa: E402
from app.pipeline.teamid.features import color_feature, encode_crops_masked, siglip_available  # noqa: E402
from app.pipeline.teamid.jersey import get_jersey_region, jersey_quality  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent
MIN_QUALITY = 0.45     # reference crops must be sharp + well-covered
THUMB = 96             # collage tile size


def collect_from_video(video: Path, n_frames: int, person_model: str,
                       conf: float, imgsz: int, device: str):
    """Sample frames, detect persons, return (person_crops, regions, masks)."""
    from ultralytics import YOLO

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        sys.exit(f"cannot open video: {video}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    idxs = np.linspace(0, max(0, total - 1), n_frames).astype(int)

    model = YOLO(person_model)
    crops, regions, masks = [], [], []
    for fi in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
        ok, frame = cap.read()
        if not ok:
            continue
        res = model.predict(frame, classes=[0], conf=conf, imgsz=imgsz,
                            device=device, verbose=False)
        if not res or res[0].boxes is None:
            continue
        for box in res[0].boxes.xyxy.cpu().numpy():
            region, mask = get_jersey_region(frame, box)
            if region is None or jersey_quality(region, mask) < MIN_QUALITY:
                continue
            x1, y1, x2, y2 = (int(v) for v in box)
            crops.append(frame[max(0, y1):y2, max(0, x1):x2].copy())
            regions.append(region)
            masks.append(mask)
    cap.release()
    print(f"collected {len(crops)} usable player crops from {len(idxs)} frames")
    return crops, regions, masks


def collect_from_dir(d: Path):
    """Folder of full-person crops -> (crops, regions, masks)."""
    crops, regions, masks = [], [], []
    for p in sorted(d.iterdir()):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        region, mask = get_jersey_region(img, (0, 0, w, h))
        if region is None:
            continue
        crops.append(img)
        regions.append(region)
        masks.append(mask)
    print(f"{d}: {len(crops)} usable crops")
    return crops, regions, masks


def save_collage(crops: list[np.ndarray], path: Path, cols: int = 10) -> None:
    tiles = [cv2.resize(c, (THUMB, THUMB)) for c in crops[:60]]
    if not tiles:
        return
    rows = (len(tiles) + cols - 1) // cols
    canvas = np.zeros((rows * THUMB, cols * THUMB, 3), np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        canvas[r * THUMB:(r + 1) * THUMB, c * THUMB:(c + 1) * THUMB] = t
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), canvas)


def build_and_save(out: Path, assignments: list[str],
                   embeddings: np.ndarray | None,
                   color_feats: list[np.ndarray | None]) -> None:
    teams = [TARGET, OTHER]
    w_color, w_siglip, centroids, colors = learn_weights(
        teams, assignments, embeddings, color_feats)

    refs = {
        "schema": 3,
        "teams": {
            t: {"embedding": centroids.get(t), "color": colors.get(t)}
            for t in teams if colors.get(t) is not None or centroids.get(t) is not None
        },
        "meta": {"w_color": w_color, "w_siglip": w_siglip,
                 "temp_c": 8.0, "temp_s": 15.0},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump(refs, f)
    n_t = assignments.count(TARGET)
    n_o = assignments.count(OTHER)
    print(f"\nsaved {out}")
    print(f"  target crops: {n_t} · other crops: {n_o}")
    print(f"  learned weights: color={w_color:.2f}  siglip={w_siglip:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", type=Path, help="clip to auto-cluster")
    src.add_argument("--target-dir", type=Path, help="folder of target-team crops")
    ap.add_argument("--other-dir", type=Path, help="folder of opponent/referee crops (with --target-dir)")
    ap.add_argument("--out", type=Path, default=BACKEND_DIR / "data" / "team_refs.pkl")
    ap.add_argument("--frames", type=int, default=40, help="frames sampled from --video")
    ap.add_argument("--clusters", type=int, default=3, help="KMeans clusters (2 teams + officials)")
    ap.add_argument("--pick", type=int, help="target cluster id (skip the interactive prompt)")
    ap.add_argument("--person-model", default="yolo11m.pt")
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--imgsz", type=int, default=960)
    ap.add_argument("--device", default="auto", help="auto | 0 | cuda | cpu")
    args = ap.parse_args()

    device = resolve_device(args.device)
    print(f"device: {device} · SigLIP available: {siglip_available()}")

    # ── Folder mode ──────────────────────────────────────────────────────
    if args.target_dir:
        t_crops, t_regions, t_masks = collect_from_dir(args.target_dir)
        if not t_crops:
            sys.exit("no usable target crops")
        o_crops, o_regions, o_masks = ([], [], [])
        if args.other_dir:
            o_crops, o_regions, o_masks = collect_from_dir(args.other_dir)
        if not o_crops:
            sys.exit("--other-dir is required (and must contain crops): the "
                     "classifier needs both classes. Use --video mode to "
                     "harvest opponents automatically.")

        regions = t_regions + o_regions
        masks = t_masks + o_masks
        assignments = [TARGET] * len(t_crops) + [OTHER] * len(o_crops)
        embeddings = encode_crops_masked(regions, masks, device)
        color_feats = [color_feature(r, m) for r, m in zip(regions, masks)]
        build_and_save(args.out, assignments, embeddings, color_feats)
        return

    # ── Video auto-cluster mode ──────────────────────────────────────────
    crops, regions, masks = collect_from_video(
        args.video, args.frames, args.person_model, args.conf, args.imgsz, device)
    if len(crops) < args.clusters * 5:
        sys.exit(f"too few crops ({len(crops)}) — use a longer/clearer clip")

    color_feats = [color_feature(r, m) for r, m in zip(regions, masks)]
    embeddings = encode_crops_masked(regions, masks, device)

    # Cluster on SigLIP embeddings (semantic), colour features as fallback.
    if embeddings is not None:
        feats = embeddings
    else:
        keep = [i for i, c in enumerate(color_feats) if c is not None]
        crops = [crops[i] for i in keep]
        regions = [regions[i] for i in keep]
        masks = [masks[i] for i in keep]
        color_feats = [color_feats[i] for i in keep]
        feats = np.stack(color_feats)

    from sklearn.cluster import KMeans
    km = KMeans(n_clusters=args.clusters, n_init=10, random_state=0).fit(feats)
    labels = km.labels_

    review_dir = args.out.parent / "team_refs_review"
    print(f"\ncluster collages -> {review_dir}")
    for k in range(args.clusters):
        members = [crops[i] for i in range(len(crops)) if labels[i] == k]
        save_collage(members, review_dir / f"cluster_{k}.jpg")
        print(f"  cluster {k}: {len(members):3d} crops  ->  cluster_{k}.jpg")

    pick = args.pick
    if pick is None:
        try:
            pick = int(input(f"\nOpen the collages above, then enter the TARGET "
                             f"(Bradford) cluster id [0-{args.clusters - 1}]: "))
        except (ValueError, EOFError):
            sys.exit("no cluster picked — re-run with --pick N")
    if not (0 <= pick < args.clusters):
        sys.exit(f"invalid cluster id {pick}")

    assignments = [TARGET if l == pick else OTHER for l in labels]
    build_and_save(args.out, assignments, embeddings, color_feats)


if __name__ == "__main__":
    main()
