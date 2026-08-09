"""Hướng B — sản phẩm: RF-DETR (club có annotation) → bảng SPONSOR-EXPOSURE/trận.

Chạy RF-DETR trên frame video → detection brand (conf-gate cho precision) → tổng hợp:
mỗi sponsor: số frame hiện diện → giây phơi sáng, số detection, conf tb, độ to tb.
Đây là output cuối mà cả pipeline nhắm tới (media-value/exposure).

    python inventory/rfdetr_exposure.py --video data/real/yt/bradford_wakefield26.mp4 \
        --weights training-result/_ema_model_only.pth --every 20 --conf 0.5 \
        --out data/inventory/exposure_report
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

BRAND = ["acs_group", "aon", "atm", "bartercard", "cch", "chadlaw", "ellgren",
         "em_workwear", "fairway", "floor_tonic", "klg", "mcp", "mna_cladding",
         "mna_support_service", "paints_lacquers", "romantica", "top_notch"]


def bname(cid: int) -> str:
    return BRAND[cid - 1] if 1 <= cid <= 17 else f"?{cid}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--weights", default="training-result/_ema_model_only.pth")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--every", type=int, default=20, help="lấy 1 frame mỗi N")
    ap.add_argument("--conf", type=float, default=0.5, help="ngưỡng conf (precision)")
    ap.add_argument("--resolution", type=int, default=704)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    import cv2
    import numpy as np
    from collections import defaultdict
    from rfdetr import RFDETRLarge
    model = RFDETRLarge(pretrain_weights=a.weights, num_classes=18, resolution=a.resolution)

    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    N = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dt = a.every / fps                       # giây/mẫu
    agg = defaultdict(lambda: {"frames": 0, "dets": 0, "sum_conf": 0.0, "sum_area": 0.0})
    n_sampled = 0
    for fr in range(0, N, a.every):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fr)
        ok, frame = cap.read()
        if not ok:
            continue
        n_sampled += 1
        H, W = frame.shape[:2]
        det = model.predict(frame[:, :, ::-1].copy(), threshold=a.conf)
        present = set()
        for xyxy, cid, cf in zip(det.xyxy, det.class_id, det.confidence):
            b = bname(int(cid))
            agg[b]["dets"] += 1
            agg[b]["sum_conf"] += float(cf)
            x0, y0, x1, y1 = (float(v) for v in xyxy)
            agg[b]["sum_area"] += (x1 - x0) * (y1 - y0) / (W * H) * 100
            present.add(b)
        for b in present:
            agg[b]["frames"] += 1
    cap.release()

    rows = []
    for b, s in agg.items():
        rows.append({"brand": b, "seconds": round(s["frames"] * dt, 1),
                     "frames": s["frames"], "dets": s["dets"],
                     "avg_conf": round(s["sum_conf"] / max(s["dets"], 1), 2),
                     "avg_area_pct": round(s["sum_area"] / max(s["dets"], 1), 2)})
    rows.sort(key=lambda r: -r["seconds"])
    total_s = round(n_sampled * dt, 1)
    report = {"video": a.video, "sampled_frames": n_sampled, "match_span_s": total_s,
              "conf_thr": a.conf, "sponsors": rows}
    (a.out / "exposure.json").write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                         encoding="utf-8")

    # bar chart giây phơi sáng
    _bar_chart(rows, total_s, a.out / "exposure.png")
    print(f"[exposure] {n_sampled} frame @conf{a.conf}, span {total_s}s")
    print(f"{'sponsor':22} {'giây':>7} {'dets':>6} {'conf':>5} {'area%':>6}")
    for r in rows:
        print(f"{r['brand']:22} {r['seconds']:>7} {r['dets']:>6} {r['avg_conf']:>5} {r['avg_area_pct']:>6}")
    print(f"-> {a.out}")


def _bar_chart(rows, total_s, path):
    import numpy as np
    import cv2
    rows = [r for r in rows if r["seconds"] > 0][:16]
    if not rows:
        return
    W, rowh, top, left = 1000, 34, 60, 220
    H = top + rowh * len(rows) + 30
    img = np.full((H, W, 3), 250, np.uint8)
    cv2.putText(img, "Sponsor exposure (giay hien dien) — RF-DETR", (20, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 40, 40), 2)
    mx = max(r["seconds"] for r in rows)
    barw = W - left - 90
    for i, r in enumerate(rows):
        y = top + i * rowh
        cv2.putText(img, r["brand"], (14, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 60), 1)
        w = int(barw * r["seconds"] / mx)
        cv2.rectangle(img, (left, y + 6), (left + w, y + rowh - 8), (150, 110, 20), -1)
        cv2.putText(img, f"{r['seconds']}s", (left + w + 8, y + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)
    cv2.imwrite(str(path), img)


if __name__ == "__main__":
    main()
