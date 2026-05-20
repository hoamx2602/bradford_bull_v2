"""
Compare sharpness methods against ground-truth labels and find the best threshold.

Usage:
    python eval/eval_sharpness.py --labels labels.csv
    python eval/eval_sharpness.py --labels labels.csv --plot
"""
import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

from frame_selector.sharpness import SCORERS, score_torso_sharpness


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _auc(scores: list[float], labels: list[int]) -> float:
    pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.5
    tp = fp = auc = prev_tp = 0
    for _, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
            auc += tp - prev_tp
            prev_tp = tp
    return auc / (n_pos * n_neg)


def _pr_at(scores: list[float], labels: list[int], thr: float) -> tuple[float, float]:
    pred = [s >= thr for s in scores]
    tp = sum(p and l for p, l in zip(pred, labels))
    fp = sum(p and not l for p, l in zip(pred, labels))
    fn = sum(not p and l for p, l in zip(pred, labels))
    return tp / max(1, tp + fp), tp / max(1, tp + fn)


def _best_threshold(scores: list[float], labels: list[int]) -> tuple[float, float, float]:
    """Return (threshold, precision, recall) maximizing F1."""
    best_f1 = best_thr = best_p = best_r = 0.0
    for thr in np.percentile(scores, np.arange(5, 96, 5)):
        p, r = _pr_at(scores, labels, float(thr))
        f1 = 2 * p * r / max(1e-9, p + r)
        if f1 > best_f1:
            best_f1, best_thr, best_p, best_r = f1, float(thr), p, r
    return best_thr, best_p, best_r


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate(labels_csv: Path, plot: bool = False) -> None:
    rows = []
    with open(labels_csv) as f:
        for row in csv.DictReader(f):
            rows.append(row)

    scores_by_method: dict[str, list[float]] = {m: [] for m in SCORERS}
    labels_binary: list[int] = []

    skipped = 0
    for row in rows:
        path = Path(row.get('path') or row['filename'])
        if not path.exists():
            skipped += 1
            continue
        img = cv2.imread(str(path))
        if img is None:
            skipped += 1
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        labels_binary.append(1 if row['label'].strip() == 'good' else 0)
        for name, fn in SCORERS.items():
            scores_by_method[name].append(fn(gray))

    n = len(labels_binary)
    print(f'Evaluated {n} frames  ({sum(labels_binary)} good, {n - sum(labels_binary)} bad)')
    if skipped:
        print(f'  Warning: {skipped} frames skipped (file not found)')
    if n == 0:
        print('No frames found on disk. Check paths in labels.csv'); return

    print(f'\n{"Method":<12} {"AUC":>6}  {"Precision":>9}  {"Recall":>7}  {"Threshold":>10}')
    print('-' * 55)

    best_method, best_auc = '', 0.0
    for name, scores in scores_by_method.items():
        auc = _auc(scores, labels_binary)
        thr, p, r = _best_threshold(scores, labels_binary)
        print(f'{name:<12} {auc:>6.3f}  {p:>9.3f}  {r:>7.3f}  {thr:>10.2f}')
        if auc > best_auc:
            best_auc, best_method = auc, name

    print(f'\n→ Best method: {best_method} (AUC={best_auc:.3f})')
    print(f'  Use in Config: sharpness_method = "{best_method}"')

    if not plot:
        return

    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(SCORERS), figsize=(5 * len(SCORERS), 4), sharey=False)
    for ax, (name, scores) in zip(axes, scores_by_method.items()):
        good = [s for s, l in zip(scores, labels_binary) if l == 1]
        bad  = [s for s, l in zip(scores, labels_binary) if l == 0]
        thr, _, _ = _best_threshold(scores, labels_binary)
        ax.hist(good, bins=20, alpha=0.6, label=f'good (n={len(good)})', color='green')
        ax.hist(bad,  bins=20, alpha=0.6, label=f'bad  (n={len(bad)})',  color='red')
        ax.axvline(thr, color='black', linestyle='--', label=f'best thr={thr:.1f}')
        ax.set_title(name); ax.legend(fontsize=8); ax.set_xlabel('score')
    fig.suptitle('Sharpness method comparison', fontsize=13)
    plt.tight_layout()
    out = Path('sharpness_eval.png')
    plt.savefig(out, dpi=120)
    print(f'\nPlot saved: {out}')
    plt.show()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--plot', action='store_true')
    args = ap.parse_args()
    evaluate(args.labels, args.plot)
