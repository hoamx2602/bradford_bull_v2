"""Đo sai số end-to-end của hệ (metric sản phẩm) trên trận gold.

Đây là metric KHÁCH HÀNG quan tâm, không phải mAP: với mỗi nhà tài trợ, hệ phải
trả đúng "logo xuất hiện bao nhiêu giây" và "to bao nhiêu % màn hình". File này
so kết quả hệ (pred) với ground-truth gán tay (gt) ở cấp trận:

  - exposure-seconds MAE / MAPE  (per-brand + tổng)
  - visibility% MAE
  - (tùy chọn) temporal IoU nếu có segments [start,end] → đo khớp thời điểm,
    không chỉ tổng thời lượng

Self-contained: chỉ numpy.

Định dạng input — JSON cho mỗi trận (pred và gt cùng schema):
    {
      "video": "bradford_vs_hull",
      "fps": 25,
      "brands": {
        "pepsi":  {"exposure_sec": 42.5, "visibility_pct": 3.1,
                    "segments": [[10.0, 14.2], [88.0, 92.3]]},
        "toyota": {"exposure_sec": 12.0, "visibility_pct": 1.2}
      }
    }
  - "segments" tùy chọn; nếu thiếu, chỉ tính theo exposure_sec/visibility_pct.
  - brand có ở bên này thiếu bên kia → coi như 0 (phạt đúng false pos/neg).

Chạy:
    python auto_label/eval_exposure.py --pred pred.json --gt gt.json
    python auto_label/eval_exposure.py --selftest
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _merge(segs: list[list[float]]) -> list[tuple[float, float]]:
    """Gộp các đoạn [start,end] chồng lấn → danh sách rời nhau, đã sort."""
    if not segs:
        return []
    s = sorted((float(a), float(b)) for a, b in segs)
    out = [list(s[0])]
    for a, b in s[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _total(segs) -> float:
    return sum(b - a for a, b in segs)


def _intersection(p, g) -> float:
    """Tổng độ dài giao của hai danh sách đoạn rời nhau."""
    i = j = 0
    inter = 0.0
    while i < len(p) and j < len(g):
        lo = max(p[i][0], g[j][0])
        hi = min(p[i][1], g[j][1])
        if hi > lo:
            inter += hi - lo
        if p[i][1] < g[j][1]:
            i += 1
        else:
            j += 1
    return inter


def temporal_iou(pred_segs, gt_segs) -> float:
    p, g = _merge(pred_segs), _merge(gt_segs)
    inter = _intersection(p, g)
    union = _total(p) + _total(g) - inter
    return inter / union if union > 0 else float("nan")


def evaluate(pred: dict, gt: dict) -> dict:
    pb = pred.get("brands", {})
    gb = gt.get("brands", {})
    brands = sorted(set(pb) | set(gb))

    per_brand: dict[str, dict] = {}
    sec_abs, vis_abs, gt_secs = [], [], []
    for b in brands:
        pe = pb.get(b, {})
        ge = gb.get(b, {})
        p_sec = float(pe.get("exposure_sec", 0.0))
        g_sec = float(ge.get("exposure_sec", 0.0))
        p_vis = float(pe.get("visibility_pct", 0.0))
        g_vis = float(ge.get("visibility_pct", 0.0))
        d = {
            "pred_sec": p_sec, "gt_sec": g_sec,
            "abs_err_sec": abs(p_sec - g_sec),
            "pred_vis": p_vis, "gt_vis": g_vis,
            "abs_err_vis": abs(p_vis - g_vis),
        }
        if "segments" in pe or "segments" in ge:
            d["temporal_iou"] = temporal_iou(
                pe.get("segments", []), ge.get("segments", []))
        per_brand[b] = d
        sec_abs.append(d["abs_err_sec"])
        vis_abs.append(d["abs_err_vis"])
        gt_secs.append(g_sec)

    sec_abs = np.array(sec_abs); vis_abs = np.array(vis_abs)
    gt_secs = np.array(gt_secs)
    denom = gt_secs.sum()
    tious = [d["temporal_iou"] for d in per_brand.values()
             if "temporal_iou" in d and not np.isnan(d["temporal_iou"])]

    return {
        "video": gt.get("video", pred.get("video", "?")),
        "n_brands": len(brands),
        "exposure_sec_MAE": float(sec_abs.mean()) if len(sec_abs) else 0.0,
        "exposure_sec_MAPE": float(sec_abs.sum() / denom) if denom else float("nan"),
        "visibility_pct_MAE": float(vis_abs.mean()) if len(vis_abs) else 0.0,
        "mean_temporal_iou": float(np.mean(tious)) if tious else None,
        "per_brand": per_brand,
    }


def report(res: dict) -> None:
    print(f"\n  [Exposure]  video: {res['video']}   brands: {res['n_brands']}")
    print("  " + "-" * 64)
    print(f"  exposure-seconds MAE : {res['exposure_sec_MAE']:.3f} s")
    print(f"  exposure-seconds MAPE: {res['exposure_sec_MAPE']:.3%}")
    print(f"  visibility%      MAE : {res['visibility_pct_MAE']:.3f}")
    if res["mean_temporal_iou"] is not None:
        print(f"  mean temporal IoU    : {res['mean_temporal_iou']:.3f}")
    print("  " + "-" * 64)
    print(f"  {'brand':<18}{'pred_s':>9}{'gt_s':>9}{'|Δ|s':>8}"
          f"{'|Δ|vis':>9}")
    for b, d in sorted(res["per_brand"].items()):
        print(f"  {b:<18}{d['pred_sec']:>9.1f}{d['gt_sec']:>9.1f}"
              f"{d['abs_err_sec']:>8.1f}{d['abs_err_vis']:>9.2f}")
    print()


def _selftest() -> None:
    pred = {"video": "t", "fps": 25, "brands": {
        "pepsi": {"exposure_sec": 40.0, "visibility_pct": 3.0,
                  "segments": [[10, 14], [88, 92]]},
        "ghost": {"exposure_sec": 5.0, "visibility_pct": 0.5},
    }}
    gt = {"video": "t", "fps": 25, "brands": {
        "pepsi": {"exposure_sec": 42.0, "visibility_pct": 3.1,
                  "segments": [[10, 14], [88, 92]]},
        "toyota": {"exposure_sec": 12.0, "visibility_pct": 1.0},
    }}
    res = evaluate(pred, gt)
    # brands = {pepsi, ghost, toyota}; |Δ|s = |40-42|, |5-0|, |0-12| = 2,5,12 → MAE 19/3
    assert abs(res["exposure_sec_MAE"] - (2 + 5 + 12) / 3) < 1e-9, "MAE sai"
    # pepsi segments trùng khít → temporal IoU 1.0; brand khác thiếu segments
    assert abs(res["per_brand"]["pepsi"]["temporal_iou"] - 1.0) < 1e-9, "tIoU sai"
    # temporal IoU độc lập
    assert abs(temporal_iou([[0, 10]], [[5, 15]]) - (5 / 15)) < 1e-9, "tIoU func sai"
    print("  eval_exposure selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Exposure/EMV error eval (end-to-end)")
    ap.add_argument("--pred", type=Path, help="JSON kết quả hệ")
    ap.add_argument("--gt", type=Path, help="JSON ground-truth gán tay")
    ap.add_argument("--json", type=Path, default=None, help="ghi JSON")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        _selftest(); return
    if not a.pred or not a.gt:
        ap.error("cần --pred và --gt (hoặc --selftest)")

    res = evaluate(json.loads(a.pred.read_text()), json.loads(a.gt.read_text()))
    report(res)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=2))
        print(f"  [json] {a.json}")


if __name__ == "__main__":
    main()
