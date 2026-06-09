#!/usr/bin/env python3
"""
Convert the Roboflow **COCO** export (logo-dataset/) into YOLO format with a
**clip-aware** train/val split, and write a data.yaml ready for yolo26 training.

Why clip-aware (not Roboflow's random split):
    The frames come from ~30 short clips; consecutive frames of the same clip are
    near-duplicates. A random per-image split leaks those near-duplicates across
    train and val, giving an over-optimistic mAP. We instead keep WHOLE clips on
    one side of the split, so val measures real generalisation to unseen footage.

Input  (default): ../logo-dataset/train/_annotations.coco.json  (+ images)
Output (default): ./data/{train,val}/{images,labels}  +  ./data/data.yaml

Usage:
    python prepare_data.py
    python prepare_data.py --coco_dir ../logo-dataset/train --val_frac 0.18
"""
import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLIP_RE = re.compile(r'^(clip_\d+)')


def clip_key(file_name: str) -> str:
    m = CLIP_RE.match(file_name)
    return m.group(1) if m else 'other'


def _one_split(by_clip, clips, val_frac, total, seed):
    import random
    order = list(clips)
    random.Random(seed).shuffle(order)
    target, val_clips, n_val = total * val_frac, set(), 0
    for c in order:
        if n_val >= target:
            break
        val_clips.add(c)
        n_val += len(by_clip[c])
    return val_clips


def split_clips(images, anns_by, val_frac, seed):
    """
    Assign whole clips to train/val (clip-aware), targeting ~val_frac of images.

    With ~30 tiny clips and heavy class imbalance, a single random clip split can
    dump most of a class into val. When seed is None we search seeds and pick the
    split that best keeps each class's instances on the TRAIN side (so every logo
    is actually learnable), while staying near the target val fraction.
    """
    by_clip = defaultdict(list)
    for im in images:
        by_clip[clip_key(im['file_name'])].append(im)
    clips = sorted(by_clip)
    total = len(images)

    def score(val_clips):
        val_ids = {im['id'] for c in val_clips for im in by_clip[c]}
        tr, va = Counter(), Counter()
        for im in images:
            tgt = va if im['id'] in val_ids else tr
            for a in anns_by.get(im['id'], []):
                tgt[a['category_id']] += 1
        # penalise classes whose train instances fall below 60% of their total
        bad = sum(1 for c in set(tr) | set(va)
                  if tr[c] < 0.6 * (tr[c] + va[c]))
        frac_dev = abs(len(val_ids) / (total or 1) - val_frac)
        return (bad, frac_dev)

    if seed is not None:
        best = _one_split(by_clip, clips, val_frac, total, seed)
    else:
        cand = [_one_split(by_clip, clips, val_frac, total, s) for s in range(200)]
        best = min(cand, key=score)

    val_ids = {im['id'] for c in best for im in by_clip[c]}
    return val_ids, best


def to_yolo_box(bbox, w, h):
    """COCO [x,y,bw,bh] (top-left, absolute) -> YOLO [cx,cy,bw,bh] normalised."""
    x, y, bw, bh = bbox
    cx = (x + bw / 2) / w
    cy = (y + bh / 2) / h
    return cx, cy, bw / w, bh / h


def main(args):
    coco_dir  = (HERE / args.coco_dir).resolve()
    json_path = coco_dir / '_annotations.coco.json'
    if not json_path.exists():
        # fall back to any *.json in the folder
        cands = list(coco_dir.glob('*.json'))
        if not cands:
            raise SystemExit(f"No COCO json found in {coco_dir}")
        json_path = cands[0]

    d = json.loads(json_path.read_text(encoding='utf-8'))

    # Keep category_id == YOLO class index (Roboflow's class 0 is an unused
    # super-category placeholder; leaving it in keeps indices aligned and matches
    # Roboflow's own YOLO export).
    cats  = {c['id']: c['name'] for c in d['categories']}
    nc    = max(cats) + 1
    names = [cats.get(i, f'class_{i}') for i in range(nc)]

    images   = {im['id']: im for im in d['images']}
    anns_by  = defaultdict(list)
    for a in d['annotations']:
        anns_by[a['image_id']].append(a)

    val_ids, val_clips = split_clips(d['images'], anns_by, args.val_frac, args.seed)

    out = (HERE / args.out_dir).resolve()
    if out.exists() and args.clean:
        shutil.rmtree(out)
    for sp in ('train', 'val'):
        (out / sp / 'images').mkdir(parents=True, exist_ok=True)
        (out / sp / 'labels').mkdir(parents=True, exist_ok=True)

    counts = Counter()
    cls_per_split = {'train': Counter(), 'val': Counter()}
    for img_id, im in images.items():
        sp = 'val' if img_id in val_ids else 'train'
        fn = im['file_name']
        w, h = im['width'], im['height']

        src = coco_dir / fn
        if not src.exists():
            print(f"  WARNING: missing image {fn} — skipped")
            continue
        shutil.copy2(src, out / sp / 'images' / fn)

        lines = []
        for a in anns_by.get(img_id, []):
            cx, cy, bw, bh = to_yolo_box(a['bbox'], w, h)
            cls = a['category_id']
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            cls_per_split[sp][cls] += 1
        # write label (empty file for background images is valid for YOLO)
        (out / sp / 'labels' / (Path(fn).stem + '.txt')).write_text(
            "\n".join(lines), encoding='utf-8')
        counts[sp] += 1

    data_yaml = out / 'data.yaml'
    # Quote names to survive special chars; write a clean YOLO data.yaml.
    names_str = "[" + ", ".join(f"'{n}'" for n in names) + "]"
    data_yaml.write_text(
        f"path: {out.as_posix()}\n"
        f"train: train/images\n"
        f"val: val/images\n"
        f"nc: {nc}\n"
        f"names: {names_str}\n",
        encoding='utf-8')

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"COCO json : {json_path}")
    print(f"Classes   : {nc} (index 0 '{names[0]}' is the unused placeholder)")
    print(f"Split     : {counts['train']} train / {counts['val']} val "
          f"({counts['val']/(sum(counts.values()) or 1):.0%} val)")
    print(f"Val clips : {sorted(val_clips)}")
    print(f"data.yaml : {data_yaml}")

    print("\nPer-class instances (train | val):")
    rare = []
    for i in range(nc):
        if i == 0:
            continue
        tr, va = cls_per_split['train'][i], cls_per_split['val'][i]
        if tr + va == 0:
            continue
        flag = '  <-- few train samples' if tr < 10 else ''
        if tr < 10:
            rare.append(names[i])
        print(f"  {i:2d} {names[i]:30s} {tr:4d} | {va:3d}{flag}")
    if rare:
        print(f"\nWARNING: {len(rare)} class(es) have <10 train instances "
              f"({', '.join(rare)}).\n"
              "         Their AP will be unreliable — collect more crops for "
              "these logos (the track-propagation trick helps).")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--coco_dir', default='../logo-dataset/train',
                   help='Folder with _annotations.coco.json + images')
    p.add_argument('--out_dir',  default='data', help='Output YOLO dataset dir')
    p.add_argument('--val_frac', type=float, default=0.18)
    p.add_argument('--seed',     type=int,   default=None,
                   help='Fix the clip-split seed; default None searches seeds '
                        'for the most train-balanced clip split')
    p.add_argument('--clean',    action='store_true',
                   help='Wipe out_dir before writing')
    main(p.parse_args())
