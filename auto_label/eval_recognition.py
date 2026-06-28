"""Đo chất lượng Tầng 2 (Recognizer) trên gold set.

Tầng 2 = nhận crop logo (do Tầng 1 cắt) → so embedding với Template DB → gán
brand, hoặc trả "unknown" nếu similarity < ngưỡng. File này chấm:

  - closed-set top-1 accuracy (chỉ trên crop có GT là brand đã biết)
  - per-brand precision / recall
  - các cặp nhầm lẫn (confusion) hay gặp — quan trọng cho logo giống nhau
    (cùng nhà tài trợ trên 2 đội — bài toán team-filter cũ)
  - open-set AUROC: tách "logo trong DB" vs "logo lạ/ngoài DB" bằng điểm
    similarity → đo khả năng TỪ CHỐI unknown (an toàn doanh thu)
  - tại ngưỡng τ: unknown-rejection rate & known-acceptance rate

Self-contained: chỉ numpy.

Định dạng input — JSONL, mỗi dòng 1 crop:
    {"id": "f0001_0", "gt": "pepsi", "pred": "pepsi", "score": 0.83}
  - gt = "unknown" (hoặc "" / "none" / "distractor") cho logo KHÔNG có trong DB
    (negative cho open-set).
  - pred = brand gần nhất theo embedding (trước khi áp ngưỡng).
  - score = cosine similarity với template gần nhất (∈ [0,1] càng cao càng giống).

Chạy:
    python auto_label/eval_recognition.py --pred preds.jsonl [--tau 0.6]
    python auto_label/eval_recognition.py --selftest
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

UNKNOWN = {"", "unknown", "none", "distractor", "other", "bg", "background"}


def is_unknown(label: str) -> bool:
    return str(label).strip().lower() in UNKNOWN


def load_jsonl(p: Path) -> list[dict]:
    rows = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """AUROC bằng thống kê Mann–Whitney U. labels: 1 = positive (known)."""
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    # xử lý hạng trung bình cho điểm bằng nhau
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            avg = (ranks[order[i]] + ranks[order[j]]) / 2.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
        i = j + 1
    r_pos = ranks[labels == 1].sum()
    n_pos, n_neg = len(pos), len(neg)
    u = r_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def evaluate(rows: list[dict], tau: float) -> dict:
    gts = [r.get("gt", "") for r in rows]
    preds = [r.get("pred", "") for r in rows]
    scores = np.array([float(r.get("score", 1.0)) for r in rows], dtype=float)

    known_mask = np.array([not is_unknown(g) for g in gts])
    n_known = int(known_mask.sum())
    n_unknown = int((~known_mask).sum())

    # closed-set top-1 (chỉ crop GT known) — pred đúng brand VÀ vượt ngưỡng τ
    correct = 0
    per_brand: dict[str, dict] = {}
    confusion: dict[tuple, int] = {}
    for g, p, s in zip(gts, preds, scores):
        if is_unknown(g):
            continue
        per_brand.setdefault(g, {"tp": 0, "fn": 0, "n_gt": 0})
        per_brand[g]["n_gt"] += 1
        accept = s >= tau
        if accept and p == g:
            correct += 1
            per_brand[g]["tp"] += 1
        else:
            per_brand[g]["fn"] += 1
            pred_lbl = p if accept else "unknown"
            if pred_lbl != g:
                confusion[(g, pred_lbl)] = confusion.get((g, pred_lbl), 0) + 1

    top1 = correct / n_known if n_known else float("nan")

    # precision per-brand: trong các crop ĐƯỢC GÁN brand b (accept & pred=b),
    # bao nhiêu thực sự là b
    pred_counts: dict[str, int] = {}
    pred_correct: dict[str, int] = {}
    for g, p, s in zip(gts, preds, scores):
        if s >= tau and not is_unknown(p):
            pred_counts[p] = pred_counts.get(p, 0) + 1
            if p == g:
                pred_correct[p] = pred_correct.get(p, 0) + 1
    for b, d in per_brand.items():
        npred = pred_counts.get(b, 0)
        d["precision"] = (pred_correct.get(b, 0) / npred) if npred else float("nan")
        d["recall"] = d["tp"] / d["n_gt"] if d["n_gt"] else float("nan")

    # open-set: known=1, unknown=0; điểm = score
    labels = known_mask.astype(int)
    auc = auroc(scores, labels)
    # tại ngưỡng τ
    rej_unknown = float(np.mean(scores[~known_mask] < tau)) if n_unknown else float("nan")
    acc_known = float(np.mean(scores[known_mask] >= tau)) if n_known else float("nan")

    top_conf = sorted(confusion.items(), key=lambda kv: -kv[1])[:10]

    return {
        "tau": tau,
        "n_crops": len(rows),
        "n_known": n_known,
        "n_unknown": n_unknown,
        "top1_acc": top1,
        "open_set_auroc": auc,
        "unknown_rejection@tau": rej_unknown,
        "known_acceptance@tau": acc_known,
        "per_brand": per_brand,
        "top_confusions": [{"gt": g, "pred": p, "count": c}
                           for (g, p), c in top_conf],
    }


def calibrate(rows: list[dict], target_known_acc: float = 0.95) -> dict:
    """Chọn ngưỡng τ vận hành trên một validation split có nhãn known/unknown.
    - tau_target: τ cao nhất giữ known-acceptance ≥ target, tối đa unknown-rejection.
    - tau_youden: τ tối đa (known-acc + unknown-rej − 1) (điểm cân bằng).
    Trả None nếu không τ nào đạt target (gợi ý: cần encoder/kênh tốt hơn)."""
    s = np.array([float(r.get("score", 1.0)) for r in rows], float)
    y = np.array([0 if is_unknown(r.get("gt", "")) else 1 for r in rows])
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return {"error": "cần cả known lẫn unknown trong validation"}
    cand = np.unique(s)
    tgt = None  # (tau, ka, ur)
    you = (-1.0, None, 0.0, 0.0)  # (J, tau, ka, ur)
    for t in cand:
        ka = float((pos >= t).mean())
        ur = float((neg < t).mean())
        if ka >= target_known_acc and ur > 0 and (tgt is None or ur > tgt[2]):
            tgt = (float(t), ka, ur)   # τ chỉ hữu ích nếu reject được unknown
        j = ka + ur - 1
        if j > you[0]:
            you = (j, float(t), ka, ur)
    return {
        "auroc": auroc(s, y),
        "target_known_acc": target_known_acc,
        "tau_target": None if tgt is None else {
            "tau": tgt[0], "known_acc": tgt[1], "unknown_rej": tgt[2]},
        "tau_youden": {"tau": you[1], "known_acc": you[2],
                       "unknown_rej": you[3], "J": you[0]},
    }


def report_calibrate(c: dict) -> None:
    print("\n  [Calibrate τ]")
    if "error" in c:
        print("  ", c["error"]); return
    print(f"  AUROC = {c['auroc']:.3f}")
    tt = c["tau_target"]
    if tt:
        print(f"  τ* (known-acc≥{c['target_known_acc']}): τ={tt['tau']:.3f} → "
              f"known-acc={tt['known_acc']:.3f}, unknown-rej={tt['unknown_rej']:.3f}")
    else:
        print(f"  ⚠ Không τ nào giữ known-acc≥{c['target_known_acc']} mà reject được "
              "unknown → encoder/kênh chưa đủ tách (cần OCR/fine-tune).")
    y = c["tau_youden"]
    print(f"  τ Youden (cân bằng): τ={y['tau']:.3f} → known-acc={y['known_acc']:.3f}, "
          f"unknown-rej={y['unknown_rej']:.3f}  (J={y['J']:.3f})")


def report(res: dict) -> None:
    print(f"\n  [Recognition]  crops: {res['n_crops']}  "
          f"(known {res['n_known']}, unknown {res['n_unknown']})  τ={res['tau']}")
    print("  " + "-" * 58)
    print(f"  closed-set top-1 acc      : {res['top1_acc']:.4f}")
    print(f"  open-set AUROC            : {res['open_set_auroc']:.4f}")
    print(f"  unknown-rejection @ τ     : {res['unknown_rejection@tau']:.4f}")
    print(f"  known-acceptance  @ τ     : {res['known_acceptance@tau']:.4f}")
    print("  " + "-" * 58)
    print(f"  {'brand':<20}{'prec':>9}{'recall':>9}{'#gt':>7}")
    for b, d in sorted(res["per_brand"].items()):
        print(f"  {b:<20}{d['precision']:>9.3f}{d['recall']:>9.3f}{d['n_gt']:>7}")
    if res["top_confusions"]:
        print("  " + "-" * 58)
        print("  top confusions (gt → pred):")
        for c in res["top_confusions"]:
            print(f"    {c['gt']:<18} → {c['pred']:<18} ×{c['count']}")
    print()


def _selftest() -> None:
    # tách hoàn hảo: known điểm cao, unknown điểm thấp, pred đúng hết
    rows = [
        {"id": "1", "gt": "pepsi", "pred": "pepsi", "score": 0.9},
        {"id": "2", "gt": "toyota", "pred": "toyota", "score": 0.85},
        {"id": "3", "gt": "unknown", "pred": "pepsi", "score": 0.2},
        {"id": "4", "gt": "unknown", "pred": "toyota", "score": 0.3},
    ]
    res = evaluate(rows, tau=0.6)
    assert abs(res["top1_acc"] - 1.0) < 1e-9, "top1 phải = 1"
    assert abs(res["open_set_auroc"] - 1.0) < 1e-9, "AUROC tách hoàn hảo phải = 1"
    assert abs(res["unknown_rejection@tau"] - 1.0) < 1e-9, "phải từ chối hết unknown"
    assert abs(res["known_acceptance@tau"] - 1.0) < 1e-9, "phải nhận hết known"
    # AUROC trộn ngẫu nhiên đối xứng ~0.5
    sc = np.array([0.5, 0.5, 0.5, 0.5]); lb = np.array([1, 0, 1, 0])
    assert abs(auroc(sc, lb) - 0.5) < 1e-9, "điểm bằng nhau → AUROC 0.5"
    print("  eval_recognition selftest: OK ✅")


def main() -> None:
    ap = argparse.ArgumentParser(description="Recognition eval (Tầng 2)")
    ap.add_argument("--pred", type=Path, help="JSONL: id, gt, pred, score")
    ap.add_argument("--tau", type=float, default=0.6, help="ngưỡng accept (default 0.6)")
    ap.add_argument("--json", type=Path, default=None, help="ghi JSON")
    ap.add_argument("--calibrate", action="store_true",
                    help="chọn τ vận hành trên validation (cần cả known+unknown)")
    ap.add_argument("--target-known-acc", dest="target_known_acc", type=float,
                    default=0.95, help="ngưỡng known-acceptance mục tiêu khi calibrate")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        _selftest(); return
    if not a.pred:
        ap.error("cần --pred (hoặc --selftest)")

    rows = load_jsonl(a.pred)
    res = evaluate(rows, a.tau)
    report(res)
    if a.calibrate:
        c = calibrate(rows, a.target_known_acc)
        report_calibrate(c)
        res["calibrate"] = c
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=2))
        print(f"  [json] {a.json}")


if __name__ == "__main__":
    main()
