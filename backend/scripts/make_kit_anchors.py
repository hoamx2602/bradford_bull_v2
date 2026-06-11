#!/usr/bin/env python3
"""Generate kit-anchor crops from the official kit sheets — zero manual work.

Slices the front/back jersey torso out of KIT/Home Kit.jpg and KIT/Away
Kit.jpg (both use the same Fourex layout) and writes them to
data/kit_anchors/<kit>/. The team-filter bootstrap then picks the target
cluster by similarity to these official-kit crops instead of the luminance
heuristic — anchored to ground truth, still fully automatic.

Usage (from backend/):
    python scripts/make_kit_anchors.py            # both kits
    python scripts/make_kit_anchors.py --kit away # one kit
Re-run only if the kit images change.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

KIT_IMAGES = {
    "away": REPO_ROOT / "KIT" / "Away Kit.jpg",
    "home": REPO_ROOT / "KIT" / "Home Kit.jpg",
}

# Jersey torso regions as fractions of the kit-sheet image (same Fourex
# template for both kits): front jersey on the left, back jersey on the right.
CROPS = {
    "front": (0.12, 0.20, 0.36, 0.62),   # x1, y1, x2, y2
    "back":  (0.66, 0.16, 0.92, 0.60),
}


def make_anchors(kit: str, out_root: Path) -> list[Path]:
    img_path = KIT_IMAGES[kit]
    img = cv2.imread(str(img_path))
    if img is None:
        sys.exit(f"cannot read kit image: {img_path}")
    h, w = img.shape[:2]

    out_dir = out_root / kit
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, (fx1, fy1, fx2, fy2) in CROPS.items():
        crop = img[int(fy1 * h):int(fy2 * h), int(fx1 * w):int(fx2 * w)]
        p = out_dir / f"{name}.jpg"
        cv2.imwrite(str(p), crop)
        written.append(p)
        print(f"  {kit}/{name}.jpg  {crop.shape[1]}x{crop.shape[0]}")
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kit", choices=["home", "away"], help="default: both")
    ap.add_argument("--out", type=Path, default=BACKEND_DIR / "data" / "kit_anchors")
    args = ap.parse_args()

    kits = [args.kit] if args.kit else list(KIT_IMAGES)
    print(f"writing anchors -> {args.out}")
    for kit in kits:
        make_anchors(kit, args.out)
    print("done — the bootstrap now picks the target cluster by these anchors.")


if __name__ == "__main__":
    main()
