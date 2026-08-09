"""Montage AUDIT cho nhãn fused (docs/12 — gold người 30', bắt buộc trước khi tin số).

Mỗi cụm inventory đã fuse → 1 hàng: header (cid/slot/status/brand + bằng chứng từng
kênh) + strip crop NÉT NHẤT phóng to (crop broadcast ~20-50px → upscale để đọc logo).
Người soi: (i) cụm có thuần 1 bề mặt không; (ii) brand có đúng logo hiện trên crop
không; (iii) slot (chest/abdomen/legs) có đúng không. CONFIRMED tô xanh, UNCERTAIN cam.

    python inventory/montage_audit.py \
        --fused    data/inventory/anchor_fused26.json \
        --clusters data/inventory/clusters26/clusters.json \
        --jersey   data/inventory/jersey26 \
        --out      data/inventory/audit26
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

CELL = 108          # cạnh ô crop sau upscale (đủ đọc logo)
NCELL = 12          # số crop/hàng
PAD = 6
ROWS_PER_PAGE = 8   # số cụm/ảnh (tránh PNG quá cao)


def _load_on_white(p: Path):
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if im is None:
        return None
    if im.ndim == 3 and im.shape[2] == 4:
        a = im[:, :, 3:4] / 255.0
        im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    elif im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    return im


def _sharp(im) -> float:
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())


def _cell(im) -> np.ndarray:
    """Upscale crop giữ tỉ lệ, letterbox trắng về CELL×CELL."""
    h, w = im.shape[:2]
    s = (CELL - 8) / max(h, w)
    r = cv2.resize(im, (max(1, int(w * s)), max(1, int(h * s))),
                   interpolation=cv2.INTER_LANCZOS4 if s > 1 else cv2.INTER_AREA)
    out = np.full((CELL, CELL, 3), 250, np.uint8)
    yo, xo = (CELL - r.shape[0]) // 2, (CELL - r.shape[1]) // 2
    out[yo:yo + r.shape[0], xo:xo + r.shape[1]] = r
    cv2.rectangle(out, (0, 0), (CELL - 1, CELL - 1), (220, 220, 220), 1)
    return out


def _header(width: int, r: dict) -> np.ndarray:
    d = r["detail"]
    ocr = f"{d['ocr'][0]}={d['ocr'][1]}" if d["ocr"] else "-"
    geo = f"{d['geo'][0]}={d['geo'][1]}" if d["geo"] else "-"
    kit = ",".join(d["kit"]) if d["kit"] else "-"
    bg = {"CONFIRMED": (60, 140, 40),     # xanh lá
          "LIKELY": (40, 160, 200),       # vàng-cam (chờ người duyệt)
          "UNCERTAIN": (30, 110, 190),    # cam
          }.get(r["status"], (110, 110, 110))  # UNKNOWN xám (BGR)
    h = np.full((46, width, 3), bg, np.uint8)
    cv2.putText(h, f"C{r['cid']}  {r['slot']}  n={r['n']}  ->  "
                   f"{r['status']}: {r['brand']}", (8, 19),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(h, f"OCR[{ocr}]  GEO[{geo}]  KIT[{kit}]", (8, 39),
                cv2.FONT_HERSHEY_SIMPLEX, 0.44, (245, 245, 245), 1)
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fused", required=True, type=Path)
    ap.add_argument("--clusters", required=True, type=Path)
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--links", default=None,
                    help="anchor_link .links.json → hiện crop ĐƯỢC-LINK (bằng chứng), "
                         "không phải sharpest (sharpest gây hiểu lầm ở cụm bẩn)")
    ap.add_argument("--confirmed-only", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    links = (json.loads(Path(a.links).read_text(encoding="utf-8"))
             if a.links and Path(a.links).exists() else None)
    fused = json.loads(a.fused.read_text(encoding="utf-8"))
    clusters = {c["cid"]: c for c in json.loads(a.clusters.read_text(encoding="utf-8"))}
    meta = {}
    for ln in (a.jersey / "meta.jsonl").read_text(encoding="utf-8").splitlines():
        m = json.loads(ln)
        meta[m["name"]] = m
    crop_dir = a.jersey / "crops"

    if a.confirmed_only:
        fused = [r for r in fused if r["status"] == "CONFIRMED"]
    width = NCELL * CELL + (NCELL + 1) * PAD

    rows_all = []
    for r in fused:
        c = clusters.get(r["cid"])
        if not c:
            continue
        cells = []
        link_list = (links or {}).get(str(r["cid"]))
        if link_list is not None:
            # BẰNG CHỨNG ANCHOR: crop mà OCR read thực sự link tới (không phải sharpest)
            for lk in link_list[:NCELL]:
                im = _load_on_white(crop_dir / f"{lk['crop']}.png")
                if im is None:
                    continue
                cell = _cell(im)
                cv2.putText(cell, lk["brand"], (3, CELL - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 2)
                cells.append(cell)
        else:
            scored = []
            for name in c["members"]:
                im = _load_on_white(crop_dir / f"{name}.png")
                if im is None:
                    continue
                size = max(meta.get(name, {}).get("wh", im.shape[:2]))
                scored.append((_sharp(im) * size, im))
            scored.sort(key=lambda x: -x[0])
            cells = [_cell(im) for _, im in scored[:NCELL]]
        while len(cells) < NCELL:
            cells.append(np.full((CELL, CELL, 3), 250, np.uint8))
        strip = np.full((CELL, width, 3), 255, np.uint8)
        for i, cell in enumerate(cells):
            x = PAD + i * (CELL + PAD)
            strip[0:CELL, x:x + CELL] = cell
        rows_all.append(np.vstack([_header(width, r),
                                   np.full((PAD, width, 3), 255, np.uint8), strip,
                                   np.full((PAD * 2, width, 3), 255, np.uint8)]))

    # phân trang
    pages = [rows_all[i:i + ROWS_PER_PAGE] for i in range(0, len(rows_all), ROWS_PER_PAGE)]
    paths = []
    for pi, page in enumerate(pages):
        img = np.vstack(page)
        p = a.out / f"audit_page{pi+1}.png"
        cv2.imwrite(str(p), img)
        paths.append(p)
    n_conf = sum(r["status"] == "CONFIRMED" for r in fused)
    print(f"[audit] {len(fused)} cụm ({n_conf} CONFIRMED) → {len(paths)} trang")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
