"""Đo mAP cho ORIENTED bounding box (OBB) trên gold set.

Vì sao OBB chứ không HBB: con số sản phẩm cuối là **visibility%** → feed EMV.
Axis-aligned box (HBB) phủ cả logo lẫn nền cho logo nghiêng/cong → thổi phồng
diện tích → sai visibility (xem ExposureEngine, arXiv 2510.04739). Localizer nên
xuất oriented box ngay từ đầu; file này chấm chất lượng OBB đó.

Self-contained: chỉ numpy + opencv. AP kiểu COCO (all-point), mAP@0.5 và
mAP@[.5:.95], AP per-class. IoU = polygon IoU (Sutherland–Hodgman + shoelace).

Định dạng nhãn (Ultralytics OBB, normalized [0,1]):
    GT  :  cls x1 y1 x2 y2 x3 y3 x4 y4
    PRED:  cls x1 y1 x2 y2 x3 y3 x4 y4 conf
Tương thích ngược: dòng 4 toạ độ (cx cy w h [conf]) kiểu HBB cũng đọc được —
tự quy thành quad axis-aligned, nên dùng chung gold set với eval_map.py.

Bố cục thư mục: giống eval_map.py (gold/images, gold/labels, pred/labels).

Chạy:
    python auto_label/eval_obb.py --gold data/gold --pred data/auto_label
    python auto_label/eval_obb.py --selftest
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    import cv2
except Exception:  # opencv là optional cho --selftest
    cv2 = None

IOU_THRS = np.round(np.arange(0.5, 1.0, 0.05), 2)


# --------------------------------------------------------------------------- #
# Hình học polygon
# --------------------------------------------------------------------------- #

def _poly_area(poly: list[tuple[float, float]]) -> float:
    """Diện tích shoelace (luôn dương)."""
    n = len(poly)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def _ensure_ccw(poly: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Đảm bảo winding ngược chiều kim đồng hồ (cho test 'inside' nhất quán)."""
    s = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return poly if s >= 0 else poly[::-1]


def _clip_polygon(subject, clip_poly):
    """Sutherland–Hodgman: cắt subject bằng clip_poly (cả hai LỒI, CCW)."""
    def inside(p, a, b):  # p nằm bên trái cạnh có hướng a->b
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= 0

    def seg_intersect(a, b, s, e):  # giao của đường a-b với đoạn s-e
        x1, y1 = a; x2, y2 = b
        x3, y3 = s; x4, y4 = e
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return e
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    output = list(subject)
    n = len(clip_poly)
    for i in range(n):
        a = clip_poly[i]
        b = clip_poly[(i + 1) % n]
        inp = output
        output = []
        if not inp:
            break
        s = inp[-1]
        for e in inp:
            if inside(e, a, b):
                if not inside(s, a, b):
                    output.append(seg_intersect(a, b, s, e))
                output.append(e)
            elif inside(s, a, b):
                output.append(seg_intersect(a, b, s, e))
            s = e
    return output


def poly_iou(a, b) -> float:
    """IoU của hai tứ giác lồi (list 4 điểm pixel-space)."""
    pa = _ensure_ccw(a)
    pb = _ensure_ccw(b)
    inter = _poly_area(_clip_polygon(pa, pb))
    if inter <= 0:
        return 0.0
    union = _poly_area(pa) + _poly_area(pb) - inter
    return inter / union if union > 0 else 0.0


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #

def load_obb_file(p: Path, with_conf: bool) -> list[tuple]:
    """Đọc 1 file nhãn -> list (cls, quad[(x,y)*4 normalized], conf).

    Chấp nhận cả OBB (8 toạ độ) lẫn HBB (cx cy w h) → quy về quad.
    """
    out: list[tuple] = []
    if not p.exists():
        return out
    for line in p.read_text().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        cls = int(float(parts[0]))
        vals = [float(v) for v in parts[1:]]
        if len(vals) >= 8:  # OBB
            quad = [(vals[0], vals[1]), (vals[2], vals[3]),
                    (vals[4], vals[5]), (vals[6], vals[7])]
            conf = float(vals[8]) if (with_conf and len(vals) >= 9) else 1.0
        else:               # HBB cx cy w h [conf] -> quad axis-aligned
            cx, cy, w, h = vals[:4]
            x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
            quad = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
            conf = float(vals[4]) if (with_conf and len(vals) >= 5) else 1.0
        out.append((cls, quad, conf))
    return out


def quad_to_pixels(quad, W: int, H: int):
    return [(x * W, y * H) for (x, y) in quad]


def image_size(gold: Path, stem: str) -> tuple[int, int]:
    if cv2 is None:
        return 1, 1
    for ext in (".jpg", ".jpeg", ".png"):
        f = gold / "images" / f"{stem}{ext}"
        if f.exists():
            img = cv2.imread(str(f))
            if img is not None:
                return img.shape[1], img.shape[0]
    return 1, 1


# --------------------------------------------------------------------------- #
# AP (giống eval_map.py, dùng polygon IoU)
# --------------------------------------------------------------------------- #

def average_precision(recall: np.ndarray, precision: np.ndarray) -> float:
    mrec = np.concatenate(([0.0], recall, [1.0]))
    mpre = np.concatenate(([0.0], precision, [0.0]))
    for i in range(mpre.size - 1, 0, -1):
        mpre[i - 1] = max(mpre[i - 1], mpre[i])
    idx = np.where(mrec[1:] != mrec[:-1])[0]
    return float(np.sum((mrec[idx + 1] - mrec[idx]) * mpre[idx + 1]))


def ap_for_class(preds: list, gts: dict, thr: float) -> tuple[float, int]:
    """preds: list (stem, conf, quad_px) sort theo conf giảm.
    gts: dict stem -> list quad_px."""
    n_gt = sum(len(v) for v in gts.values())
    if n_gt == 0:
        return float("nan"), 0
    matched: dict[str, set] = {s: set() for s in gts}
    tp = np.zeros(len(preds)); fp = np.zeros(len(preds))
    for i, (stem, _conf, quad) in enumerate(preds):
        cand = gts.get(stem, [])
        best_iou, best_j = 0.0, -1
        for j, g in enumerate(cand):
            if j in matched[stem]:
                continue
            v = poly_iou(quad, g)
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

    gts_by_cls: dict[int, dict[str, list]] = {}
    preds_by_cls: dict[int, list] = {}
    classes: set[int] = set()
    used_fallback = False

    for stem in stems:
        W, H = image_size(gold, stem)
        if (W, H) == (1, 1):
            used_fallback = True
        for cls, quad, _ in load_obb_file(gt_dir / f"{stem}.txt", with_conf=False):
            classes.add(cls)
            gts_by_cls.setdefault(cls, {}).setdefault(stem, []).append(
                quad_to_pixels(quad, W, H))
        for cls, quad, conf in load_obb_file(pr_dir / f"{stem}.txt", with_conf=True):
            classes.add(cls)
            preds_by_cls.setdefault(cls, []).append(
                (stem, conf, quad_to_pixels(quad, W, H)))

    per_class: dict[int, dict] = {}
    map50_list, map5095_list = [], []
    for c in sorted(classes):
        preds = sorted(preds_by_cls.get(c, []), key=lambda x: -x[1])
        gts = gts_by_cls.get(c, {})
        n_gt = sum(len(v) for v in gts.values())
        if n_gt == 0:
            continue
        aps = {float(t): ap_for_class(preds, gts, t)[0] for t in IOU_THRS}
        ap50 = aps[0.5]
        ap5095 = float(np.nanmean(list(aps.values())))
        per_class[c] = {"ap50": ap50, "ap5095": ap5095, "n_gt": n_gt,
                        "n_pred": len(preds)}
        map50_list.append(ap50); map5095_list.append(ap5095)

    return {
        "metric": "obb",
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
    print(f"\n  [OBB]  images: {res['n_images']}   "
          f"classes evaluated: {len(res['per_class'])}")
    if res["iou_fallback_normalized"]:
        print("  ⚠ thiếu ảnh trong gold/images → IoU normalized (kém chính xác).")
    print(f"  {'class':<22}{'AP@.5':>9}{'AP@.5:.95':>12}{'#gt':>7}{'#pred':>8}")
    print("  " + "-" * 58)
    for c, m in sorted(res["per_class"].items()):
        nm = names.get(c, str(c))
        print(f"  {nm:<22}{m['ap50']:>9.4f}{m['ap5095']:>12.4f}"
              f"{m['n_gt']:>7}{m['n_pred']:>8}")
    print("  " + "-" * 58)
    print(f"  {'mAP@0.5 (OBB)':<22}{res['map50']:>9.4f}")
    print(f"  {'mAP@0.5:0.95 (OBB)':<22}{res['map5095']:>21.4f}\n")


def _selftest() -> None:
    # IoU: hai ô vuông trùng khít -> 1.0
    sq = [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert abs(poly_iou(sq, sq) - 1.0) < 1e-9, "IoU trùng khít phải = 1"
    # rời nhau -> 0
    far = [(5, 5), (6, 5), (6, 6), (5, 6)]
    assert poly_iou(sq, far) == 0.0, "IoU rời nhau phải = 0"
    # chồng một nửa theo x -> inter 0.5, union 1.5 -> 1/3
    half = [(0.5, 0), (1.5, 0), (1.5, 1), (0.5, 1)]
    assert abs(poly_iou(sq, half) - (0.5 / 1.5)) < 1e-9, "IoU nửa chồng sai"
    # quad CW vẫn ra đúng (ensure_ccw)
    sq_cw = sq[::-1]
    assert abs(poly_iou(sq_cw, sq) - 1.0) < 1e-9, "winding CW phải bình thường"
    # AP hoàn hảo = 1.0
    gts = {"a": [[(0, 0), (10, 0), (10, 10), (0, 10)]]}
    preds = [("a", 0.9, [(0, 0), (10, 0), (10, 10), (0, 10)])]
    ap, n = ap_for_class(preds, gts, 0.5)
    assert n == 1 and abs(ap - 1.0) < 1e-9, "AP dự đoán hoàn hảo phải = 1"
    print("  eval_obb selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="OBB mAP eval (gold set)")
    ap.add_argument("--gold", type=Path, help="gold: images/ + labels/")
    ap.add_argument("--pred", type=Path, help="pred: labels/ (OBB + conf)")
    ap.add_argument("--names", type=Path, default=None, help="data.yaml tên class")
    ap.add_argument("--json", type=Path, default=None, help="ghi JSON")
    ap.add_argument("--selftest", action="store_true",
                    help="chạy self-test hình học (không cần dữ liệu)")
    a = ap.parse_args()

    if a.selftest:
        _selftest(); return
    if not a.gold or not a.pred:
        ap.error("cần --gold và --pred (hoặc --selftest)")

    res = evaluate(a.gold, a.pred)
    report(res, load_names(a.names))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=2))
        print(f"  [json] {a.json}")


if __name__ == "__main__":
    main()
