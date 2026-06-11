"""
Merge the 32 home/away logo classes into ~17 brand classes.

Downstream measures sponsor-logo *coverage* (which sponsor is visible), which is
kit-agnostic: home vs away is recoverable from clip metadata, so the detector
should not be burdened with separating two visually-near-identical variants of
the same logo. Merging doubles data per brand, removes the hardest home<->away
confusions, and rescues rare *_home classes.

What it does (in-place on the current train/ + val/ split):
  * backs up existing labels + data.yaml to data/_backup_32class/
  * strips the _home/_away suffix -> brand classes, remaps every label file's
    first token (box AND segment rows are preserved; only the class id changes)
  * rewrites data.yaml (nc, names)
  * deletes stale labels.cache

Re-runnable check: if data.yaml already has the merged (brand) names it aborts.

    python scripts/merge_home_away.py
"""

import re
import shutil
from collections import Counter
from pathlib import Path

import yaml

DATA_DIR = Path(r"C:\Users\xmai\Bradford\bradford_bull_v2\logo_detection\data")
SPLITS = ["train", "val"]


def brand_of(name: str) -> str:
    return re.sub(r"_(home|away)$", "", name)


def main():
    yaml_path = DATA_DIR / "data.yaml"
    cfg = yaml.safe_load(yaml_path.read_text())
    old_names = list(cfg["names"])

    # Build brand list preserving first-appearance order
    brands, brand_index = [], {}
    for n in old_names:
        b = brand_of(n)
        if b not in brand_index:
            brand_index[b] = len(brands)
            brands.append(b)

    if len(brands) == len(old_names):
        raise SystemExit("No home/away suffixes to merge — already brand-level. Aborting.")

    old_to_new = {i: brand_index[brand_of(n)] for i, n in enumerate(old_names)}

    print(f"Merging {len(old_names)} -> {len(brands)} classes")
    for i, n in enumerate(old_names):
        print(f"  {i:>2} {n:<28} -> {old_to_new[i]:>2} {brands[old_to_new[i]]}")

    # 1) Backup
    backup = DATA_DIR / "_backup_32class"
    if backup.exists():
        raise SystemExit(f"{backup} already exists — refusing to overwrite a backup.")
    backup.mkdir()
    shutil.copy2(yaml_path, backup / "data.yaml")
    for sp in SPLITS:
        src = DATA_DIR / sp / "labels"
        if src.exists():
            shutil.copytree(src, backup / sp / "labels")
    print(f"\nBacked up original labels + data.yaml -> {backup}")

    # 2) Remap labels (only the first token of each row)
    counts = Counter()
    for sp in SPLITS:
        lbl_dir = DATA_DIR / sp / "labels"
        if not lbl_dir.exists():
            continue
        for txt in lbl_dir.glob("*.txt"):
            out = []
            for line in txt.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                new_id = old_to_new[int(parts[0])]
                parts[0] = str(new_id)
                counts[new_id] += 1
                out.append(" ".join(parts))
            txt.write_text("\n".join(out) + ("\n" if out else ""))

    # 3) Rewrite data.yaml
    cfg["nc"] = len(brands)
    cfg["names"] = brands
    yaml_path.write_text(yaml.dump(cfg, allow_unicode=True, sort_keys=False))

    # 4) Drop caches
    for c in DATA_DIR.rglob("labels.cache"):
        c.unlink()

    print(f"\ndata.yaml updated: nc={len(brands)}")
    print("Per-brand instance counts (train+val):")
    for i, b in enumerate(brands):
        print(f"  {i:>2} {b:<28} {counts[i]:>5}")
    print("\nDone. To revert: restore data/_backup_32class/ over data/.")


if __name__ == "__main__":
    main()
