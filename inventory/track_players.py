"""M1a — Track cầu thủ trên video trận đấu (kiến trúc inventory, docs/12).

YOLO person + ByteTrack (built-in ultralytics). Lưu track làm xương sống cho
slot-clustering: mỗi detection (frame, track_id, bbox) + torso color feature
để phân đội ở bước sau.

    python inventory/track_players.py --video data/real/yt/bradford_home.mp4 \
        --out data/inventory/tracks --stride 2
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

MIN_H = 90          # px — người nhỏ hơn thì bỏ (không đọc được logo, nhiễu màu)
TORSO = (0.20, 0.55, 0.15, 0.85)  # (y0,y1,x0,x1) tỷ lệ trong person bbox → vùng áo


def torso_hsv_feat(frame: np.ndarray, xyxy) -> np.ndarray | None:
    """Histogram HS trên vùng torso — feature phân đội (bất biến sáng hơn RGB)."""
    x0, y0, x1, y1 = (int(v) for v in xyxy)
    h, w = y1 - y0, x1 - x0
    ty0, ty1 = y0 + int(h * TORSO[0]), y0 + int(h * TORSO[1])
    tx0, tx1 = x0 + int(w * TORSO[2]), x0 + int(w * TORSO[3])
    crop = frame[max(0, ty0):ty1, max(0, tx0):tx1]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [12, 4], [0, 180, 0, 256]).flatten()
    n = np.linalg.norm(hist)
    return hist / n if n > 0 else hist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--model", default="yolov8m.pt")
    ap.add_argument("--stride", type=int, default=2, help="vid_stride (2 = 12.5fps)")
    ap.add_argument("--conf", type=float, default=0.35)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO
    model = YOLO(a.model)

    n_det = 0
    feats: dict[int, list[np.ndarray]] = {}
    with (a.out / "tracks.jsonl").open("w", encoding="utf-8") as f:
        results = model.track(source=a.video, stream=True, persist=True,
                              tracker="bytetrack.yaml", classes=[0],
                              conf=a.conf, vid_stride=a.stride, verbose=False)
        for fi, r in enumerate(results):
            if r.boxes is None or r.boxes.id is None:
                continue
            frame = r.orig_img
            for b, tid, cf in zip(r.boxes.xyxy.cpu().numpy(),
                                  r.boxes.id.cpu().numpy().astype(int),
                                  r.boxes.conf.cpu().numpy()):
                if b[3] - b[1] < MIN_H:
                    continue
                f.write(json.dumps({"fi": fi, "tid": int(tid),
                                    "xyxy": [round(float(v), 1) for v in b],
                                    "conf": round(float(cf), 3)}) + "\n")
                n_det += 1
                # feature màu: lấy tối đa 20 mẫu / track, cách nhau
                lst = feats.setdefault(int(tid), [])
                if len(lst) < 20 and fi % 5 == 0:
                    ft = torso_hsv_feat(frame, b)
                    if ft is not None:
                        lst.append(ft)

    med = {tid: np.median(np.stack(v), axis=0).tolist()
           for tid, v in feats.items() if len(v) >= 2}
    (a.out / "track_color_feats.json").write_text(json.dumps(med), encoding="utf-8")
    print(f"[tracks] {n_det} detections, {len(feats)} tracks "
          f"({len(med)} with color feats) -> {a.out}")


if __name__ == "__main__":
    main()
