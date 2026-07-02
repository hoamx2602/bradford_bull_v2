"""Đo mAP trên gold set — so dự đoán (YOLO format) với ground-truth gán tay.

Dùng để lấy số THẬT cho paper (thay các \\TODOnum placeholder): chấm chất lượng
nhãn auto của teacher hoặc dự đoán của student so với một "gold test set" nhỏ
annotate tay (chỉ để eval, không train — xem paper_cyberworlds.md §7.1).

Self-contained: chỉ cần numpy + opencv (đọc kích thước ảnh). Tính AP kiểu COCO
(101-point interpolation), báo cáo mAP@0.5 và mAP@[.5:.95] + AP per-class.

Bố cục thư mục mong đợi:
    gold/
      images/<stem>.jpg          # để lấy (W,H) cho IoU pixel-space
      labels/<stem>.txt          # GT YOLO: "cls cx cy w h"   (normalized)
    pred/
      labels/<stem>.txt          # PRED YOLO: "cls cx cy w h conf"
                                 #   (thiếu conf -> coi như 1.0)

Chạy:
    python auto_label/eval_map.py --gold data/gold --pred data/auto_label
    python auto_label/eval_map.py --gold data/gold --pred data/auto_label \\
        --names data/auto_label/data.yaml --json eval_runs/teacher.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

IOU_THRS = np.round(np.arange(0.5, 1.0, 0.05), 2)  # 0.50 .. 0.95


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #

def load_label_file(p: Path, with_conf: bool) -> list[tuple]:
    """Đọc 1 file YOLO → list (cls, cx, cy, w, h, conf).

    Hỗ trợ cả AABB (5 fields) và OBB (9 fields: cls x1 y1 x2 y2 x3 y3 x4 y4).
    OBB được convert thành AABB lấy axis-aligned bounding box từ 4 góc.
    """
    out: list[tuple] = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls = int(float(parts[0]))
        if len(parts) >= 9:
            # OBB format: cls x1 y1 x2 y2 x3 y3 x4 y4 (normalized coords)
            xs = [float(parts[i]) for i in range(1, 9, 2)]
            ys = [float(parts[i]) for i in range(2, 9, 2)]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            cx = (x1 + x2) / 2; cy = (y1 + y2) / 2
            w = x2 - x1; h = y2 - y1
            conf = 1.0
        else:
            # AABB format: cls cx cy w h [conf]
            cx, cy, w, h = (float(v) for v in parts[1:5])
            conf = float(parts[5]) if (with_conf and len(parts) >= 6) else 1.0
        out.append((cls, cx, cy, w, h, conf))
    return out


def yolo_to_xyxy(box, W: int, H: int) -> tuple[float, float, float, float]:
    _, cx, cy, w, h, _ = box
    return ((cx - w / 2) * W, (cy - h / 2) * H,
            (cx + w / 2) * W, (cy + h / 2) * H)


def image_size(gold: Path, stem: str) -> tuple[int, int]:
    for ext in (".jpg", ".jpeg", ".png"):
        f = gold / "images" / f"{stem}{ext}"
        if f.exists():
            img = cv2.imread(str(f))
            if img is not None:
                return img.shape[1], img.shape[0]  # W, H
    return 1, 1  # fallback: IoU trong không gian normalized (cảnh báo riêng)


# --------------------------------------------------------------------------- #
# Hình học + AP
# --------------------------------------------------------------------------- #

def iou(a, b) -> float:
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(ix1 - ix0, 0), max(iy1 - iy0, 0)
    inter = iw * ih
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def average_precision(recall: np.ndarray, precision: np.ndarray) -> float:
    """All-point (VOC2010) area under the precision envelope.

    Exact for perfect predictions (AP=1.0); avoids the 101-point sampling
    artifact at a duplicated terminal recall value.
    """
    mrec = np.concatenate(([0.0], recall, [1.0]))
    mpre = np.concatenate(([0.0], precision, [0.0]))
    for i in range(mpre.size - 1, 0, -1):       # precision envelope (monotone)
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    idx = np.where(mrec[1:] != mrec[:-1])[0]    # các bậc recall tăng
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def ap_for_class(preds: list, gts: dict, thr: float) -> tuple[float, int]:
    """preds: list (stem, conf, xyxy) đã sort theo conf giảm.
    gts: dict stem -> list xyxy. Trả (AP, n_gt)."""
    n_gt = sum(len(v) for v in gts.values())
    if n_gt == 0:
        return float("nan"), 0
    matched: dict[str, set] = {s: set() for s in gts}
    tp = np.zeros(len(preds)); fp = np.zeros(len(preds))
    for i, (stem, _conf, box) in enumerate(preds):
        cand = gts.get(stem, [])
        best_iou, best_j = 0.0, -1
        for j, g in enumerate(cand):
            if j in matched[stem]:
                continue
            v = iou(box, g)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_iou >= thr and best_j >= 0:
            tp[i] = 1; matched[stem].add(best_j)
        else:
            fp[i] = 1
    tp_c, fp_c = np.cumsum(tp), np.cumsum(fp)
    recall = tp_c / n_gt
    precision = tp_c / np.maximum(tp_c + fp_c, 1e-9)
    return average_precision(recall, precision), n_gt


# --------------------------------------------------------------------------- #
# Eval chính
# --------------------------------------------------------------------------- #

def evaluate(gold: Path, pred: Path) -> dict:
    gt_dir, pr_dir = gold / "labels", pred / "labels"
    if not gt_dir.is_dir():
        raise SystemExit(f"Không thấy {gt_dir}")
    stems = sorted(p.stem for p in gt_dir.glob("*.txt"))
    if not stems:
        raise SystemExit(f"Không có nhãn GT trong {gt_dir}")

    # gom theo class
    gts_by_cls: dict[int, dict[str, list]] = {}
    preds_by_cls: dict[int, list] = {}
    classes: set[int] = set()
    used_fallback = False

    for stem in stems:
        W, H = image_size(gold, stem)
        if (W, H) == (1, 1):
            used_fallback = True
        for box in load_label_file(gt_dir / f"{stem}.txt", with_conf=False):
            c = box[0]; classes.add(c)
            gts_by_cls.setdefault(c, {}).setdefault(stem, []).append(
                yolo_to_xyxy(box, W, H))
        for box in load_label_file(pr_dir / f"{stem}.txt", with_conf=True):
            c = box[0]; classes.add(c)
            preds_by_cls.setdefault(c, []).append(
                (stem, box[5], yolo_to_xyxy(box, W, H)))

    per_class: dict[int, dict] = {}
    map50_list, map5095_list = [], []
    for c in sorted(classes):
        preds = sorted(preds_by_cls.get(c, []), key=lambda x: -x[1])
        gts = gts_by_cls.get(c, {})
        aps = {float(t): ap_for_class(preds, gts, t)[0] for t in IOU_THRS}
        n_gt = sum(len(v) for v in gts.values())
        if n_gt == 0:
            continue  # COCO: bỏ class không có GT
        ap50 = aps[0.5]
        ap5095 = float(np.nanmean(list(aps.values())))
        per_class[c] = {"ap50": ap50, "ap5095": ap5095, "n_gt": n_gt,
                        "n_pred": len(preds)}
        map50_list.append(ap50); map5095_list.append(ap5095)

    return {
        "map50": float(np.mean(map50_list)) if map50_list else 0.0,
        "map5095": float(np.mean(map5095_list)) if map5095_list else 0.0,
        "per_class": per_class,
        "n_images": len(stems),
        "iou_fallback_normalized": used_fallback,
    }


def load_names(names_path: Path | None) -> dict[int, str]:
    if not names_path or not names_path.is_file():
        return {}
    out: dict[int, str] = {}
    in_names = False
    for line in names_path.read_text().splitlines():
        s = line.strip()
        if s.startswith("names:"):
            in_names = True; continue
        if in_names and ":" in s:
            k, v = s.split(":", 1)
            try:
                out[int(k.strip())] = v.strip()
            except ValueError:
                in_names = False
    return out


def report(res: dict, names: dict[int, str]) -> None:
    print(f"\n  images: {res['n_images']}   "
          f"classes evaluated: {len(res['per_class'])}")
    if res["iou_fallback_normalized"]:
        print("  ⚠ thiếu ảnh trong gold/images → IoU tính trong không gian "
              "normalized (kém chính xác). Bổ sung ảnh để có IoU pixel-space.")
    print(f"  {'class':<22}{'AP@.5':>9}{'AP@.5:.95':>12}{'#gt':>7}{'#pred':>8}")
    print("  " + "-" * 58)
    for c, m in sorted(res["per_class"].items()):
        nm = names.get(c, str(c))
        print(f"  {nm:<22}{m['ap50']:>9.4f}{m['ap5095']:>12.4f}"
              f"{m['n_gt']:>7}{m['n_pred']:>8}")
    print("  " + "-" * 58)
    print(f"  {'mAP@0.5':<22}{res['map50']:>9.4f}")
    print(f"  {'mAP@0.5:0.95':<22}{res['map5095']:>21.4f}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="mAP eval (YOLO format, gold set)")
    ap.add_argument("--gold", required=True, type=Path,
                    help="thư mục gold: images/ + labels/ (GT gán tay)")
    ap.add_argument("--pred", required=True, type=Path,
                    help="thư mục dự đoán: labels/ (YOLO + conf)")
    ap.add_argument("--names", type=Path, default=None,
                    help="data.yaml để hiển thị tên class")
    ap.add_argument("--json", type=Path, default=None,
                    help="ghi kết quả ra file JSON")
    a = ap.parse_args()

    res = evaluate(a.gold, a.pred)
    report(res, load_names(a.names))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=2))
        print(f"  [json] {a.json}")


if __name__ == "__main__":
    main()
