"""Auto-label logo trên video THẬT bằng SAM 3 **concept** (text="logo").

Khác `sam3_exemplar_autolabel.py` (PoC theo exemplar per-brand): file này dùng đúng
API concept của ultralytics — `SAM3SemanticPredictor(text=["logo"])` → tìm MỌI logo
class-agnostic, mask sát viền → OBB. Đây là teacher Tầng 1 cho video thật.

Output:
    out/images/*.jpg            frame
    out/labels/*.txt            OBB class 0 (logo)  — "0 x1 y1 ... x4 y4"
    out/crops/*.jpg             crop logo (cho Tầng 2 recognizer / gallery)
    out/viz/*.jpg               vài frame annotate để kiểm mắt
    out/data.yaml               nc:1 names:{0:logo}

Chạy:
    python auto_label/sam3_concept_label.py --video data/real/match.mp4 \
        --weights data/sam3/sam3.pt --out data/real/auto \
        --every 25 --conf 0.5 --max-frames 40 --device cuda
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from sam3_exemplar_autolabel import mask_to_obb_poly, obb_poly_from_xyxy


def run(a) -> None:
    from ultralytics.models.sam import SAM3SemanticPredictor

    out = Path(a.out)
    img_dir, lbl_dir, crop_dir, viz_dir = (out / "images", out / "labels",
                                           out / "crops", out / "viz")
    for d in (img_dir, lbl_dir, crop_dir, viz_dir):
        d.mkdir(parents=True, exist_ok=True)

    ov = dict(conf=a.conf, task="segment", mode="predict", model=a.weights,
              save=False, verbose=False, device=a.device)
    P = SAM3SemanticPredictor(overrides=ov)

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {a.video}")

    fi = kept = nbox = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % a.every != 0:
            fi += 1; continue
        if a.max_frames and kept >= a.max_frames:
            break

        P.set_image(frame)
        r = P(text=[a.text])[0]
        H, W = frame.shape[:2]
        masks = r.masks.xy if getattr(r, "masks", None) is not None else None
        lines = []
        if r.boxes is not None:
            for i, b in enumerate(r.boxes):
                c = float(b.conf)
                if c < a.conf:
                    continue
                xyxy = b.xyxy[0].tolist()
                poly = (mask_to_obb_poly(masks[i])
                        if (masks is not None and i < len(masks)) else None)
                if poly is None:
                    poly = obb_poly_from_xyxy(xyxy)
                coords = " ".join(f"{x / W:.6f} {y / H:.6f}" for x, y in poly)
                lines.append(f"0 {coords}")
                x0, y0, x1, y1 = (int(v) for v in xyxy)
                crop = frame[max(y0, 0):y1, max(x0, 0):x1]
                if crop.size:
                    cv2.imwrite(str(crop_dir / f"f{fi:06d}_{i}.jpg"), crop)
        stem = f"frame_{fi:06d}"
        cv2.imwrite(str(img_dir / f"{stem}.jpg"), frame)
        (lbl_dir / f"{stem}.txt").write_text("\n".join(lines))
        if kept < a.viz:
            r.save(str(viz_dir / f"{stem}.jpg"))
        nbox += len(lines); kept += 1; fi += 1
    cap.release()

    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images\nval: images\nnc: 1\nnames:\n  0: logo\n")
    print(f"[sam3-concept] {kept} frame gán nhãn, {nbox} logo box, "
          f"{len(list(crop_dir.glob('*.jpg')))} crop → {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="SAM 3 concept auto-label (text=logo)")
    ap.add_argument("--video", required=True)
    ap.add_argument("--weights", default="data/sam3/sam3.pt")
    ap.add_argument("--out", default="data/real/auto")
    ap.add_argument("--text", default="logo")
    ap.add_argument("--every", type=int, default=25)
    ap.add_argument("--conf", type=float, default=0.5)
    ap.add_argument("--max-frames", dest="max_frames", type=int, default=0,
                    help="giới hạn số frame gán nhãn (0 = hết video)")
    ap.add_argument("--viz", type=int, default=4, help="số frame lưu ảnh annotate")
    ap.add_argument("--device", default="cuda")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
