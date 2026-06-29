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
from collections import Counter
from pathlib import Path

import cv2


def run(a) -> None:
    coco_dir = Path(a.coco)
    js = json.loads((coco_dir / "_annotations.coco.json").read_text())
    cats = {c["id"]: c["name"] for c in js["categories"]}
    imgs = {im["id"]: im for im in js["images"]}
    by_img: dict[int, list] = {}
    for ann in js["annotations"]:
        by_img.setdefault(ann["image_id"], []).append(ann)

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
    print(f"[coco] {len(ids)} ảnh → gallery {n_train} / test {len(ids)-n_train}")
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
    ap.add_argument("--split", type=float, default=0.6, help="tỉ lệ ảnh cho gallery")
    ap.add_argument("--pad", type=float, default=0.08)
    ap.add_argument("--yolo", action="store_true", help="xuất nhãn YOLO HBB")
    ap.add_argument("--seed", type=int, default=0)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
