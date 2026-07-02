"""Stage 0 — Phân rã lỗi + thí nghiệm oracle person-ROI (không cần annotate gì mới).

Trả lời 2 câu hỏi quyết định trước khi xây pipeline mới:
  1. ORACLE: nếu chỉ giữ detection OWL-ViT2 nằm TRONG person box, P/R thay đổi ra sao?
     → đo trần của person-ROI gating với zero code mới.
     H0: ≥70% FP nằm ngoài person box.
  2. DECOMPOSE: FP nằm ở đâu (trong/ngoài người)? FN vì sao (quá nhỏ / ngoài người)?
     → biết headroom của từng stage tiếp theo.

Input:
  --frames  data/real/auto/images     (40 frame gold)
  --gold    data/real/auto/labels     (GT OBB: cls x1 y1 x2 y2 x3 y3 x4 y4)
  --raw     data/owlv2_full/labels    (pred YOLO+conf, threshold 0.05 gốc)
  --out     data/stage0               (report JSON + person boxes + viz)

Chạy:
  conda run -n bradford_bulls python auto_label/stage0_error_analysis.py \
      --frames data/real/auto/images --gold data/real/auto/labels \
      --raw data/owlv2_full/labels --out data/stage0
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png"}
PERSON_PAD = 0.10          # nới person box 10% mỗi chiều (logo sát mép torso)
THRESHOLDS = [0.05, 0.08, 0.10, 0.13, 0.16, 0.20]
IOU_MATCH = 0.5
# FN size bins theo cạnh dài nhất của GT box (px)
SIZE_BINS = [(0, 30, "tiny <30px"), (30, 60, "small 30-60px"),
             (60, 120, "medium 60-120px"), (120, 1e9, "large >120px")]


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #

def load_gt(p: Path, W: int, H: int) -> list[tuple]:
    """GT OBB hoặc AABB → list xyxy pixel."""
    out = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 9:
            xs = [float(parts[i]) * W for i in range(1, 9, 2)]
            ys = [float(parts[i]) * H for i in range(2, 9, 2)]
            out.append((min(xs), min(ys), max(xs), max(ys)))
        elif len(parts) >= 5:
            cx, cy, w, h = (float(v) for v in parts[1:5])
            out.append(((cx - w/2) * W, (cy - h/2) * H,
                        (cx + w/2) * W, (cy + h/2) * H))
    return out


def load_preds(p: Path, W: int, H: int) -> list[tuple]:
    """Pred YOLO+conf → list (xyxy pixel, conf)."""
    out = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cx, cy, w, h = (float(v) for v in parts[1:5])
        conf = float(parts[5]) if len(parts) >= 6 else 1.0
        box = ((cx - w/2) * W, (cy - h/2) * H,
               (cx + w/2) * W, (cy + h/2) * H)
        out.append((box, conf))
    return out


def iou(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(ix1 - ix0, 0), max(iy1 - iy0, 0)
    inter = iw * ih
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def center_in_any(box, person_boxes) -> bool:
    """Tâm của box có nằm trong person box (đã pad) nào không."""
    cx, cy = (box[0]+box[2])/2, (box[1]+box[3])/2
    for pb in person_boxes:
        if pb[0] <= cx <= pb[2] and pb[1] <= cy <= pb[3]:
            return True
    return False


# --------------------------------------------------------------------------- #
# Person detection
# --------------------------------------------------------------------------- #

def detect_persons(frames: list[Path], out_dir: Path) -> dict[str, list]:
    """YOLOv8 person detection. Cache ra JSON — chạy 1 lần."""
    cache = out_dir / "person_boxes.json"
    if cache.exists():
        print(f"[person] dùng cache {cache}")
        return json.loads(cache.read_text())

    from ultralytics import YOLO
    model = YOLO("yolov8m.pt")          # medium đủ cho person 720p
    boxes_by_stem: dict[str, list] = {}
    for fp in frames:
        res = model.predict(str(fp), classes=[0], conf=0.30, verbose=False)[0]
        img = cv2.imread(str(fp)); H, W = img.shape[:2]
        person_boxes = []
        for b in res.boxes.xyxy.cpu().numpy():
            x0, y0, x1, y1 = b[:4]
            pw, ph = (x1-x0)*PERSON_PAD, (y1-y0)*PERSON_PAD
            person_boxes.append([float(max(0, x0-pw)), float(max(0, y0-ph)),
                                 float(min(W, x1+pw)), float(min(H, y1+ph))])
        boxes_by_stem[fp.stem] = person_boxes
        print(f"[person] {fp.stem}: {len(person_boxes)} người")
    cache.write_text(json.dumps(boxes_by_stem))
    return boxes_by_stem


# --------------------------------------------------------------------------- #
# Eval P/R/F1 với matching greedy theo conf
# --------------------------------------------------------------------------- #

def eval_frame(preds, gts) -> tuple[list[bool], set[int]]:
    """preds sort theo conf giảm. Trả (is_tp per pred, matched gt indices)."""
    matched: set[int] = set()
    is_tp = []
    for box, _conf in preds:
        best_iou, best_j = 0.0, -1
        for j, g in enumerate(gts):
            if j in matched:
                continue
            v = iou(box, g)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_iou >= IOU_MATCH:
            is_tp.append(True); matched.add(best_j)
        else:
            is_tp.append(False)
    return is_tp, matched


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    f1 = 2*p*r / max(p + r, 1e-9)
    return p, r, f1


# --------------------------------------------------------------------------- #
# Main analysis
# --------------------------------------------------------------------------- #

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, type=Path)
    ap.add_argument("--gold",   required=True, type=Path)
    ap.add_argument("--raw",    required=True, type=Path)
    ap.add_argument("--out",    required=True, type=Path)
    ap.add_argument("--viz", type=int, default=6,
                    help="số frame xuất ảnh visualize (0=tắt)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    frames = sorted(p for p in a.frames.iterdir() if p.suffix.lower() in IMG_EXT)
    persons = detect_persons(frames, a.out)

    # Load tất cả 1 lần
    data = {}   # stem -> dict(W,H,gts,preds)
    for fp in frames:
        img = cv2.imread(str(fp)); H, W = img.shape[:2]
        data[fp.stem] = {
            "W": W, "H": H, "path": fp,
            "gts": load_gt(a.gold / f"{fp.stem}.txt", W, H),
            "preds": sorted(load_preds(a.raw / f"{fp.stem}.txt", W, H),
                            key=lambda x: -x[1]),
            "persons": persons.get(fp.stem, []),
        }

    n_gt_total = sum(len(d["gts"]) for d in data.values())
    print(f"\n{len(frames)} frames, {n_gt_total} GT boxes\n")

    # ── Sweep: baseline vs oracle person-filter ─────────────────────────────
    results = {"n_frames": len(frames), "n_gt": n_gt_total,
               "person_pad": PERSON_PAD, "sweep": []}
    print(f"{'thr':>5} │ {'── baseline ──':^25} │ {'── person-ROI oracle ──':^25}")
    print(f"{'':>5} │ {'P':>7}{'R':>7}{'F1':>7} {'#pred':>6} │ "
          f"{'P':>7}{'R':>7}{'F1':>7} {'#pred':>6}")
    print("─" * 75)

    for thr in THRESHOLDS:
        agg = {k: 0 for k in ("tp_b", "fp_b", "fn_b", "np_b",
                              "tp_o", "fp_o", "fn_o", "np_o")}
        for d in data.values():
            preds_t = [(b, c) for b, c in d["preds"] if c >= thr]
            # baseline
            is_tp, matched = eval_frame(preds_t, d["gts"])
            agg["tp_b"] += sum(is_tp); agg["fp_b"] += sum(not t for t in is_tp)
            agg["fn_b"] += len(d["gts"]) - len(matched); agg["np_b"] += len(preds_t)
            # oracle: chỉ giữ pred có tâm trong person box
            preds_o = [(b, c) for b, c in preds_t if center_in_any(b, d["persons"])]
            is_tp_o, matched_o = eval_frame(preds_o, d["gts"])
            agg["tp_o"] += sum(is_tp_o); agg["fp_o"] += sum(not t for t in is_tp_o)
            agg["fn_o"] += len(d["gts"]) - len(matched_o); agg["np_o"] += len(preds_o)

        pb, rb, fb = prf(agg["tp_b"], agg["fp_b"], agg["fn_b"])
        po, ro, fo = prf(agg["tp_o"], agg["fp_o"], agg["fn_o"])
        print(f"{thr:>5} │ {pb:>7.3f}{rb:>7.3f}{fb:>7.3f} {agg['np_b']:>6} │ "
              f"{po:>7.3f}{ro:>7.3f}{fo:>7.3f} {agg['np_o']:>6}")
        results["sweep"].append({
            "thr": thr,
            "baseline": {"P": pb, "R": rb, "F1": fb, "n_pred": agg["np_b"],
                         "tp": agg["tp_b"], "fp": agg["fp_b"], "fn": agg["fn_b"]},
            "oracle":   {"P": po, "R": ro, "F1": fo, "n_pred": agg["np_o"],
                         "tp": agg["tp_o"], "fp": agg["fp_o"], "fn": agg["fn_o"]},
        })

    # ── Phân rã lỗi tại threshold 0.05 (recall cao nhất) ────────────────────
    thr = 0.05
    fp_in, fp_out = 0, 0
    fn_by_bin = defaultdict(int)
    fn_in_person, fn_out_person = 0, 0
    gt_in_person, gt_out_person = 0, 0
    tp_by_bin = defaultdict(int)

    for d in data.values():
        preds_t = [(b, c) for b, c in d["preds"] if c >= thr]
        is_tp, matched = eval_frame(preds_t, d["gts"])
        for (box, _c), t in zip(preds_t, is_tp):
            if not t:
                if center_in_any(box, d["persons"]):
                    fp_in += 1
                else:
                    fp_out += 1
        for j, g in enumerate(d["gts"]):
            longest = max(g[2]-g[0], g[3]-g[1])
            in_p = center_in_any(g, d["persons"])
            if in_p: gt_in_person += 1
            else:    gt_out_person += 1
            for lo, hi, name in SIZE_BINS:
                if lo <= longest < hi:
                    if j in matched:
                        tp_by_bin[name] += 1
                    else:
                        fn_by_bin[name] += 1
                    break
            if j not in matched:
                if in_p: fn_in_person += 1
                else:    fn_out_person += 1

    n_fp = fp_in + fp_out
    print(f"\n══ Phân rã lỗi @ thr={thr} ══")
    print(f"\nFP tổng: {n_fp}")
    print(f"  ngoài person box : {fp_out:>5}  ({100*fp_out/max(n_fp,1):.1f}%)"
          f"   ← person-ROI loại được")
    print(f"  trong person box : {fp_in:>5}  ({100*fp_in/max(n_fp,1):.1f}%)"
          f"   ← cần verification tầng WHAT")
    h0 = fp_out / max(n_fp, 1)
    print(f"\n  H0 (≥70% FP ngoài person): {'✓ ĐẠT' if h0 >= 0.70 else '✗ KHÔNG ĐẠT'}"
          f" ({100*h0:.1f}%)")

    print(f"\nGT phân bố: {gt_in_person} trong person box, "
          f"{gt_out_person} ngoài ({100*gt_out_person/max(n_gt_total,1):.1f}% "
          f"— biển quảng cáo / người bị YOLO sót)")

    print(f"\nFN theo kích thước (cạnh dài GT, px):")
    print(f"  {'bin':<18}{'#FN':>6}{'#TP':>6}{'miss rate':>11}")
    for lo, hi, name in SIZE_BINS:
        fn_c, tp_c = fn_by_bin[name], tp_by_bin[name]
        tot = fn_c + tp_c
        if tot:
            print(f"  {name:<18}{fn_c:>6}{tp_c:>6}{100*fn_c/tot:>10.1f}%")
    print(f"\nFN theo vị trí: {fn_in_person} trong person / {fn_out_person} ngoài")

    results["decompose_thr005"] = {
        "fp_outside_person": fp_out, "fp_inside_person": fp_in,
        "h0_frac_fp_outside": h0, "h0_pass": h0 >= 0.70,
        "gt_in_person": gt_in_person, "gt_out_person": gt_out_person,
        "fn_by_size": dict(fn_by_bin), "tp_by_size": dict(tp_by_bin),
        "fn_in_person": fn_in_person, "fn_out_person": fn_out_person,
    }
    (a.out / "stage0_report.json").write_text(json.dumps(results, indent=2))
    print(f"\n[json] {a.out / 'stage0_report.json'}")

    # ── Visualize vài frame ─────────────────────────────────────────────────
    if a.viz:
        viz_dir = a.out / "viz"; viz_dir.mkdir(exist_ok=True)
        for stem in list(data)[:a.viz]:
            d = data[stem]
            img = cv2.imread(str(d["path"]))
            for pb in d["persons"]:                       # person: xanh dương
                cv2.rectangle(img, (int(pb[0]), int(pb[1])),
                              (int(pb[2]), int(pb[3])), (255, 160, 0), 2)
            preds_t = [(b, c) for b, c in d["preds"] if c >= thr]
            is_tp, matched = eval_frame(preds_t, d["gts"])
            for (b, _c), t in zip(preds_t, is_tp):        # TP xanh lá / FP đỏ
                col = (0, 200, 0) if t else (0, 0, 255)
                cv2.rectangle(img, (int(b[0]), int(b[1])),
                              (int(b[2]), int(b[3])), col, 1)
            for j, g in enumerate(d["gts"]):              # FN: vàng đậm
                if j not in matched:
                    cv2.rectangle(img, (int(g[0]), int(g[1])),
                                  (int(g[2]), int(g[3])), (0, 220, 255), 2)
            cv2.imwrite(str(viz_dir / f"{stem}.jpg"), img)
        print(f"[viz] {a.viz} frame → {viz_dir}  "
              f"(xanh dương=person, xanh lá=TP, đỏ=FP, vàng=FN)")


if __name__ == "__main__":
    main()
