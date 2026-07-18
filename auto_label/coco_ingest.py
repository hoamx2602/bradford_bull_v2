"""Ingest COCO (Roboflow) → crop logo theo brand + split train/test + nhãn YOLO.

Dùng tập gán tay (vd `Auto Label White.coco`) ĐÚNG vai trò (xem analysis-log):
  - gallery (train split) → real crop nuôi Template DB Tầng 2 (vá điểm thấp).
  - test split → gold để đo recognizer (gt = brand thật).
  - (tùy chọn) xuất nhãn YOLO HBB cho localizer Tầng 1.

KHÔNG leakage: split ở mức ẢNH (crop cùng ảnh không rơi 2 bên).

    out/gallery/<brand>/*.jpg     out/test/<brand>/*.jpg     out/labels/*.txt (nếu --yolo)

Chạy:
    python auto_label/coco_ingest.py --coco "Auto Label White.coco/train" \
        --out data/real/coco --split 0.6 --pad 0.08
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import cv2

# clip/match key: "M01_white_1080p", "clip_014" — everything before the frame index
_CLIP_RE = re.compile(r"(M\d+_[a-z]+_\d+p|clip_\d+)", re.I)


def _clip_key(file_name: str) -> str:
    m = _CLIP_RE.match(Path(file_name).name)
    return m.group(1) if m else Path(file_name).stem.split("_")[0]


def _clip_disjoint_split(by_img, imgs, cats, target_gallery_frac, seed):
    """Assign whole clips to gallery/test so no clip straddles the split
    (frames of one clip are near-duplicates → random split leaks). Greedy:
    grow TEST with clips that add the most *new* brands first, until the test
    crop fraction is reached, while guaranteeing every brand keeps >=1 gallery
    crop. Returns {image_id: 'gallery'|'test'}."""
    clip_imgs: dict[str, list[int]] = defaultdict(list)
    clip_brands: dict[str, Counter] = defaultdict(Counter)
    total_crops = 0
    for img_id, anns in by_img.items():
        k = _clip_key(imgs[img_id]["file_name"])
        clip_imgs[k].append(img_id)
        for ann in anns:
            clip_brands[k][cats[ann["category_id"]]] += 1
            total_crops += 1
    brand_total = Counter()
    for c in clip_brands.values():
        brand_total.update(c)

    target_test = total_crops * (1.0 - target_gallery_frac)
    rng = random.Random(seed)
    clips = sorted(clip_imgs, key=lambda k: (-sum(clip_brands[k].values()), k))
    test_clips: set[str] = set()
    test_crops = 0
    test_brands: set[str] = set()
    gallery_brand = Counter(brand_total)  # crops left in gallery per brand
    # pass 1: greedily add clips that introduce the most new brands to test
    while test_crops < target_test:
        best, best_gain = None, -1
        for k in clips:
            if k in test_clips:
                continue
            # don't move a clip if it would zero-out a brand's gallery presence
            if any(gallery_brand[b] - clip_brands[k][b] <= 0 for b in clip_brands[k]):
                continue
            gain = len(set(clip_brands[k]) - test_brands)
            size = sum(clip_brands[k].values())
            score = gain * 1000 - size  # prefer new-brand coverage, then smaller
            if score > best_gain:
                best_gain, best = score, k
        if best is None:
            break
        test_clips.add(best)
        test_crops += sum(clip_brands[best].values())
        test_brands |= set(clip_brands[best])
        for b, n in clip_brands[best].items():
            gallery_brand[b] -= n
    split = {}
    for k, ids_ in clip_imgs.items():
        where = "test" if k in test_clips else "gallery"
        for i in ids_:
            split[i] = where
    print(f"[split] clip-disjoint: {len(test_clips)}/{len(clip_imgs)} clips -> test "
          f"({test_crops}/{total_crops} crops, {len(test_brands)}/{len(brand_total)} brands)")
    print(f"[split] test clips: {sorted(test_clips)}")
    return split


def run(a) -> None:
    coco_dir = Path(a.coco)
    js = json.loads((coco_dir / "_annotations.coco.json").read_text())
    cats = {c["id"]: c["name"] for c in js["categories"]}
    imgs = {im["id"]: im for im in js["images"]}
    by_img: dict[int, list] = {}
    for ann in js["annotations"]:
        by_img.setdefault(ann["image_id"], []).append(ann)

    if a.split_by == "clip":
        split = _clip_disjoint_split(by_img, imgs, cats, a.split, a.seed)
        n_train = sum(1 for v in split.values() if v == "gallery")
    else:
        ids = sorted(by_img)
        random.seed(a.seed); random.shuffle(ids)
        n_train = int(len(ids) * a.split)
        split = {i: ("gallery" if k < n_train else "test") for k, i in enumerate(ids)}

    out = Path(a.out)
    cnt: Counter = Counter()
    lbl_dir = out / "labels"; lbl_dir.mkdir(parents=True, exist_ok=True)
    for img_id, anns in by_img.items():
        im = imgs[img_id]
        path = coco_dir / im["file_name"]
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        H, W = frame.shape[:2]
        where = split[img_id]
        lines = []
        for ann in anns:
            x, y, w, h = ann["bbox"]
            brand = cats[ann["category_id"]]
            px = w * a.pad; py = h * a.pad
            x0 = max(int(x - px), 0); y0 = max(int(y - py), 0)
            x1 = min(int(x + w + px), W); y1 = min(int(y + h + py), H)
            crop = frame[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            d = out / where / brand; d.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(d / f"{img_id}_{ann['id']}.jpg"), crop)
            cnt[(where, brand)] += 1
            # YOLO HBB (class theo brand index) — cho localizer nếu cần
            cx, cy = (x + w / 2) / W, (y + h / 2) / H
            lines.append(f"{ann['category_id']} {cx:.6f} {cy:.6f} {w/W:.6f} {h/H:.6f}")
        if a.yolo:
            (lbl_dir / f"{Path(im['file_name']).stem}.txt").write_text("\n".join(lines))

    g = sum(v for (wq, _), v in cnt.items() if wq == "gallery")
    t = sum(v for (wq, _), v in cnt.items() if wq == "test")
    n_test_img = sum(1 for v in split.values() if v == "test")
    print(f"[coco] {len(split)} ảnh → gallery {len(split)-n_test_img} / test {n_test_img}")
    print(f"  crops: gallery {g}, test {t}, brands {len({b for _,b in cnt})}")
    per = Counter()
    for (wq, b), v in cnt.items():
        if wq == "test":
            per[b] += v
    print("  test crops/brand:", dict(per.most_common()))


def main() -> None:
    ap = argparse.ArgumentParser(description="COCO → gallery/test crops + YOLO")
    ap.add_argument("--coco", required=True, help="thư mục chứa _annotations.coco.json + ảnh")
    ap.add_argument("--out", default="data/real/coco")
    ap.add_argument("--split", type=float, default=0.6, help="tỉ lệ crop cho gallery")
    ap.add_argument("--split-by", choices=["image", "clip"], default="clip",
                    help="clip = disjoint theo trận/clip (tránh leak, mặc định); image = random")
    ap.add_argument("--pad", type=float, default=0.08)
    ap.add_argument("--yolo", action="store_true", help="xuất nhãn YOLO HBB")
    ap.add_argument("--seed", type=int, default=0)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
