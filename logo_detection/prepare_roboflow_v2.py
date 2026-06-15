#!/usr/bin/env python3
r"""
Convert the new Roboflow COCO export (C:\Users\xmai\roboflow) into a YOLO dataset
ready for yolo26 training, in ONE pass:

  * drops Roboflow's placeholder category 0 ("Auto-Black", 0 instances)
  * merges the 32 *_home / *_away classes -> 17 brand classes, in the SAME order
    as the existing logo_detection/data/data.yaml so the trained model stays
    drop-in compatible with downstream (orchestrator / registry expect that order)
  * clip-aware train/val split: whole matches (M\d+) and whole clips (clip_\d+)
    stay on one side, so val measures generalisation to unseen footage (frames are
    ~2 fps -> consecutive frames are near-duplicates; a random split would leak)
  * keeps the 721 un-annotated images as YOLO background (empty label) by default
    (--drop_backgrounds to exclude them) and reports how many there are
  * writes data_v2/{train,val}/{images,labels} + data_v2/data.yaml

Usage (env: bradford_bulls):
    python prepare_roboflow_v2.py
    python prepare_roboflow_v2.py --val_frac 0.18 --drop_backgrounds
"""
import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Preserve the EXACT 17-brand order of the existing trained pipeline.
BRAND_ORDER = [
    "acs_group", "aon", "atm", "bartercard", "cch", "chadlaw", "ellgren",
    "em_workwear", "fairway", "floor_tonic", "klg", "mcp", "mna_cladding",
    "mna_support_service", "paints_lacquers", "romantica", "top_notch",
]
BRAND_IDX = {b: i for i, b in enumerate(BRAND_ORDER)}


def brand_of(name: str) -> str:
    return re.sub(r"_(home|away)$", "", name)


def group_key(file_name: str) -> str:
    """Whole match (M01..) or whole source clip (clip_007) -> one group."""
    m = re.match(r"^(M\d+)", file_name)
    if m:
        return m.group(1)
    m = re.match(r"^(clip_\d+)", file_name)
    if m:
        return m.group(1)
    return file_name  # fallback: its own group


def _one_split(by_group, groups, val_frac, total, seed):
    import random
    order = list(groups)
    random.Random(seed).shuffle(order)
    target, val_groups, n_val = total * val_frac, set(), 0
    for g in order:
        if n_val >= target:
            break
        val_groups.add(g)
        n_val += len(by_group[g])
    return val_groups


def split_groups(images, anns_by, brand_of_cat, val_frac, seed):
    """Search seeds; pick the clip-aware split that keeps every brand mostly in
    TRAIN (so rare logos stay learnable) while staying near the val target."""
    by_group = defaultdict(list)
    for im in images:
        by_group[group_key(im["file_name"])].append(im)
    groups = sorted(by_group)
    total = len(images)

    def score(val_groups):
        val_ids = {im["id"] for g in val_groups for im in by_group[g]}
        tr, va = Counter(), Counter()
        for im in images:
            tgt = va if im["id"] in val_ids else tr
            for a in anns_by.get(im["id"], []):
                b = brand_of_cat.get(a["category_id"])
                if b is not None:
                    tgt[b] += 1
        bad = sum(1 for c in set(tr) | set(va) if tr[c] < 0.6 * (tr[c] + va[c]))
        frac_dev = abs(len(val_ids) / (total or 1) - val_frac)
        return (bad, frac_dev)

    if seed is not None:
        best = _one_split(by_group, groups, val_frac, total, seed)
    else:
        cand = [_one_split(by_group, groups, val_frac, total, s) for s in range(300)]
        best = min(cand, key=score)

    val_ids = {im["id"] for g in best for im in by_group[g]}
    return val_ids, best


def to_yolo_box(bbox, w, h):
    x, y, bw, bh = bbox
    return (x + bw / 2) / w, (y + bh / 2) / h, bw / w, bh / h


def main(args):
    coco_dir = Path(args.coco_dir).resolve()
    json_path = coco_dir / "_annotations.coco.json"
    if not json_path.exists():
        cands = list(coco_dir.glob("*.json"))
        if not cands:
            raise SystemExit(f"No COCO json in {coco_dir}")
        json_path = cands[0]

    d = json.loads(json_path.read_text(encoding="utf-8"))
    cats = {c["id"]: c["name"] for c in d["categories"]}

    # category_id -> merged brand index (drop placeholder + anything not a brand)
    brand_of_cat = {}
    skipped_cats = []
    for cid, name in cats.items():
        b = brand_of(name)
        if b in BRAND_IDX:
            brand_of_cat[cid] = BRAND_IDX[b]
        else:
            skipped_cats.append(name)

    images = {im["id"]: im for im in d["images"]}
    anns_by = defaultdict(list)
    for a in d["annotations"]:
        if a["category_id"] in brand_of_cat:  # silently drop placeholder anns (none here)
            anns_by[a["image_id"]].append(a)

    n_bg = sum(1 for iid in images if not anns_by.get(iid))
    val_ids, val_groups = split_groups(
        d["images"], anns_by, brand_of_cat, args.val_frac, args.seed)

    out = (HERE / args.out_dir).resolve()
    if out.exists() and args.clean:
        shutil.rmtree(out)
    for sp in ("train", "val"):
        (out / sp / "images").mkdir(parents=True, exist_ok=True)
        (out / sp / "labels").mkdir(parents=True, exist_ok=True)

    counts = Counter()
    bg_per = {"train": 0, "val": 0}
    cls_per = {"train": Counter(), "val": Counter()}
    for img_id, im in images.items():
        is_bg = not anns_by.get(img_id)
        if is_bg and args.drop_backgrounds:
            continue
        sp = "val" if img_id in val_ids else "train"
        fn = im["file_name"]
        w, h = im["width"], im["height"]
        src = coco_dir / fn
        if not src.exists():
            print(f"  WARNING missing image {fn} — skipped")
            continue
        shutil.copy2(src, out / sp / "images" / fn)

        lines = []
        for a in anns_by.get(img_id, []):
            cx, cy, bw, bh = to_yolo_box(a["bbox"], w, h)
            cls = brand_of_cat[a["category_id"]]
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            cls_per[sp][cls] += 1
        (out / sp / "labels" / (Path(fn).stem + ".txt")).write_text(
            "\n".join(lines), encoding="utf-8")
        counts[sp] += 1
        if is_bg:
            bg_per[sp] += 1

    names_str = "[" + ", ".join(f"'{n}'" for n in BRAND_ORDER) + "]"
    (out / "data.yaml").write_text(
        f"path: {out.as_posix()}\n"
        f"train: train/images\n"
        f"val: val/images\n"
        f"nc: {len(BRAND_ORDER)}\n"
        f"names: {names_str}\n",
        encoding="utf-8")

    # ── Report ──────────────────────────────────────────────────────────────
    print(f"COCO json : {json_path}")
    if skipped_cats:
        print(f"Dropped categories (not a brand): {skipped_cats}")
    tot = counts["train"] + counts["val"]
    print(f"Split     : {counts['train']} train / {counts['val']} val "
          f"({counts['val']/(tot or 1):.0%} val)")
    if args.drop_backgrounds:
        print(f"Background: {n_bg} un-annotated images DROPPED")
    else:
        print(f"Background: {n_bg} un-annotated images kept "
              f"(train {bg_per['train']}, val {bg_per['val']})")
    print(f"Val groups: {sorted(val_groups)}")
    print(f"data.yaml : {out / 'data.yaml'}")
    print("\nPer-brand instances (train | val):")
    for i, b in enumerate(BRAND_ORDER):
        tr, va = cls_per["train"][i], cls_per["val"][i]
        flag = "  <-- few train" if tr < 20 else ("  <-- 0 in val" if va == 0 else "")
        print(f"  {i:2d} {b:24s} {tr:5d} | {va:4d}{flag}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--coco_dir", default=r"C:\Users\xmai\roboflow\train")
    p.add_argument("--out_dir", default="data")
    p.add_argument("--val_frac", type=float, default=0.18)
    p.add_argument("--seed", type=int, default=None,
                   help="fix split seed; default searches 300 seeds for balance")
    p.add_argument("--drop_backgrounds", action="store_true",
                   help="exclude the un-annotated images instead of keeping as background")
    p.add_argument("--clean", action="store_true", help="wipe out_dir first")
    main(p.parse_args())
