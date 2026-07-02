"""owlv2_autolabel.py — Zero-shot logo detection bằng OWL-ViT2 image-guided detection.

Không cần training. Chỉ cần logo PNG → detect instances trong broadcast frames.
Xuất YOLO-format labels + JSON report để đo mAP qua eval_map.py.

Cách dùng:
  # Detect Bradford Bulls logos trên real frames
  conda run -n bradford_bulls python auto_label/owlv2_autolabel.py detect \\
      --frames data/real/auto/images \\
      --logos "Sponsor Logo" \\
      --out data/owlv2_run1 \\
      --threshold 0.10

  # Sweep threshold để tìm optimal
  conda run -n bradford_bulls python auto_label/owlv2_autolabel.py sweep \\
      --frames data/real/auto/images \\
      --logos "Sponsor Logo" \\
      --gold data/real/auto/labels \\
      --out data/owlv2_sweep

  # Evaluate predictions vs gold set
  conda run -n bradford_bulls python auto_label/owlv2_autolabel.py eval \\
      --pred data/owlv2_run1/labels \\
      --gold data/real/auto/labels \\
      --images data/real/auto/images

  # Visualize side-by-side (GT vs predictions)
  conda run -n bradford_bulls python auto_label/owlv2_autolabel.py viz \\
      --frames data/real/auto/images \\
      --pred data/owlv2_run1/labels \\
      --gold data/real/auto/labels \\
      --out data/owlv2_run1/viz
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import Owlv2ForObjectDetection, Owlv2Processor

# ── Constants ────────────────────────────────────────────────────────────────
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}
DEVICE  = "cuda" if torch.cuda.is_available() else "cpu"

# Logo file stem → brand name.  Verified against KIT/Home Kit.jpg + KIT/Away Kit.jpg (2025/26).
#
# Jersey FRONT body:   topnotch (home) / floor_tonic (away), romantica, mna_cladding, mna_support
# Jersey SLEEVES:      chadwick_lawrence (L), atm_hospitality + bartercard (R)
# Jersey BACK:         fairway, mcp, acs_group
# SHORTS:              cedar_court (front), klg + aon + paints_laquers (back)
# SOCKS:               em_workwear
#
# Romantica variant logic:
#   romantica_home.jpg             → HOME kit (black text on light bg — generated from FINAL WHITE)
#   Romantica Beds - Logo FINAL WHITE → AWAY kit (white text on black bg — matches black jersey)
LOGO_BRAND_MAP = {
    # ── Jersey front (main visible in broadcast) ──────────────────────────────
    "13 - Top Notch Logo":              "topnotch",        # HOME main chest sponsor
    "Floor tonic Logo":                 "floor_tonic",     # AWAY main chest sponsor
    "romantica_home":                   "romantica",       # HOME mid-left chest (light bg)
    "Romantica Beds - Logo FINAL WHITE":"romantica",       # AWAY mid-left chest (dark bg)
    "10 - MNA Cladding":               "mna_cladding",    # top-left collar (both kits)
    "11 - MNA Support Services":       "mna_support",     # top-right collar (both kits)
    # ── Sleeves ───────────────────────────────────────────────────────────────
    "4 - ChadLaw1":                    "chadwick_lawrence",# left sleeve
    "2 - ATM-Hospitality-Logo-New-Font":"atm_hospitality", # right sleeve
    "Bartercard":                      "bartercard",       # right sleeve
    # ── Jersey back ───────────────────────────────────────────────────────────
    "6 - Fairway Flooring Ltd Logo nO NUMBER": "fairway", # back top-right
    "9 - MCP":                         "mcp",              # back top-center (home)
    "8 - MCP Away":                    "mcp",              # back top-center (away)
    "acs_group":                       "acs_group",        # back center
    # ── Shorts ────────────────────────────────────────────────────────────────
    "3 - CCH - Master Logo Black [A3 Digital]": "cedar_court",  # shorts front (home)
    "3 - CCH - Master Logo White [A3 Digital]": "cedar_court",  # shorts front (away)
    "7 - KLG Transparent Final":       "klg",              # shorts back center
    "1 - aon_logo_signature_red_rgb (2)": "aon",           # shorts back right (home)
    "1 - aon_logo_white_rgb (3)":      "aon",              # shorts back right (away)
    "Paints & Laquers Logo FINAL":     "paints_laquers",   # shorts back left
    "12 - yellow":                     "paints_laquers",   # same brand, yellow variant
    # ── Socks ─────────────────────────────────────────────────────────────────
    "5 - EM workwear logo":            "em_workwear",      # socks
}

# ── Model loading (singleton) ────────────────────────────────────────────────
_processor: Owlv2Processor | None = None
_model: Owlv2ForObjectDetection | None = None


def get_model() -> tuple[Owlv2Processor, Owlv2ForObjectDetection]:
    global _processor, _model
    if _model is None:
        print("[owlv2] Loading google/owlv2-large-patch14-ensemble …")
        t0 = time.time()
        _processor = Owlv2Processor.from_pretrained("google/owlv2-large-patch14-ensemble")
        _model = (
            Owlv2ForObjectDetection
            .from_pretrained("google/owlv2-large-patch14-ensemble")
            .to(DEVICE)
            .eval()
        )
        print(f"[owlv2] Loaded in {time.time()-t0:.1f}s on {DEVICE}")
    return _processor, _model


# ── Logo loading + augmentation ──────────────────────────────────────────────


# OWL-ViT2 query images should approximate the scale of logos in broadcast frames.
# GT logos are ~60×47px in 1280×720 frames. Rescaling queries to this range
# tells the model what size to look for, avoiding full-frame false positives.
_QUERY_MAX_PX = 300   # max side length of logo query image

def load_logo_queries(logo_dir: Path, skip_corrupt: bool = True) -> dict[str, list[Image.Image]]:
    """
    Load mỗi logo PNG/JPG → list[PIL.Image] (queries augmented).
    Trả về dict: brand_name → [query_img1, query_img2, ...]

    Scale logos down to _QUERY_MAX_PX so OWL-ViT2 searches at the right scale.
    Add tight-crop variant to improve recall.
    """
    queries: dict[str, list[Image.Image]] = defaultdict(list)

    for p in sorted(logo_dir.iterdir()):
        if p.suffix.lower() not in IMG_EXT:
            continue
        brand = LOGO_BRAND_MAP.get(p.stem, p.stem.lower().replace(" ", "_"))

        try:
            img = Image.open(p).convert("RGBA")
            img.verify()
            img = Image.open(p).convert("RGBA")
        except Exception as e:
            if skip_corrupt:
                print(f"  [warn] skip corrupt: {p.name}: {e}")
                continue
            raise

        # Composite alpha onto white background (OWL-ViT2 requires RGB)
        rgb = _composite_white(img)

        # Tight center crop (remove whitespace padding around logo)
        cropped = _tight_crop(rgb)
        base = cropped if cropped is not None else rgb

        # Resize to scale-appropriate size
        scaled = _resize_for_query(base)
        queries[brand].append(scaled)

        # Second variant: keep original aspect ratio without tight crop
        # Useful when crop removes important context
        if cropped is not None:
            scaled_full = _resize_for_query(rgb)
            if scaled_full.size != scaled.size:
                queries[brand].append(scaled_full)

    print(f"[owlv2] {len(queries)} brands, "
          f"{sum(len(v) for v in queries.values())} total query images")
    return dict(queries)


def _resize_for_query(img: Image.Image, max_px: int = _QUERY_MAX_PX) -> Image.Image:
    """Downscale to max_px on longest side; upscale tiny logos to at least 64px."""
    W, H = img.size
    longest = max(W, H)
    if longest == 0:
        return img
    # Downscale if too large
    if longest > max_px:
        scale = max_px / longest
        new_w, new_h = max(1, int(W * scale)), max(1, int(H * scale))
        return img.resize((new_w, new_h), Image.LANCZOS)
    # Upscale if too small
    if longest < 64:
        scale = 64 / longest
        new_w, new_h = max(1, int(W * scale)), max(1, int(H * scale))
        return img.resize((new_w, new_h), Image.LANCZOS)
    return img


def _composite_white(img: Image.Image) -> Image.Image:
    """RGBA → RGB trên nền trắng."""
    bg = Image.new("RGB", img.size, (255, 255, 255))
    if img.mode == "RGBA":
        bg.paste(img, mask=img.split()[3])
    else:
        bg.paste(img.convert("RGB"))
    return bg


def _tight_crop(img: Image.Image, margin: float = 0.05) -> Image.Image | None:
    """Crop bỏ border trắng/transparent xung quanh logo."""
    arr = np.array(img.convert("L"))
    mask = arr < 240  # non-white pixels
    if not mask.any():
        return None
    rows, cols = np.where(mask)
    r0, r1 = rows.min(), rows.max()
    c0, c1 = cols.min(), cols.max()
    H, W = arr.shape
    pad_r = int((r1 - r0) * margin)
    pad_c = int((c1 - c0) * margin)
    r0 = max(0, r0 - pad_r); r1 = min(H, r1 + pad_r)
    c0 = max(0, c0 - pad_c); c1 = min(W, c1 + pad_c)
    return img.crop((c0, r0, c1, r1)) if (r1 - r0) > 4 and (c1 - c0) > 4 else None


# ── Core detection ────────────────────────────────────────────────────────────

def _encode_frame(pv: "torch.Tensor") -> "tuple[torch.Tensor, torch.Tensor]":
    """
    Encode frame thành (feature_map, image_feats) một lần duy nhất cho mọi logo queries.
    Tránh re-encoding frame N lần (N = số logo brands × queries).
    """
    _, model = get_model()
    feature_map, _ = model.image_embedder(pixel_values=pv)
    bs, ph, pw, hd = feature_map.shape
    image_feats = feature_map.reshape(bs, ph * pw, hd)
    return feature_map, image_feats


def _detect_one_query(
    feature_map: "torch.Tensor",
    image_feats: "torch.Tensor",
    qpv: "torch.Tensor",
    proc: "Owlv2Processor",
    model: "Owlv2ForObjectDetection",
    threshold: float,
    target_sizes: "torch.Tensor",
    W: int,
    H: int,
) -> list[dict]:
    """Run detection for a single logo query against pre-encoded frame embeddings."""
    query_fmap, _ = model.image_embedder(pixel_values=qpv)
    bs, ph, pw, hd = query_fmap.shape
    query_feats = query_fmap.reshape(bs, ph * pw, hd)

    query_embeds, _, query_pred_boxes = model.embed_image_query(query_feats, query_fmap)
    pred_logits, class_embeds = model.class_predictor(image_feats=image_feats, query_embeds=query_embeds)
    target_pred_boxes = model.box_predictor(image_feats, feature_map)

    from transformers.models.owlv2.modeling_owlv2 import Owlv2ImageGuidedObjectDetectionOutput
    outputs = Owlv2ImageGuidedObjectDetectionOutput(
        image_embeds=feature_map,
        query_image_embeds=query_fmap,
        target_pred_boxes=target_pred_boxes,
        query_pred_boxes=query_pred_boxes,
        logits=pred_logits,
        class_embeds=class_embeds,
        text_model_output=None,
        vision_model_output=None,
    )
    results = proc.post_process_image_guided_detection(
        outputs=outputs,
        threshold=threshold,
        nms_threshold=0.5,
        target_sizes=target_sizes,
    )[0]

    # GT logos are ~4-12% of frame width. Filter huge boxes (FP due to scale mismatch).
    max_w_frac = 0.40   # max 40% of frame width
    max_h_frac = 0.50   # max 50% of frame height
    min_w_frac = 0.01   # min 1% of frame width (ignore tiny detections)

    dets = []
    for box, score in zip(results["boxes"], results["scores"]):
        x1, y1, x2, y2 = [float(v) for v in box.tolist()]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        bw, bh = (x2 - x1) / W, (y2 - y1) / H
        if bw > max_w_frac or bh > max_h_frac or bw < min_w_frac:
            continue
        dets.append({
            "bbox_xyxy": [x1, y1, x2, y2],
            "bbox_yolo": [
                (x1 + x2) / 2 / W,
                (y1 + y2) / 2 / H,
                bw,
                bh,
            ],
            "score": float(score),
        })
    return dets


def detect_logos_in_frame(
    frame_path: Path,
    logo_queries: dict[str, list[Image.Image]],
    threshold: float = 0.10,
    nms_iou: float = 0.40,
) -> list[dict]:
    """
    Chạy OWL-ViT2 image-guided detection cho mọi logo trong một frame.

    Tối ưu: encode frame một lần duy nhất, reuse cho N logo queries.
    Speedup: ~N× so với naive approach (encode frame mỗi lần).

    Trả về list of dicts:
      {brand, bbox_xyxy, bbox_yolo, score, query_idx}
    """
    proc, model = get_model()
    frame = Image.open(frame_path).convert("RGB")
    W, H = frame.size
    target_sizes = torch.tensor([[H, W]], dtype=torch.int32)

    # Encode frame ONCE
    pv = proc(images=frame, return_tensors="pt")["pixel_values"].to(DEVICE)
    with torch.no_grad():
        feature_map, image_feats = _encode_frame(pv)

    all_dets: list[dict] = []

    # For each logo brand + query variant, only encode the (small) logo
    for brand, query_imgs in logo_queries.items():
        for q_idx, query in enumerate(query_imgs):
            qpv = proc(query_images=query, return_tensors="pt")["query_pixel_values"].to(DEVICE)
            with torch.no_grad():
                dets = _detect_one_query(
                    feature_map, image_feats, qpv, proc, model,
                    threshold, target_sizes, W, H,
                )
            for d in dets:
                d["brand"] = brand
                d["query_idx"] = q_idx
                all_dets.append(d)

    # 1. Per-brand NMS (remove duplicate detections for same logo)
    after_brand_nms = _nms_per_brand(all_dets, iou_threshold=nms_iou)
    # 2. Global NMS (remove cross-brand overlaps — logos don't physically overlap)
    return _global_nms(after_brand_nms, iou_threshold=nms_iou)


def _iou(a: list, b: list) -> float:
    """IoU giữa hai [x1,y1,x2,y2] boxes."""
    ix1 = max(a[0], b[0]); iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]); iy2 = min(a[3], b[3])
    iw  = max(0, ix2 - ix1); ih = max(0, iy2 - iy1)
    inter = iw * ih
    area_a = (a[2]-a[0]) * (a[3]-a[1])
    area_b = (b[2]-b[0]) * (b[3]-b[1])
    return inter / (area_a + area_b - inter + 1e-9)


def _nms_per_brand(dets: list[dict], iou_threshold: float) -> list[dict]:
    """NMS riêng theo brand, sort by score descending."""
    by_brand: dict[str, list] = defaultdict(list)
    for d in dets:
        by_brand[d["brand"]].append(d)

    kept = []
    for brand, group in by_brand.items():
        group = sorted(group, key=lambda x: x["score"], reverse=True)
        accepted: list[dict] = []
        for d in group:
            if all(_iou(d["bbox_xyxy"], a["bbox_xyxy"]) < iou_threshold
                   for a in accepted):
                accepted.append(d)
        kept.extend(accepted)
    return kept


def _global_nms(dets: list[dict], iou_threshold: float = 0.40) -> list[dict]:
    """Global NMS across all brands — removes overlapping FP from different brand queries.

    Logos don't physically overlap, so cross-brand duplicates are FP.
    Keep highest-score detection when two brands detect the same region.
    """
    dets = sorted(dets, key=lambda x: x["score"], reverse=True)
    kept: list[dict] = []
    for d in dets:
        if all(_iou(d["bbox_xyxy"], k["bbox_xyxy"]) < iou_threshold for k in kept):
            kept.append(d)
    return kept


# ── Batch processing ─────────────────────────────────────────────────────────

def run_detect(
    frames_dir:  Path,
    logo_dir:    Path,
    out_dir:     Path,
    threshold:   float = 0.10,
    nms_iou:     float = 0.40,
    max_frames:  int   = 0,
) -> dict:
    """Detect logos trong toàn bộ frame directory. Ghi YOLO labels + report JSON."""
    logo_queries = load_logo_queries(logo_dir)
    frames = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in IMG_EXT)
    if max_frames:
        frames = frames[:max_frames]

    lbl_dir = out_dir / "labels"
    lbl_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)

    report: dict = {
        "threshold": threshold, "nms_iou": nms_iou,
        "n_frames": len(frames), "frames": {}
    }
    total_dets = 0

    for i, fp in enumerate(frames):
        t0 = time.time()
        dets = detect_logos_in_frame(fp, logo_queries, threshold, nms_iou)
        elapsed = time.time() - t0

        # Write YOLO labels  (cls=0 for all — class-agnostic "logo")
        yolo_lines = []
        for d in dets:
            cx, cy, w, h = d["bbox_yolo"]
            yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f} {d['score']:.4f}")
        (lbl_dir / (fp.stem + ".txt")).write_text("\n".join(yolo_lines))

        report["frames"][fp.name] = {
            "n_det": len(dets),
            "time_s": round(elapsed, 2),
            "detections": [{
                "brand": d["brand"],
                "bbox_xyxy": [round(v, 1) for v in d["bbox_xyxy"]],
                "score": round(d["score"], 4),
            } for d in dets],
        }
        total_dets += len(dets)

        brand_counts = defaultdict(int)
        for d in dets:
            brand_counts[d["brand"]] += 1
        bc_str = " ".join(f"{b}={n}" for b, n in sorted(brand_counts.items()))
        print(f"[{i+1:03d}/{len(frames)}] {fp.name}: {len(dets):2d} dets  "
              f"({elapsed:.1f}s)  {bc_str}")

    report["total_detections"] = total_dets
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n[owlv2] Done. {total_dets} total detections across {len(frames)} frames.")
    print(f"[owlv2] Labels → {lbl_dir}")
    print(f"[owlv2] Report → {report_path}")
    return report


# ── Evaluation against gold set ──────────────────────────────────────────────

def _obb_to_aabb(parts: list[str]) -> tuple[float, float, float, float]:
    """OBB 4-corner format → axis-aligned bbox (x1,y1,x2,y2) normalised [0,1]."""
    xs = [float(parts[i]) for i in range(1, 9, 2)]
    ys = [float(parts[i]) for i in range(2, 9, 2)]
    return min(xs), min(ys), max(xs), max(ys)


def _load_gt(label_path: Path, W: int, H: int) -> list[dict]:
    """Load ground truth — supports both OBB (8 coords) and YOLO AABB (4 coords)."""
    gt = []
    if not label_path.exists():
        return gt
    for line in label_path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls = int(float(parts[0]))
        if len(parts) == 9:          # OBB: cls x1 y1 x2 y2 x3 y3 x4 y4
            nx1, ny1, nx2, ny2 = _obb_to_aabb(parts)
            x1, y1, x2, y2 = nx1*W, ny1*H, nx2*W, ny2*H
        else:                         # YOLO AABB: cls cx cy w h
            cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            x1 = (cx - w/2) * W; y1 = (cy - h/2) * H
            x2 = (cx + w/2) * W; y2 = (cy + h/2) * H
        gt.append({"cls": cls, "bbox_xyxy": [x1, y1, x2, y2]})
    return gt


def _load_pred(label_path: Path, W: int, H: int) -> list[dict]:
    """Load predictions in YOLO format (cls cx cy w h [conf])."""
    preds = []
    if not label_path.exists():
        return preds
    for line in label_path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls = int(float(parts[0]))
        cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
        conf = float(parts[5]) if len(parts) >= 6 else 1.0
        x1 = (cx - w/2) * W; y1 = (cy - h/2) * H
        x2 = (cx + w/2) * W; y2 = (cy + h/2) * H
        preds.append({"cls": cls, "bbox_xyxy": [x1, y1, x2, y2], "score": conf})
    return preds


def run_eval(
    pred_dir:   Path,
    gold_dir:   Path,
    images_dir: Path,
    iou_thr:    float = 0.5,
) -> dict:
    """
    Đo Precision / Recall / F1 / mAP@0.5 của OWL-ViT2 predictions vs gold labels.

    Gold labels có thể là OBB (8 coords) hoặc YOLO AABB (4 coords) — tự detect.
    """
    frames = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMG_EXT)

    all_tp = all_fp = all_fn = 0
    per_frame_results = []

    # Collect all (score, tp_flag) for AP calculation
    all_scores: list[float] = []
    all_tp_flags: list[int] = []
    n_gt_total = 0

    for fp in frames:
        img = cv2.imread(str(fp))
        H, W = img.shape[:2]

        gt   = _load_gt(gold_dir / (fp.stem + ".txt"), W, H)
        pred = _load_pred(pred_dir / (fp.stem + ".txt"), W, H)
        pred = sorted(pred, key=lambda x: x["score"], reverse=True)

        n_gt_total += len(gt)
        matched_gt = set()
        tp = fp_count = 0

        for p in pred:
            best_iou, best_j = 0.0, -1
            for j, g in enumerate(gt):
                if j in matched_gt:
                    continue
                iou = _iou(p["bbox_xyxy"], g["bbox_xyxy"])
                if iou > best_iou:
                    best_iou, best_j = iou, j

            if best_iou >= iou_thr and best_j >= 0:
                matched_gt.add(best_j)
                tp += 1
                all_tp_flags.append(1)
            else:
                fp_count += 1
                all_tp_flags.append(0)
            all_scores.append(p["score"])

        fn = len(gt) - tp
        all_tp += tp
        all_fp += fp_count
        all_fn += fn
        per_frame_results.append({
            "frame":    fp.name,
            "n_gt":     len(gt),
            "n_pred":   len(pred),
            "tp": tp, "fp": fp_count, "fn": fn,
        })

    # Global P / R / F1
    precision = all_tp / (all_tp + all_fp + 1e-9)
    recall    = all_tp / (all_tp + all_fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)

    # AP@0.5 (11-point interpolation)
    ap = _compute_ap(all_scores, all_tp_flags, n_gt_total)

    result = {
        "iou_threshold": iou_thr,
        "n_frames": len(frames),
        "n_gt_total": n_gt_total,
        "n_pred_total": all_tp + all_fp,
        "TP": all_tp, "FP": all_fp, "FN": all_fn,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1":        round(f1, 4),
        "AP@0.5":    round(ap, 4),
        "per_frame": per_frame_results,
    }

    print("\n══════════ Evaluation Results ══════════")
    print(f"  IoU threshold : {iou_thr}")
    print(f"  Frames        : {len(frames)}")
    print(f"  GT logos      : {n_gt_total}")
    print(f"  Predictions   : {all_tp + all_fp}")
    print(f"  TP / FP / FN  : {all_tp} / {all_fp} / {all_fn}")
    print(f"  Precision     : {precision:.3f}")
    print(f"  Recall        : {recall:.3f}")
    print(f"  F1            : {f1:.3f}")
    print(f"  AP@0.5        : {ap:.3f}")
    print("════════════════════════════════════════\n")
    return result


def _compute_ap(scores: list[float], tp_flags: list[int], n_gt: int) -> float:
    """Average Precision via 11-point interpolation."""
    if not scores or n_gt == 0:
        return 0.0
    order = np.argsort(scores)[::-1]
    tp_arr = np.array(tp_flags)[order]
    tp_cum = np.cumsum(tp_arr)
    fp_cum = np.cumsum(1 - tp_arr)

    precisions = tp_cum / (tp_cum + fp_cum + 1e-9)
    recalls    = tp_cum / n_gt

    ap = 0.0
    for t in np.linspace(0, 1, 11):
        p = precisions[recalls >= t].max() if (recalls >= t).any() else 0.0
        ap += p / 11
    return float(ap)


# ── Threshold sweep ──────────────────────────────────────────────────────────

def run_sweep(
    frames_dir: Path,
    logo_dir:   Path,
    gold_dir:   Path,
    out_dir:    Path,
    thresholds: list[float] | None = None,
    raw_dir:    Path | None = None,
    gnms:       bool = True,
) -> None:
    """
    Run detection à nhiều threshold → tìm threshold cho F1 tốt nhất.
    Chỉ chạy OWL-ViT2 inference một lần (thr=0.05) rồi filter nhiều lần.

    raw_dir: nếu đã có labels ở thr=0.05 từ lần chạy trước (vd data/owlv2_full/labels),
             truyền vào để skip bước detect lại (tránh GPU OOM khi đang chạy song song).
    gnms: áp dụng global NMS khi filter (default True).
    """
    if thresholds is None:
        thresholds = [0.05, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30]

    if raw_dir is not None and (raw_dir / "labels").is_dir():
        print(f"[sweep] Reusing existing raw labels from {raw_dir}/labels (skip detection)")
        raw_labels_dir = raw_dir / "labels"
    else:
        # Detect một lần với threshold rất thấp, giữ lại tất cả detections + scores
        _raw = out_dir / "_raw"
        print(f"[sweep] Detecting with base threshold=0.05 (will filter later)…")
        run_detect(frames_dir, logo_dir, _raw, threshold=0.05, max_frames=0)
        raw_labels_dir = _raw / "labels"

    frames = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in IMG_EXT)
    sweep_results = []

    for thr in thresholds:
        # Filter raw predictions by threshold + optional global NMS
        thr_dir = out_dir / f"thr_{thr:.2f}" / "labels"
        thr_dir.mkdir(parents=True, exist_ok=True)
        for fp in frames:
            raw_label = raw_labels_dir / (fp.stem + ".txt")
            if not raw_label.exists():
                continue

            # Load all predictions above threshold
            preds = []
            for line in raw_label.read_text().splitlines():
                parts = line.split()
                if len(parts) >= 6 and float(parts[5]) >= thr:
                    preds.append(parts)

            if gnms and preds:
                # Apply global NMS: convert to xyxy, filter, convert back
                img = cv2.imread(str(fp))
                IH, IW = img.shape[:2]
                boxes = []
                for parts in preds:
                    cx, cy, w, h = float(parts[1])*IW, float(parts[2])*IH, float(parts[3])*IW, float(parts[4])*IH
                    sc = float(parts[5])
                    boxes.append([cx-w/2, cy-h/2, cx+w/2, cy+h/2, sc, parts])
                boxes = sorted(boxes, key=lambda x: -x[4])
                kept_parts = []
                accepted = []
                for b in boxes:
                    if all(_iou(b[:4], k[:4]) < 0.40 for k in accepted):
                        accepted.append(b)
                        kept_parts.append(b[5])
                preds = kept_parts

            (thr_dir / (fp.stem + ".txt")).write_text("\n".join(" ".join(p) for p in preds))

        img = cv2.imread(str(frames[0]))
        H, W = img.shape[:2]
        result = run_eval(thr_dir, gold_dir, frames_dir)
        result["threshold"] = thr
        sweep_results.append(result)
        print(f"  thr={thr:.2f}: P={result['precision']:.3f} "
              f"R={result['recall']:.3f} F1={result['f1']:.3f} "
              f"AP={result['AP@0.5']:.3f}")

    # Find best
    best = max(sweep_results, key=lambda x: x["f1"])
    print(f"\n[sweep] Best F1={best['f1']:.3f} at threshold={best['threshold']}")
    (out_dir / "sweep_results.json").write_text(json.dumps(sweep_results, indent=2))

    # Print table
    print("\n─── Threshold Sweep ───────────────────────────────")
    print(f"{'Thr':>6}  {'P':>6}  {'R':>6}  {'F1':>6}  {'AP@0.5':>8}  {'#Pred':>6}")
    print("─" * 55)
    for r in sweep_results:
        marker = " ◄ best F1" if r["threshold"] == best["threshold"] else ""
        print(f"{r['threshold']:>6.2f}  {r['precision']:>6.3f}  {r['recall']:>6.3f}  "
              f"{r['f1']:>6.3f}  {r['AP@0.5']:>8.3f}  "
              f"{r['n_pred_total']:>6}{marker}")
    print("─" * 55)


# ── Visualization ─────────────────────────────────────────────────────────────

def run_viz(
    frames_dir: Path,
    pred_dir:   Path,
    gold_dir:   Path,
    out_dir:    Path,
    max_frames: int = 0,
) -> None:
    """Side-by-side visualization: GT (green) vs Predictions (red/orange)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted(p for p in frames_dir.iterdir() if p.suffix.lower() in IMG_EXT)
    if max_frames:
        frames = frames[:max_frames]

    for fp in frames:
        img = Image.open(fp).convert("RGB")
        W, H = img.size

        # Left panel: GT
        left = img.copy()
        draw = ImageDraw.Draw(left)
        gt = _load_gt(gold_dir / (fp.stem + ".txt"), W, H)
        for g in gt:
            x1, y1, x2, y2 = g["bbox_xyxy"]
            draw.rectangle([x1, y1, x2, y2], outline=(0, 220, 0), width=3)

        # Right panel: Predictions
        right = img.copy()
        draw = ImageDraw.Draw(right)
        pred = _load_pred(pred_dir / (fp.stem + ".txt"), W, H)
        for p in pred:
            x1, y1, x2, y2 = p["bbox_xyxy"]
            color = (255, 60, 60) if p["score"] >= 0.15 else (255, 180, 0)
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            draw.text((x1 + 2, y1 + 2), f"{p['score']:.2f}", fill=color)

        # Combine
        canvas = Image.new("RGB", (W * 2, H), (30, 30, 30))
        canvas.paste(left, (0, 0))
        canvas.paste(right, (W, 0))

        # Labels
        draw_c = ImageDraw.Draw(canvas)
        draw_c.text((8,   8), f"GT: {len(gt)} logos",   fill=(0, 220, 0))
        draw_c.text((W+8, 8), f"Pred: {len(pred)} logos", fill=(255, 60, 60))
        draw_c.text((4, H-18), fp.name, fill=(200, 200, 200))

        out_path = out_dir / fp.name
        canvas.save(str(out_path))

    print(f"[viz] Saved {len(frames)} visualizations → {out_dir}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    # detect
    p_det = sub.add_parser("detect", help="Run OWL-ViT2 detection on frames")
    p_det.add_argument("--frames",    required=True, type=Path)
    p_det.add_argument("--logos",     default="Sponsor Logo", type=Path)
    p_det.add_argument("--out",       required=True, type=Path)
    p_det.add_argument("--threshold", type=float, default=0.10)
    p_det.add_argument("--nms-iou",   type=float, default=0.40)
    p_det.add_argument("--max-frames",type=int,   default=0)

    # sweep
    p_sw = sub.add_parser("sweep", help="Sweep threshold to find best F1")
    p_sw.add_argument("--frames",   required=True, type=Path)
    p_sw.add_argument("--logos",    default="Sponsor Logo", type=Path)
    p_sw.add_argument("--gold",     required=True, type=Path)
    p_sw.add_argument("--out",      required=True, type=Path)
    p_sw.add_argument("--raw-dir",  type=Path, default=None,
                      help="Reuse existing detection labels (skip inference). "
                           "Pass the dir that contains a labels/ subdir at thr=0.05.")

    # eval
    p_ev = sub.add_parser("eval", help="Evaluate predictions vs gold")
    p_ev.add_argument("--pred",    required=True, type=Path)
    p_ev.add_argument("--gold",    required=True, type=Path)
    p_ev.add_argument("--images",  required=True, type=Path)
    p_ev.add_argument("--iou",     type=float, default=0.5)
    p_ev.add_argument("--out",     type=Path)

    # viz
    p_vz = sub.add_parser("viz", help="Visualize GT vs predictions")
    p_vz.add_argument("--frames",     required=True, type=Path)
    p_vz.add_argument("--pred",       required=True, type=Path)
    p_vz.add_argument("--gold",       required=True, type=Path)
    p_vz.add_argument("--out",        required=True, type=Path)
    p_vz.add_argument("--max-frames", type=int, default=0)

    args = ap.parse_args()

    if args.cmd == "detect":
        run_detect(
            frames_dir  = Path(args.frames),
            logo_dir    = Path(args.logos),
            out_dir     = Path(args.out),
            threshold   = args.threshold,
            nms_iou     = args.nms_iou,
            max_frames  = args.max_frames,
        )

    elif args.cmd == "sweep":
        run_sweep(
            frames_dir = Path(args.frames),
            logo_dir   = Path(args.logos),
            gold_dir   = Path(args.gold),
            out_dir    = Path(args.out),
            raw_dir    = Path(args.raw_dir) if args.raw_dir else None,
        )

    elif args.cmd == "eval":
        result = run_eval(
            pred_dir   = Path(args.pred),
            gold_dir   = Path(args.gold),
            images_dir = Path(args.images),
            iou_thr    = args.iou,
        )
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=2))

    elif args.cmd == "viz":
        run_viz(
            frames_dir = Path(args.frames),
            pred_dir   = Path(args.pred),
            gold_dir   = Path(args.gold),
            out_dir    = Path(args.out),
            max_frames = args.max_frames,
        )


if __name__ == "__main__":
    main()
