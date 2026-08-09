"""Bootstrap dataset — nhãn brand đã verify → YOLO-cls dataset (docs/12 M3).

Triết lý v3 "ít nhưng ĐÚNG": KHÔNG lấy cả cụm (bẩn — board lẫn jersey), chỉ lấy
**crop-anchor đã verify** (OCR read link tới, brand khớp) rồi **lan theo track**
(cùng tid, cùng (u,v) trên thân = cùng bề mặt) để nhân số mà giữ purity.

Split **track-disjoint** (val = track chưa thấy) — chống leakage near-duplicate
(bài học docs/12: random-crop split thổi 0.92, track-disjoint hạ về 0.56 thật).

`--append`: gộp thêm crop vào ds có sẵn → tích lũy qua NHIỀU TRẬN (flywheel).

    python inventory/build_bootstrap_ds.py --approved data/inventory/approved26.json \
        --links data/inventory/cluster_ocr26_fw45.links.json \
        --jersey data/inventory/jersey26 --out data/inventory/boot_ds --val-frac 0.3
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

UV_TOL = 0.1        # bán kính (u,v) coi là cùng bề mặt khi lan theo track


def load_on_white(p: Path):
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0
        im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    return im


def _quality_ok(crop_dir: Path, name: str, min_px: int, min_lap: float) -> bool:
    """Quality-gate v3 (docs/12): đủ to + đủ nét → chống lan nhãn vào frame mờ/blob."""
    im = load_on_white(crop_dir / f"{name}.png")
    if im is None or max(im.shape[:2]) < min_px:
        return False
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY) if im.ndim == 3 else im
    return float(cv2.Laplacian(g, cv2.CV_64F).var()) >= min_lap


def collect(approved: dict, links: dict, jersey_meta: dict, crop_dir: Path,
            uv_tol: float = UV_TOL, min_px: int = 24, min_lap: float = 40.0
            ) -> dict[str, dict[str, int]]:
    """→ {brand: {crop_name: tid}} qua anchor + lan theo track + quality-gate.

    Anchor crop (đã verify) LUÔN giữ; crop lan thêm phải qua gate nét/to (v3).
    """
    by_tid = defaultdict(list)
    for name, m in jersey_meta.items():
        by_tid[m["tid"]].append(m)
    out: dict[str, dict[str, int]] = defaultdict(dict)
    for cid, brand in approved.items():
        for lk in links.get(str(cid), []):
            if lk["brand"] != brand:
                continue
            seed = jersey_meta.get(lk["crop"])
            if seed is None:
                continue
            out[brand][lk["crop"]] = seed["tid"]          # anchor: giữ vô điều kiện
            for m in by_tid[seed["tid"]]:
                if m["name"] == lk["crop"]:
                    continue
                if abs(m["u"] - seed["u"]) < uv_tol and abs(m["v"] - seed["v"]) < uv_tol \
                        and _quality_ok(crop_dir, m["name"], min_px, min_lap):
                    out[brand][m["name"]] = m["tid"]
    return out


def track_disjoint_split(crops: dict[str, dict[str, int]], val_frac: float, seed: int):
    """Giữ nguyên track không tách 2 phía. Mỗi brand: bốc track cho val tới val_frac
    crop, nhưng luôn chừa ≥1 track train. Brand 1-track → toàn bộ vào train (val trống)."""
    import random
    rng = random.Random(seed)
    split = {}  # crop_name -> 'train'|'val'
    for brand, cd in crops.items():
        tid_crops = defaultdict(list)
        for name, tid in cd.items():
            tid_crops[tid].append(name)
        tids = list(tid_crops)
        rng.shuffle(tids)
        n_total = len(cd)
        val_tids, n_val = set(), 0
        for t in tids:
            if len(val_tids) >= len(tids) - 1:      # chừa ≥1 track train
                break
            if n_val >= val_frac * n_total:
                break
            val_tids.add(t); n_val += len(tid_crops[t])
        for name, tid in cd.items():
            split[name] = "val" if tid in val_tids else "train"
    return split


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved", required=True, help="JSON {cid: brand} (CONFIRMED + LIKELY đã duyệt)")
    ap.add_argument("--links", required=True)
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--val-frac", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-px", type=int, default=24, help="quality-gate: cạnh dài tối thiểu")
    ap.add_argument("--min-lap", type=float, default=40.0, help="quality-gate: Laplacian var")
    ap.add_argument("--append", action="store_true", help="gộp vào ds có sẵn (flywheel đa trận)")
    a = ap.parse_args()

    approved = json.loads(Path(a.approved).read_text(encoding="utf-8"))
    links = json.loads(Path(a.links).read_text(encoding="utf-8"))
    jm = {m["name"]: m for m in
          (json.loads(l) for l in (a.jersey / "meta.jsonl").read_text().splitlines())}
    crop_dir = a.jersey / "crops"

    crops = collect(approved, links, jm, crop_dir, min_px=a.min_px, min_lap=a.min_lap)
    split = track_disjoint_split(crops, a.val_frac, a.seed)

    if not a.append and a.out.exists():
        shutil.rmtree(a.out)
    tag = a.jersey.name         # tránh trùng tên khi gộp nhiều trận
    n = defaultdict(lambda: defaultdict(int))
    for brand, cd in crops.items():
        for name in cd:
            sp = split[name]
            d = a.out / sp / brand
            d.mkdir(parents=True, exist_ok=True)
            im = load_on_white(crop_dir / f"{name}.png")
            if im is None:
                continue
            cv2.imwrite(str(d / f"{tag}_{name}.png"), im)
            n[sp][brand] += 1

    print(f"{'brand':12} {'train':>6} {'val':>6}")
    for brand in sorted(crops):
        print(f"  {brand:12} {n['train'][brand]:>6} {n['val'][brand]:>6}")
    tot_tr = sum(n['train'].values()); tot_va = sum(n['val'].values())
    print(f"  {'TOTAL':12} {tot_tr:>6} {tot_va:>6}  → {a.out}")
    # cảnh báo brand degenerate (không đủ track cho val)
    for brand in sorted(crops):
        if n['val'][brand] == 0:
            print(f"  ⚠ {brand}: 0 val (chỉ 1 track) → val không đo được brand này")


if __name__ == "__main__":
    main()
