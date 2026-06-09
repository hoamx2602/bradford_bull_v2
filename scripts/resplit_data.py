"""
Group-aware (clip-level) resplit of the YOLO logo dataset.

WHY group split instead of random:
    ~2140/2456 frames are consecutive video frames (clip_XXX, sampled ~1s apart).
    Frames 1s apart in the same clip are near-duplicates. A random per-image split
    leaks near-identical scenes into val -> val mAP is inflated and does NOT reflect
    performance on unseen matches. We therefore keep whole clips together: a clip
    goes entirely to train OR val. The sparse `stratum_*` frames are temporally
    independent, so each is its own group (frame-level split is safe for them).

The split is also class-aware: rare classes are forced to get some val coverage
first, then val is filled up to ~VAL_RATIO. Per-class train/val counts are printed
so you can SEE the balance before trusting the metric.

Usage:
    python scripts/resplit_data.py --dry-run     # preview, writes nothing
    python scripts/resplit_data.py               # perform the split
"""

import argparse
import re
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import yaml

DATA_DIR = Path(r"C:\Users\xmai\Bradford\bradford_bull_v2\logo_detection\data")
VAL_RATIO = 0.20
SEED = 42
SOURCES = ["train", "valid", "val", "test"]
IMG_EXT = {".jpg", ".jpeg", ".png"}


def group_key(stem: str) -> str:
    """clip_XXX frames -> grouped by clip; stratum frames -> their own group."""
    m = re.match(r"^(clip_\d+)", stem)
    return m.group(1) if m else stem


def classes_in(lbl: Path) -> list[int]:
    if not lbl.exists():
        return []
    out = []
    for line in lbl.read_text().splitlines():
        line = line.strip()
        if line:
            out.append(int(line.split()[0]))
    return out


def pool_samples() -> list[tuple[Path, Path]]:
    samples, seen = [], set()
    for src in SOURCES:
        img_dir = DATA_DIR / src / "images"
        lbl_dir = DATA_DIR / src / "labels"
        if not img_dir.exists():
            continue
        for img in sorted(img_dir.iterdir()):
            if img.suffix.lower() not in IMG_EXT or img.stem in seen:
                continue
            seen.add(img.stem)
            samples.append((img, lbl_dir / (img.stem + ".txt")))
    return samples


def build_groups(samples):
    groups = defaultdict(lambda: {"items": [], "counts": Counter()})
    for img, lbl in samples:
        g = groups[group_key(img.stem)]
        g["items"].append((img, lbl))
        for c in classes_in(lbl):
            g["counts"][c] += 1
    return dict(groups)


def split_groups(groups, total, n_images):
    """Greedy multi-label stratification at the GROUP level.

    Process groups largest-first; assign each whole group to the split (train or
    val) that currently has the largest unmet 'desire' for the classes in that
    group. Because train's desired share is 4x val's, rare classes (concentrated
    in 1-2 clips) naturally land in TRAIN where they can actually be learned, and
    val stays close to VAL_RATIO without overshooting.
    """
    rng = random.Random(SEED)
    keys = list(groups)
    rng.shuffle(keys)  # tie-break deterministically
    keys.sort(key=lambda k: sum(groups[k]["counts"].values()), reverse=True)

    desired = {
        "train": {c: (1 - VAL_RATIO) * total[c] for c in total},
        "val": {c: VAL_RATIO * total[c] for c in total},
    }
    have = {"train": Counter(), "val": Counter()}
    imgs = {"train": 0, "val": 0}
    val_cap = round(VAL_RATIO * n_images) * 1.10  # 10% slack, no big overshoot
    assigned = {}

    def need(split, g):
        return sum(max(0.0, desired[split][c] - have[split][c]) * cnt
                   for c, cnt in g["counts"].items())

    for k in keys:
        g = groups[k]
        n = len(g["items"])
        if not g["counts"] or imgs["val"] + n > val_cap:
            choice = "train"
        else:
            choice = "val" if need("val", g) > need("train", g) else "train"
        assigned[k] = choice
        have[choice].update(g["counts"])
        imgs[choice] += n
    return assigned


def report(groups, assigned, total, names):
    tr_c, va_c, tr_i, va_i = Counter(), Counter(), 0, 0
    tr_clips, va_clips = 0, 0
    for k, where in assigned.items():
        n = len(groups[k]["items"])
        if where == "val":
            va_c.update(groups[k]["counts"]); va_i += n; va_clips += 1
        else:
            tr_c.update(groups[k]["counts"]); tr_i += n; tr_clips += 1

    print(f"\n{'class':<28}{'train':>7}{'val':>7}{'val%':>7}")
    print("-" * 49)
    zero = []
    for c in sorted(total):
        t, v = tr_c[c], va_c[c]
        pct = (100 * v / total[c]) if total[c] else 0
        flag = "  <-- 0 in val" if v == 0 else ("  <-- rare" if total[c] < 50 else "")
        if v == 0:
            zero.append(names[c])
        print(f"{names[c]:<28}{t:>7}{v:>7}{pct:>6.0f}%{flag}")
    print("-" * 49)
    print(f"{'IMAGES':<28}{tr_i:>7}{va_i:>7}")
    print(f"{'GROUPS (clips+frames)':<28}{tr_clips:>7}{va_clips:>7}")
    if zero:
        print(f"\n[WARN] {len(zero)} class(es) have 0 val samples (too rare to "
              f"cover at clip level): {', '.join(zero)}")
        print("       -> their mAP cannot be measured. Collect more data for these.")


def write_split(items, img_dir, lbl_dir):
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    for img, lbl in items:
        shutil.copy2(img, img_dir / img.name)
        if lbl.exists():
            shutil.copy2(lbl, lbl_dir / lbl.name)


def update_yaml():
    p = DATA_DIR / "data.yaml"
    cfg = yaml.safe_load(p.read_text())
    cfg["path"] = str(DATA_DIR).replace("\\", "/")
    cfg["train"] = "train/images"
    cfg["val"] = "val/images"
    cfg.pop("test", None)
    p.write_text(yaml.dump(cfg, allow_unicode=True, sort_keys=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load((DATA_DIR / "data.yaml").read_text())
    names = cfg["names"]

    samples = pool_samples()
    groups = build_groups(samples)
    total = Counter()
    for g in groups.values():
        total.update(g["counts"])

    print(f"Pooled {len(samples)} images into {len(groups)} groups "
          f"(clips kept whole, stratum frames individual).")
    assigned = split_groups(groups, total, len(samples))
    report(groups, assigned, total, names)

    if args.dry_run:
        print("\n[dry-run] nothing written.")
        return

    tr = [it for k, w in assigned.items() if w == "train" for it in groups[k]["items"]]
    va = [it for k, w in assigned.items() if w == "val" for it in groups[k]["items"]]

    print("\nWriting splits to temp dirs...")
    write_split(tr, DATA_DIR / "_train_new" / "images", DATA_DIR / "_train_new" / "labels")
    write_split(va, DATA_DIR / "_val_new" / "images", DATA_DIR / "_val_new" / "labels")

    for old in ["train", "valid", "val", "test"]:
        if (DATA_DIR / old).exists():
            shutil.rmtree(DATA_DIR / old)
    (DATA_DIR / "_train_new").rename(DATA_DIR / "train")
    (DATA_DIR / "_val_new").rename(DATA_DIR / "val")

    for cache in DATA_DIR.rglob("labels.cache"):
        cache.unlink()
    update_yaml()
    print("Done. data.yaml updated (train/images, val/images; test removed).")


if __name__ == "__main__":
    main()
