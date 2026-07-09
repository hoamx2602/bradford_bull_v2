"""M1e — Anchor: định danh mỗi cụm inventory MỘT LẦN (docs/12).

Mỗi cụm (n đủ lớn): lấy K crop to nhất → upscale → OCR → fuzzy-match lexicon
(tự sinh từ gallery). Đồng thuận đa số → brand; không khớp → unknown (rác/đối
thủ/ngoài roster — ĐÚNG hành vi mong muốn).

    python inventory/anchor_clusters.py --clusters data/inventory/clusters \
        --jersey data/inventory/jersey --lex data/lexicon.json --min-n 20
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "auto_label"))
from signage_ocr import classify, _reader  # noqa


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", required=True, type=Path)
    ap.add_argument("--jersey", required=True, type=Path)
    ap.add_argument("--lex", required=True)
    ap.add_argument("--min-n", type=int, default=20)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--thr", type=float, default=0.8)
    a = ap.parse_args()

    lex = json.loads(Path(a.lex).read_text(encoding="utf-8"))
    clusters = json.loads((a.clusters / "clusters.json").read_text(encoding="utf-8"))
    meta = {m["name"]: m for m in
            (json.loads(l) for l in (a.jersey / "meta.jsonl").read_text().splitlines())}
    crop_dir = a.jersey / "crops"
    reader = _reader()

    out = []
    for c in clusters:
        if c["n"] < a.min_n:
            continue
        mem = sorted(c["members"], key=lambda n: -max(meta[n]["wh"]))[:a.topk]
        votes, texts = [], []
        for name in mem:
            im = cv2.imread(str(crop_dir / f"{name}.png"), cv2.IMREAD_UNCHANGED)
            if im is None:
                continue
            al = im[:, :, 3:4] / 255.0
            rgb = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
            up = cv2.resize(rgb, None, fx=4, fy=4, interpolation=cv2.INTER_LANCZOS4)
            txt = " ".join(reader.readtext(up, detail=0))
            if not txt.strip():
                continue
            brand, sc = classify(txt, lex, thr=a.thr)
            texts.append(txt)
            if brand != "unknown":
                votes.append(brand)
        n_read = len(texts)
        if votes:
            brand, nb = Counter(votes).most_common(1)[0]
            conf = nb / max(len(mem), 1)
            label = brand if nb >= 3 else f"{brand}?"
        else:
            label, conf = "unknown", 0.0
        out.append({"cid": c["cid"], "n": c["n"], "slot": c["slot"],
                    "u": c["u"], "v": c["v"], "label": label,
                    "votes": dict(Counter(votes)), "n_ocr_read": n_read,
                    "sample_texts": texts[:5], "anchor_conf": round(conf, 2)})
        print(f"C{c['cid']:<4} n={c['n']:<4} {c['slot']:<9} -> {label:<14} "
              f"votes={dict(Counter(votes))} texts={texts[:3]}")

    (a.clusters / "anchors.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ided = [o for o in out if o["label"] not in ("unknown",) and not o["label"].endswith("?")]
    print(f"\n[anchor] {len(out)} cụm xét, {len(ided)} cụm CONFIRMED: "
          f"{[(o['label'], o['slot'], o['n']) for o in ided]}")


if __name__ == "__main__":
    main()
