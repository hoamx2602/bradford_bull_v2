"""Stage 1a — Thí nghiệm chẩn đoán scale: OWL-ViT2 trên TORSO CROP thay vì full frame.

Giả thuyết H1 (master plan docs/11): FN 30-60px chủ yếu do scale mismatch —
logo chỉ phủ 3-4 ViT patch ở full frame. Crop person box rồi đưa vào OWL-ViT2
(processor tự pad-resize lên 960 → upscale hiệu dụng 2-5×) sẽ kéo recall lên.

Gate: recall jersey-GT 0.495 → ≥0.70 ⇒ H1 đúng, đầu tư torso-crop cho Stage 1b.

Tối ưu quan trọng: query embeddings KHÔNG phụ thuộc frame → precompute 1 lần
cho mọi crop (khác owlv2_autolabel.py: re-encode query mỗi frame).

Chạy:
  conda run -n bradford_bulls python auto_label/stage1a_torso_owlv2.py \
      --frames data/real/auto/images --gold data/real/auto/labels \
      --logos "Sponsor Logo" --persons data/stage0/person_boxes.json \
      --out data/stage1a
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from owlv2_autolabel import (            # noqa: E402
    DEVICE, IMG_EXT, get_model, load_logo_queries,
    _encode_frame, _nms_per_brand, _global_nms,
)
from stage0_error_analysis import load_gt, center_in_any, iou  # noqa: E402

THRESHOLDS = [0.05, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30]
RAW_THR = 0.05                 # ghi label ở thr thấp nhất, sweep offline
MIN_PERSON_W = 40              # px — person nhỏ hơn thì logo không đọc được
CROP_MARGIN = 0.05             # nới crop 5% (logo sát mép person box)
# Size filter TRÊN CROP (nới hơn full-frame vì logo chiếm tỷ lệ lớn trong torso)
MAX_FRAC_W, MAX_FRAC_H, MIN_FRAC_W = 0.90, 0.90, 0.02
SIZE_BINS = [(0, 30, "tiny <30px"), (30, 60, "small 30-60px"),
             (60, 120, "medium 60-120px"), (120, 1e9, "large >120px")]


# --------------------------------------------------------------------------- #
# Query embedding cache (điểm khác biệt then chốt so với owlv2_autolabel)
# --------------------------------------------------------------------------- #

_DTYPE = torch.float16   # fp16: tránh OOM softmax eager 1.6GB trên WSL2, nhanh 2×


def _get_model_half():
    proc, model = get_model()
    if next(model.parameters()).dtype != _DTYPE:
        model.half()
    return proc, model


def precompute_query_embeds(logo_queries) -> list[tuple[str, "torch.Tensor"]]:
    """Encode mỗi logo query 1 lần duy nhất → list (brand, query_embeds)."""
    proc, model = _get_model_half()
    out = []
    t0 = time.time()
    for brand, imgs in logo_queries.items():
        for img in imgs:
            qpv = proc(query_images=img, return_tensors="pt")["query_pixel_values"].to(DEVICE, _DTYPE)
            with torch.no_grad():
                qfmap, _ = model.image_embedder(pixel_values=qpv)
                bs, ph, pw, hd = qfmap.shape
                qfeats = qfmap.reshape(bs, ph * pw, hd)
                qembeds, _, _ = model.embed_image_query(qfeats, qfmap)
            out.append((brand, qembeds))
    print(f"[query-cache] {len(out)} query embeds trong {time.time()-t0:.1f}s")
    return out


def detect_in_crop(crop: Image.Image, query_cache) -> list[dict]:
    """Chạy mọi query (đã cache embeds) trên 1 torso crop. Trả dets tọa độ crop."""
    proc, model = _get_model_half()
    W, H = crop.size
    target_sizes = torch.tensor([[H, W]], dtype=torch.int32)
    pv = proc(images=crop, return_tensors="pt")["pixel_values"].to(DEVICE, _DTYPE)
    with torch.no_grad():
        feature_map, image_feats = _encode_frame(pv)

    all_dets = []
    for brand, qembeds in query_cache:
        with torch.no_grad():
            pred_logits, class_embeds = model.class_predictor(
                image_feats=image_feats, query_embeds=qembeds)
            target_pred_boxes = model.box_predictor(image_feats, feature_map)
        from transformers.models.owlv2.modeling_owlv2 import (
            Owlv2ImageGuidedObjectDetectionOutput)
        outputs = Owlv2ImageGuidedObjectDetectionOutput(
            image_embeds=feature_map, query_image_embeds=None,
            target_pred_boxes=target_pred_boxes, query_pred_boxes=None,
            logits=pred_logits, class_embeds=class_embeds,
            text_model_output=None, vision_model_output=None)
        results = proc.post_process_image_guided_detection(
            outputs=outputs, threshold=RAW_THR, nms_threshold=0.5,
            target_sizes=target_sizes)[0]
        for box, score in zip(results["boxes"], results["scores"]):
            x1, y1, x2, y2 = [float(v) for v in box.tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            bw, bh = (x2-x1)/W, (y2-y1)/H
            if bw > MAX_FRAC_W or bh > MAX_FRAC_H or bw < MIN_FRAC_W:
                continue
            all_dets.append({"bbox_xyxy": [x1, y1, x2, y2],
                             "score": float(score), "brand": brand})
    after = _nms_per_brand(all_dets, iou_threshold=0.40)
    return _global_nms(after, iou_threshold=0.40)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames",  required=True, type=Path)
    ap.add_argument("--gold",    required=True, type=Path)
    ap.add_argument("--logos",   required=True, type=Path)
    ap.add_argument("--persons", required=True, type=Path)
    ap.add_argument("--out",     required=True, type=Path)
    a = ap.parse_args()
    (a.out / "labels").mkdir(parents=True, exist_ok=True)

    persons = json.loads(a.persons.read_text())
    frames = sorted(p for p in a.frames.iterdir() if p.suffix.lower() in IMG_EXT)
    logo_queries = load_logo_queries(a.logos)
    query_cache = precompute_query_embeds(logo_queries)

    n_crops_total = 0
    all_frame_dets: dict[str, list[dict]] = {}

    for i, fp in enumerate(frames):
        t0 = time.time()
        frame = Image.open(fp).convert("RGB")
        W, H = frame.size
        frame_dets: list[dict] = []
        pboxes = [b for b in persons.get(fp.stem, [])
                  if (b[2]-b[0]) >= MIN_PERSON_W]
        for pb in pboxes:
            mw, mh = (pb[2]-pb[0]) * CROP_MARGIN, (pb[3]-pb[1]) * CROP_MARGIN
            cx0, cy0 = max(0, pb[0]-mw), max(0, pb[1]-mh)
            cx1, cy1 = min(W, pb[2]+mw), min(H, pb[3]+mh)
            crop = frame.crop((cx0, cy0, cx1, cy1))
            for d in detect_in_crop(crop, query_cache):
                x1, y1, x2, y2 = d["bbox_xyxy"]
                frame_dets.append({
                    "bbox_xyxy": [x1+cx0, y1+cy0, x2+cx0, y2+cy0],
                    "score": d["score"], "brand": d["brand"]})
            n_crops_total += 1
        # dedupe vùng person box chồng nhau
        frame_dets = _global_nms(frame_dets, iou_threshold=0.40)
        all_frame_dets[fp.stem] = frame_dets
        # ghi label YOLO+conf (frame coords) để tái sử dụng
        lines = []
        for d in frame_dets:
            x1, y1, x2, y2 = d["bbox_xyxy"]
            lines.append(f"0 {(x1+x2)/2/W:.6f} {(y1+y2)/2/H:.6f} "
                         f"{(x2-x1)/W:.6f} {(y2-y1)/H:.6f} {d['score']:.4f}")
        (a.out / "labels" / f"{fp.stem}.txt").write_text("\n".join(lines))
        print(f"[{i+1}/{len(frames)}] {fp.stem}: {len(pboxes)} crop, "
              f"{len(frame_dets)} det, {time.time()-t0:.1f}s")

    # ── Eval: recall class-agnostic trên jersey GT (GT trong person box) ────
    import cv2
    report = {"n_crops": n_crops_total, "sweep": []}
    print(f"\n{'thr':>5} {'R_jersey':>9} {'prop/person':>12} {'#det':>7}"
          f"   (recall trên GT trong person box, IoU≥0.5)")
    for thr in THRESHOLDS:
        n_gt = n_matched = n_det = 0
        bin_tot: dict = defaultdict(int); bin_hit: dict = defaultdict(int)
        for fp in frames:
            img = cv2.imread(str(fp)); H, W = img.shape[:2]
            pb = persons.get(fp.stem, [])
            gts = [g for g in load_gt(a.gold / f"{fp.stem}.txt", W, H)
                   if center_in_any(g, pb)]
            dets = [d["bbox_xyxy"] for d in all_frame_dets[fp.stem]
                    if d["score"] >= thr]
            n_det += len(dets); n_gt += len(gts)
            for g in gts:
                hit = any(iou(d, g) >= 0.5 for d in dets)
                longest = max(g[2]-g[0], g[3]-g[1])
                for lo, hi, name in SIZE_BINS:
                    if lo <= longest < hi:
                        bin_tot[name] += 1
                        if hit:
                            bin_hit[name] += 1
                        break
                if hit:
                    n_matched += 1
        rec = n_matched / max(n_gt, 1)
        ppp = n_det / max(n_crops_total, 1)
        print(f"{thr:>5} {rec:>9.3f} {ppp:>12.1f} {n_det:>7}")
        report["sweep"].append({
            "thr": thr, "recall_jersey": rec, "props_per_person": ppp,
            "n_det": n_det, "n_gt": n_gt,
            "recall_by_bin": {n: bin_hit[n]/max(bin_tot[n], 1) for n in bin_tot}})

    # bin breakdown ở thr thấp nhất
    b0 = report["sweep"][0]
    print(f"\nRecall theo size bin @ thr={THRESHOLDS[0]} "
          f"(so với miss-rate Stage 0):")
    for lo, hi, name in SIZE_BINS:
        if name in b0["recall_by_bin"]:
            print(f"  {name:<18} R={b0['recall_by_bin'][name]:.3f}")

    (a.out / "stage1a_report.json").write_text(json.dumps(report, indent=2))
    print(f"\n[json] {a.out / 'stage1a_report.json'}")


if __name__ == "__main__":
    main()
