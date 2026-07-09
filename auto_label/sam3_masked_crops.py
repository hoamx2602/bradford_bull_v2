"""Regenerate SAM3 concept crops dưới dạng RGBA (alpha = mask SAM3).

Vì sao: `sam3_concept_label.py` lưu crop JPG phẳng (nguyên bbox, có nền áo). Khi
recognizer query, template thì đã xoá nền (alpha) còn query thì không → mismatch
tiền xử lý = domain gap (chuyên gia cảnh báo). SAM3 vốn TRẢ mask; file này áp mask
→ lưu RGBA crop (logo + alpha) để recognizer.prep_for_embed xoá nền GIỐNG template.

Giữ nguyên WHERE (imgsz 644 full, conf 0.5) để so A/B chỉ đổi biến masking.

    python auto_label/sam3_masked_crops.py --video data/real/match.mp4 \
        --weights data/sam3/sam3.pt --out data/real/auto_masked \
        --every 25 --conf 0.5 --max-frames 40
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def run(a) -> None:
    from ultralytics.models.sam import SAM3SemanticPredictor
    out = Path(a.out); crop_dir = out / "crops"; crop_dir.mkdir(parents=True, exist_ok=True)
    ov = dict(conf=a.conf, task="segment", mode="predict", model=a.weights,
              save=False, verbose=False, device=a.device, imgsz=a.imgsz)
    P = SAM3SemanticPredictor(overrides=ov)
    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"Khong mo duoc video: {a.video}")
    fi = kept = ncrop = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % a.every != 0:
            fi += 1; continue
        if a.max_frames and kept >= a.max_frames:
            break
        P.set_image(frame)
        r = P(text=["logo"])[0]
        if r.boxes is not None and r.masks is not None:
            masks = r.masks.data.cpu().numpy()  # (N,H,W) float/bool
            for i, b in enumerate(r.boxes):
                if float(b.conf) < a.conf:
                    continue
                x0, y0, x1, y1 = (int(v) for v in b.xyxy[0].tolist())
                x0, y0 = max(0, x0), max(0, y0)
                if x1 <= x0 or y1 <= y0:
                    continue
                rgb = frame[y0:y1, x0:x1]
                m = (masks[i, y0:y1, x0:x1] > 0.5).astype(np.uint8) * 255
                if m.shape[:2] != rgb.shape[:2] or m.max() == 0:
                    continue
                bgra = np.dstack([rgb, m])  # BGR + alpha
                cv2.imwrite(str(crop_dir / f"f{fi:06d}_{i}.png"), bgra)
                ncrop += 1
        kept += 1; fi += 1
    cap.release()
    print(f"[sam3-masked] {kept} frame, {ncrop} RGBA crop -> {crop_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="data/real/match.mp4")
    ap.add_argument("--weights", default="data/sam3/sam3.pt")
    ap.add_argument("--out", default="data/real/auto_masked")
    ap.add_argument("--every", type=int, default=25)
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--max-frames", dest="max_frames", type=int, default=40)
    ap.add_argument("--imgsz", type=int, default=644)
    ap.add_argument("--device", default="cuda")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
