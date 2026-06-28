"""End-to-end glue: video → exposure metrics (chạy trọn 2 tầng + aggregation).

    video.mp4
      │  sample mỗi N frame
      ▼  Tầng 1: YOLOv11-OBB localizer  → vùng logo (OBB) + conf
      │     mỗi detection: crop + mask (từ OBB) ; area_pct ; clarity (Laplacian)
      ▼  Tầng 2: recognizer (DINO embed ⊕ color ⊕ OCR) → brand + score
      │     score < τ → "unknown" (mặc định bỏ, không tính exposure)
      ▼  dets.jsonl  → aggregate.py  → result.json (exposure/visibility/EMV)

Đây là lệnh chạy 1 phát cho 1 video. Cần: weights localizer (Phase 1) + Template DB
(Phase 2). Không có gold thì vẫn ra result.json; có gold thì tự chấm bằng eval_exposure.

Chạy:
    python auto_label/run_pipeline.py --video V.mp4 \
        --weights runs/obb/train/weights/best.pt --db data/templates.npz \
        --out-dir data/run1 --every 10 --device cuda \
        --mask --w-color 0.3 --tau 0.55 [--gold gold.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

import aggregate
import recognizer as R


def poly_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2.0)


def clarity_score(crop_rgb: np.ndarray, scale: float = 150.0) -> float:
    """Image-clarity ∈ (0,1) từ Laplacian variance (sắc→1, mờ→0)."""
    if crop_rgb.size == 0:
        return 0.0
    g = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    v = cv2.Laplacian(g, cv2.CV_64F).var()
    return float(v / (v + scale))


def detections_from_result(res):
    """Ultralytics result → list (poly_px (4,2), conf). OBB ưu tiên, else HBB."""
    out = []
    obb = getattr(res, "obb", None)
    if obb is not None and getattr(obb, "xyxyxyxy", None) is not None and len(obb):
        polys = obb.xyxyxyxy.cpu().numpy()
        confs = obb.conf.cpu().numpy()
        for p, c in zip(polys, confs):
            out.append((p.astype(np.float32), float(c)))
        return out
    boxes = getattr(res, "boxes", None)
    if boxes is not None and len(boxes):
        xyxy = boxes.xyxy.cpu().numpy(); confs = boxes.conf.cpu().numpy()
        for (x0, y0, x1, y1), c in zip(xyxy, confs):
            out.append((np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32),
                        float(c)))
    return out


def crop_and_mask(frame_rgb, poly, pad=4):
    """Cắt bbox quanh OBB + mask polygon (nền=0) để recognizer xoá nền."""
    H, W = frame_rgb.shape[:2]
    x0 = max(int(poly[:, 0].min()) - pad, 0); x1 = min(int(poly[:, 0].max()) + pad, W)
    y0 = max(int(poly[:, 1].min()) - pad, 0); y1 = min(int(poly[:, 1].max()) + pad, H)
    if x1 <= x0 or y1 <= y0:
        return None, None
    crop = frame_rgb[y0:y1, x0:x1]
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.fillPoly(m, [(poly - [x0, y0]).astype(np.int32)], 1)
    return crop, m


def run(a) -> None:
    from ultralytics import YOLO

    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    yolo = YOLO(a.weights)
    db = R.TemplateDB.load(Path(a.db))
    emb = R.Embedder(db.model_id or a.model, device=a.device)
    tr = R.TextReader(a.text_backend)

    cap = cv2.VideoCapture(a.video)
    if not cap.isOpened():
        raise SystemExit(f"Không mở được video: {a.video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    sample_fps = fps / a.every

    dets: list[dict] = []
    fi = n_loc = n_known = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if fi % a.every != 0:
            fi += 1; continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        H, W = rgb.shape[:2]; frame_area = float(H * W)
        res = yolo.predict(frame, imgsz=a.imgsz, conf=a.loc_conf,
                          device=a.device, verbose=False)[0]
        cand = detections_from_result(res)
        n_loc += len(cand)

        # chuẩn bị crop để recognizer (batch theo frame)
        metas, crops, colors, texts = [], [], [], []
        for poly, conf in cand:
            crop, mask = crop_and_mask(rgb, poly)
            if crop is None:
                continue
            prepped = R.prep_for_embed(crop, mask) if a.mask else crop
            metas.append((poly, conf, crop, mask))
            crops.append(prepped)
            colors.append(R.hue_hist(crop, mask))
            texts.append(tr.read(prepped))
        if crops:
            qv = emb.embed(crops)
            preds = db.query_batch(qv, np.array(colors, np.float32), texts,
                                   w_color=a.w_color, w_text=a.w_text,
                                   score_mode=a.score)
            for (poly, conf, crop, _), (brand, score) in zip(metas, preds):
                if score < a.tau:
                    brand = "unknown"
                if brand == "unknown" and not a.keep_unknown:
                    continue
                n_known += (brand != "unknown")
                dets.append({
                    "frame": fi, "brand": brand,
                    "conf": round(conf, 4),
                    "area_pct": round(poly_area(poly) / frame_area * 100.0, 4),
                    "clarity": round(clarity_score(crop), 4),
                    "rec_score": round(float(score), 4),
                })
        fi += 1
    cap.release()

    dets_path = out_dir / "dets.jsonl"
    dets_path.write_text("\n".join(json.dumps(d) for d in dets))
    print(f"[pipeline] {fi} frame, sample mỗi {a.every} (≈{sample_fps:.2f} fps); "
          f"{n_loc} localized, {len(dets)} detection ghi ({n_known} known).")
    print(f"  dets → {dets_path}")

    res = aggregate.aggregate(dets, fps, sample_fps, conf_thr=a.loc_conf,
                              bridge=a.bridge, min_seg=a.min_seg,
                              rate_per_sec=a.rate, video=Path(a.video).stem)
    out_json = out_dir / "result.json"
    out_json.write_text(json.dumps(res, indent=2, ensure_ascii=False))
    aggregate.report(res)
    print(f"  result → {out_json}")

    if a.gold:
        import eval_exposure
        ev = eval_exposure.evaluate(res, json.loads(Path(a.gold).read_text()))
        eval_exposure.report(ev)


def main() -> None:
    ap = argparse.ArgumentParser(description="End-to-end: video → exposure")
    ap.add_argument("--video", required=True)
    ap.add_argument("--weights", required=True, help="localizer YOLOv11-OBB best.pt")
    ap.add_argument("--db", required=True, help="Template DB .npz (Phase 2)")
    ap.add_argument("--out-dir", dest="out_dir", default="data/run")
    ap.add_argument("--every", type=int, default=10, help="sample 1 frame / N")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--loc-conf", dest="loc_conf", type=float, default=0.25)
    ap.add_argument("--device", default=None)
    ap.add_argument("--model", default="facebook/dinov2-base")
    # recognizer
    ap.add_argument("--mask", action="store_true", default=True)
    ap.add_argument("--no-mask", dest="mask", action="store_false")
    ap.add_argument("--w-color", dest="w_color", type=float, default=0.0)
    ap.add_argument("--w-text", dest="w_text", type=float, default=0.0)
    ap.add_argument("--text-backend", default="none",
                    choices=["none", "easyocr", "tesseract"])
    ap.add_argument("--score", choices=["cosine", "margin"], default="cosine")
    ap.add_argument("--tau", type=float, default=0.0,
                    help="ngưỡng open-set: score<τ → unknown")
    ap.add_argument("--keep-unknown", dest="keep_unknown", action="store_true",
                    help="ghi cả detection unknown (mặc định bỏ)")
    # aggregate
    ap.add_argument("--bridge", type=float, default=0.8)
    ap.add_argument("--min-seg", dest="min_seg", type=float, default=0.4)
    ap.add_argument("--rate", type=float, default=50.0)
    ap.add_argument("--gold", default=None, help="(tùy chọn) gold.json để tự chấm")
    a = ap.parse_args()
    run(a)


if __name__ == "__main__":
    main()
