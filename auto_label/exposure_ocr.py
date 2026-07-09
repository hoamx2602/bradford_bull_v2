"""Sponsor-exposure GENERIC từ video: OCR full-frame → lexicon-match → temporal.

Cho signage: OCR đọc chữ toàn frame (biển to, rõ ở 1080p), match token vào lexicon
tự-sinh (signage_ocr.build-lex). Nhiễu (tên cầu thủ/scoreboard) không khớp token đội
→ bỏ. Gộp qua nhiều frame → mỗi brand: số frame xuất hiện → giây phơi sáng.

Generic: đổi đội = đổi lexicon (từ gallery đội đó), KHÔNG sửa code.

    python auto_label/exposure_ocr.py --video data/real/yt/bradford_home.mp4 \
        --lex data/lexicon.json --every 50 --out data/exposure
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from collections import defaultdict
import cv2

sys.path.insert(0, str(Path(__file__).parent))
from signage_ocr import classify, _reader  # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--lex", required=True)
    ap.add_argument("--every", type=int, default=50)
    ap.add_argument("--thr", type=float, default=0.82)
    ap.add_argument("--min-conf", type=float, default=0.30, help="ngưỡng conf OCR")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    lex = json.loads(Path(a.lex).read_text(encoding="utf-8"))
    reader = _reader()
    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    dets = []            # mỗi text box khớp roster
    frame_brands = defaultdict(set)   # frame_idx -> {brands} (đếm frame, không double)
    fi = kept = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if fi % a.every == 0:
            for box, text, conf in reader.readtext(fr):
                if conf < a.min_conf:
                    continue
                brand, sc = classify(text, lex, thr=a.thr)
                if brand == "unknown":
                    continue
                xs = [p[0] for p in box]; ys = [p[1] for p in box]
                dets.append({"frame": fi, "t": round(fi / fps, 1), "brand": brand,
                             "text": text, "ocr_conf": round(float(conf), 2),
                             "match": sc, "box": [int(min(xs)), int(min(ys)),
                                                  int(max(xs)), int(max(ys))]})
                frame_brands[fi].add(brand)
            kept += 1
        fi += 1
    cap.release()

    (out / "detections.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in dets), encoding="utf-8")

    # temporal aggregate → exposure
    per = defaultdict(lambda: {"frames": 0, "dets": 0, "texts": defaultdict(int)})
    for fidx, bs in frame_brands.items():
        for b in bs:
            per[b]["frames"] += 1
    for d in dets:
        per[d["brand"]]["dets"] += 1
        per[d["brand"]]["texts"][d["text"].lower()] += 1
    sec_per_sample = a.every / fps
    expo = {}
    for b, v in per.items():
        expo[b] = {"frames_present": v["frames"],
                   "exposure_sec": round(v["frames"] * sec_per_sample, 1),
                   "total_dets": v["dets"],
                   "top_texts": sorted(v["texts"].items(), key=lambda x: -x[1])[:4]}
    expo = dict(sorted(expo.items(), key=lambda x: -x[1]["exposure_sec"]))
    (out / "exposure.json").write_text(json.dumps(expo, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[exposure] {kept} frames sampled (every {a.every}, ~{sec_per_sample:.1f}s), "
          f"{len(dets)} roster text-dets → {out}")
    print(f"\n{'brand':18s}{'frames':>7}{'exposure_s':>12}{'dets':>6}   top_text")
    for b, v in expo.items():
        tt = v["top_texts"][0][0][:20] if v["top_texts"] else ""
        print(f"{b:18s}{v['frames_present']:>7}{v['exposure_sec']:>12}{v['total_dets']:>6}   {tt}")


if __name__ == "__main__":
    main()
