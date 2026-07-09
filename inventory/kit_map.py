"""Kit-map — trích slot→brand từ ảnh kit chính thức (docs/12, nâng cấp theo
Kit Regulations: anchor không cần video, ảnh kit 300dpi đọc được mọi slot).

Cách làm (generic, không hard-code brand):
  1. Tách garment components: threshold vùng sáng (áo/quần/tất trắng trên nền
     tối của sheet mockup) → connected components đủ lớn.
  2. OCR full-sheet (easyocr) → mỗi text hit fuzzy-match vào lexicon tự sinh
     (`signage_ocr.classify`) → (brand, xy).
  3. Gán hit vào component chứa nó → kit_map.json:
     {component_id: {bbox, hits: [{brand, text, xy_rel}]}}
  4. Đặt tên component (front/back/shorts/socks) — bước duy nhất cần mắt người
     (30s/kit sheet): xem montage `kit_map_view.jpg` rồi điền `--names`.

    python inventory/kit_map.py --kit "KIT/Home Kit.jpg" --lex data/lexicon.json \
        --out data/inventory/kitmap_home.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "auto_label"))
from signage_ocr import classify, _reader  # noqa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", required=True)
    ap.add_argument("--lex", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--thr", type=float, default=0.8)
    ap.add_argument("--names", default=None,
                    help="JSON: {component_id: slot_name} sau khi xem montage")
    a = ap.parse_args()

    im = cv2.imread(a.kit)
    H, W = im.shape[:2]
    # 1) garment components: vùng sáng trên nền tối
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(g, 90, 255, cv2.THRESH_BINARY)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    ncc, lab, stats, _ = cv2.connectedComponentsWithStats(bw, 8)
    comps = []
    for i in range(1, ncc):
        x, y, w, h, area = stats[i]
        if area < 0.002 * H * W or w > 0.9 * W:   # bỏ mảnh vụn + khung nền
            continue
        comps.append({"id": len(comps), "bbox": [int(x), int(y), int(w), int(h)]})

    # 2) OCR full-sheet (chia 2 nửa để giữ độ nét — sheet 3508px)
    reader = _reader()
    hits = []
    for x_off in (0, W // 2):
        part = im[:, x_off:x_off + W // 2 + 100]
        for box, text, conf in reader.readtext(part):
            if conf < 0.3:
                continue
            brand, sc = classify(text, json.loads(Path(a.lex).read_text(encoding="utf-8")), thr=a.thr)
            if brand == "unknown":
                continue
            xs = [p[0] + x_off for p in box]; ys = [p[1] for p in box]
            hits.append({"brand": brand, "text": text,
                         "xy": [int(sum(xs) / 4), int(sum(ys) / 4)],
                         "conf": round(float(conf), 2)})

    # 3) gán hit vào component
    for h_ in hits:
        h_["comp"] = -1
        for c in comps:
            x, y, w, hh = c["bbox"]
            if x <= h_["xy"][0] <= x + w and y <= h_["xy"][1] <= y + hh:
                h_["comp"] = c["id"]
                break

    names = json.loads(a.names) if a.names else {}
    out = {"kit": a.kit, "components": comps, "hits": hits, "names": names}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) montage verify
    vis = im.copy()
    for c in comps:
        x, y, w, hh = c["bbox"]
        cv2.rectangle(vis, (x, y), (x + w, y + hh), (255, 160, 0), 6)
        cv2.putText(vis, f"#{c['id']}", (x + 8, y + 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 160, 0), 5)
    for h_ in hits:
        cv2.circle(vis, tuple(h_["xy"]), 14, (0, 0, 255), -1)
        cv2.putText(vis, f"{h_['brand']}", (h_["xy"][0] + 16, h_["xy"][1] + 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 4)
    s = 1300 / W
    cv2.imwrite(str(a.out.with_suffix(".view.jpg")),
                cv2.resize(vis, None, fx=s, fy=s), [cv2.IMWRITE_JPEG_QUALITY, 85])
    per = {}
    for h_ in hits:
        per.setdefault(h_["comp"], []).append(h_["brand"])
    print(f"[kitmap] {len(comps)} components, {len(hits)} brand hits")
    for cid, bs in sorted(per.items()):
        print(f"  comp#{cid}: {bs}")
    print(f"view: {a.out.with_suffix('.view.jpg')}")


if __name__ == "__main__":
    main()
