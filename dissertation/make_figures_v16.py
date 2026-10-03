"""Draw every quantitative figure that version 16 of the dissertation introduces.

    .venv-rfdetr/Scripts/python.exe dissertation/make_figures_v16.py [name ...]

Every value plotted here is read from a recorded measurement in `v16_data/`:

    eval_dump.json      held-out COCO metrics, per-class AP and the confidence
                        sweep for RF-DETR Small and the three YOLO26 baselines,
                        all scored with one pycocotools protocol on the same
                        61 test images
    dataset_dump.json   split composition, annotation geometry and the training
                        curve read from runs/rfdetr_matchsplit_r896/metrics.csv
    breakdown_dump.json condition-stratified held-out results (per match, per
                        camera distance, per lighting label, per box size)

Figures carried over unchanged from version 15 are copied, not redrawn; they
sit in `v16_data/carry_*.png` and are stamped into the media folder by
`stage_media()` so the numbering of the version 16 document is contiguous.

The visual system matches the version 15 plates: maroon for the measured
headline series, gold for anything the reader must not over-read, blue for a
secondary series, and a grey footnote carrying the caveat that belongs with
the picture rather than with the caption.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
from matplotlib import pyplot as plt

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "v16_data"
MEDIA = ROOT / "LogoLens_MSc_Dissertation_v16_media"
MEDIA.mkdir(exist_ok=True)

MAROON = "#8c0b2e"
GOLD = "#c69a2e"
BLUE = "#3b76a8"
TEAL = "#2f7f6f"
INK = "#1a1a1a"
INK2 = "#3f3f3f"
MUTED = "#8a8f98"
GRID = "#dcdcdc"

plt.rcParams.update({
    "figure.dpi": 200, "savefig.dpi": 200,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10,
    "axes.titleweight": "bold", "axes.edgecolor": "#b8b8b8",
    "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "grid.color": GRID, "grid.linewidth": 0.8,
    "legend.frameon": False, "lines.linewidth": 2.0, "lines.markersize": 6,
})


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


EV = load("eval_dump.json")
DS = load("dataset_dump.json")
BD = load("breakdown_dump.json") if (DATA / "breakdown_dump.json").exists() else None
RF = EV["models"]["RF-DETR Small"]

PRETTY = {
    "klg_home": "KLG", "mcp_home": "MCP", "aon_home": "Aon",
    "paints_lacquers_home": "Paints & Lacquers", "top_notch_home": "Top Notch",
    "romantica_home": "Romantica", "asc_group_home": "ASC Group",
    "ellgren_home": "Ellgren", "atm_home": "ATM", "em_workwear_home": "EM Workwear",
    "bartercard_home": "Bartercard", "fairway_home": "Fairway",
    "mna_cladding_home": "MNA Cladding", "chadlaw_home": "Chadlaw",
    "mna_support_service_home": "MNA Support", "cch_home": "CCH",
}


def footnote(fig, text, y=0.005):
    fig.text(0.5, y, text, ha="center", va="bottom", fontsize=9, color=MUTED)


def save(fig, name, footer=None, rect=None):
    if footer:
        footnote(fig, footer)
    fig.tight_layout(rect=rect or [0, 0.035, 1, 1])
    path = MEDIA / name
    fig.savefig(path, bbox_inches="tight", pad_inches=0.22, facecolor="white")
    plt.close(fig)
    print(f"  wrote {path.name}")


def grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)


# ==========================================================================
# 6 — input geometry: what preprocessing does to an already small logo
# ==========================================================================
def fig_input_geometry():
    b = DS["boxes"]
    mw, mh = b["median_w"], b["median_h"]
    lb_h_frac = (1208 * 1080 / 1920) / 1280          # Roboflow "fit" canvas

    cfgs = [
        ("Letterbox\n1208x1280\nR=640", 640, lb_h_frac, GOLD),
        ("Letterbox\n1208x1280\nR=896", 896, lb_h_frac, GOLD),
        ("Native 16:9\nR=512", 512, 1.0, BLUE),
        ("Native 16:9\nR=640", 640, 1.0, BLUE),
        ("Native 16:9\nR=896", 896, 1.0, MAROON),
    ]
    labels, widths, heights, areas, colors = [], [], [], [], []
    for lab, R, frac, col in cfgs:
        w = mw * R / 1920
        h = mh * R * frac / 1080
        labels.append(lab); widths.append(w); heights.append(h)
        areas.append(w * h); colors.append(col)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4))
    fig.suptitle("The median sponsor logo, as the model actually receives it",
                 fontsize=14, fontweight="bold", y=1.0)

    x = np.arange(len(labels))
    ax1.bar(x - 0.19, widths, 0.38, color=colors)
    ax1.bar(x + 0.19, heights, 0.38, color=colors, alpha=0.45)
    for i, (w, h) in enumerate(zip(widths, heights)):
        ax1.text(i - 0.19, w + 0.7, f"{w:.1f}", ha="center", fontsize=9, color=INK2)
        ax1.text(i + 0.19, h + 0.7, f"{h:.1f}", ha="center", fontsize=9, color=INK2)
    ax1.axhline(16, color=INK, linestyle="--", linewidth=1.2)
    ax1.text(-0.42, 17.2, "one 16 px backbone token", ha="left", fontsize=9, color=INK)
    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel("Model-input pixels")
    ax1.set_title("A. Width is fixed by resolution alone; only height responds\n"
                  "to preprocessing", fontsize=11)
    ax1.set_ylim(0, max(max(widths), max(heights)) * 1.34)
    from matplotlib.patches import Patch
    ax1.legend(handles=[Patch(facecolor="#6b6b6b", label="logo width"),
                        Patch(facecolor="#6b6b6b", alpha=0.45, label="logo height")],
               loc="upper left", fontsize=9)
    grid(ax1)

    bars = ax2.bar(x, areas, 0.55, color=colors)
    for i, a in enumerate(areas):
        ax2.text(i, a + 22, f"{a:.0f} px²", ha="center", fontsize=9.5, color=INK2)
    base = areas[0]
    ax2.annotate("", xy=(4, areas[4]), xytext=(0, base),
                 arrowprops=dict(arrowstyle="-|>", color=MAROON, lw=1.6,
                                 connectionstyle="arc3,rad=-0.25"))
    ax2.text(2.0, base + (areas[4] - base) * 0.72,
             f"x{areas[4] / base:.1f} effective area,\nat no extra annotation cost",
             ha="center", fontsize=10, color=MAROON, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylabel("Effective logo area (model-input px²)")
    ax2.set_title("B. Effective area is what the detector has to work with", fontsize=11)
    ax2.set_ylim(0, max(areas) * 1.22)
    grid(ax2)

    save(fig, "figure_06_input_geometry.png",
         f"Median annotated logo measures {mw:.0f} x {mh:.0f} px in the source frame "
         f"(n = {b['n']} boxes). The letterbox canvas leaves "
         f"{100 - lb_h_frac * 100:.0f}% of the input black.")


# ==========================================================================
# 11 — architecture comparison under one protocol
# ==========================================================================
def fig_architecture():
    order = ["YOLO26-n", "YOLO26-s", "YOLO26-m", "RF-DETR Small"]
    m = {k: EV["models"][k] for k in order}
    cols = [GOLD, GOLD, GOLD, MAROON]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.4),
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    fig.suptitle("Detector families scored under one protocol, on the same "
                 "three unseen matches", fontsize=14, fontweight="bold", y=1.0)

    metrics = [("mAP@0.50", "map50"), ("mAP@0.75", "map75"),
               ("mAP@[.50:.95]", "map"), ("best F1", None)]
    x = np.arange(len(metrics))
    width = 0.2
    for i, name in enumerate(order):
        vals = [m[name][k] if k else m[name]["best"]["f1"] for _, k in metrics]
        off = (i - 1.5) * width
        ax1.bar(x + off, vals, width, color=cols[i],
                alpha=1.0 if name.startswith("RF") else 0.35 + 0.2 * i,
                label=f"{name} ({m[name]['params'] / 1e6:.1f}M)")
        for xi, v in zip(x + off, vals):
            ax1.text(xi, v + 0.012, f"{v:.3f}", ha="center", fontsize=7.8,
                     color=INK2, rotation=90, va="bottom")
    ax1.set_xticks(x); ax1.set_xticklabels([n for n, _ in metrics])
    ax1.set_ylabel("Held-out score"); ax1.set_ylim(0, 1.12)
    ax1.set_title("A. The margin widens as the localisation requirement tightens",
                  fontsize=11)
    ax1.legend(loc="upper right", fontsize=8.5, ncol=2)
    grid(ax1)

    for i, name in enumerate(order):
        p = m[name]["params"] / 1e6
        ax2.scatter(p, m[name]["map50"], s=150, color=cols[i], zorder=3,
                    edgecolor="white", linewidth=1.2)
        ax2.annotate(f"{name}\n{m[name]['map50']:.3f}", (p, m[name]["map50"]),
                     textcoords="offset points", xytext=(0, -34),
                     ha="center", fontsize=9, color=INK2)
    yolo = [(m[n]["params"] / 1e6, m[n]["map50"]) for n in order[:3]]
    ax2.plot(*zip(*yolo), color=GOLD, linewidth=1.4, linestyle="--", zorder=2)
    ax2.set_xlabel("Trainable parameters (millions)")
    ax2.set_ylabel("mAP@0.50 on held-out matches")
    ax2.set_title("B. Extra capacity inside one family does not close the gap",
                  fontsize=11)
    ax2.set_ylim(0.42, 1.02); ax2.set_xlim(0, 36)
    grid(ax2)

    save(fig, "figure_11_architecture_comparison.png",
         "Same images, same match-disjoint split, same 896-pixel input and the same "
         "pycocotools scoring. Augmentation recipes and pre-training differ by family "
         "and are not controlled.")


# ==========================================================================
# 9 — confidence sweep and the cost of the operating point
# ==========================================================================
def fig_confidence():
    sw = [r for r in RF["sweep"] if r["conf"] <= 0.90]
    conf = [r["conf"] for r in sw]
    best = RF["best"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.4, 5.2))
    fig.suptitle("Choosing an operating point, and what it costs to be wrong",
                 fontsize=14, fontweight="bold", y=1.0)

    ax1.plot(conf, [r["p"] for r in sw], color=BLUE, marker="o", markersize=3.5,
             label="precision")
    ax1.plot(conf, [r["r"] for r in sw], color=GOLD, marker="o", markersize=3.5,
             label="recall")
    ax1.plot(conf, [r["f1"] for r in sw], color=MAROON, marker="o", markersize=4.5,
             label="F1")
    ax1.axvline(best["conf"], color=INK, linestyle="--", linewidth=1.2)
    ax1.scatter([best["conf"]], [best["f1"]], s=140, facecolor="none",
                edgecolor=MAROON, linewidth=2, zorder=4)
    ax1.annotate(f"best F1 {best['f1']:.3f} at {best['conf']:.2f}\n"
                 f"P {best['p']:.3f} / R {best['r']:.3f}",
                 (best["conf"], best["f1"]), textcoords="offset points",
                 xytext=(14, -46), fontsize=9.5, color=INK,
                 arrowprops=dict(arrowstyle="-", color=MUTED, lw=1))
    band = [r for r in sw if 0.20 <= r["conf"] <= 0.50]
    ax1.axvspan(0.20, 0.50, color=MAROON, alpha=0.06)
    ax1.text(0.35, 0.12, f"F1 varies only {max(r['f1'] for r in band) - min(r['f1'] for r in band):.3f}\n"
                         "across this band", ha="center", fontsize=9, color=MUTED)
    ax1.set_xlabel("Confidence threshold"); ax1.set_ylabel("Score")
    ax1.set_ylim(0, 1.05); ax1.legend(loc="lower left", fontsize=9)
    ax1.set_title("A. Precision, recall and F1 across the sweep", fontsize=11)
    grid(ax1)

    tp = np.array([r["tp"] for r in sw])
    fp = np.array([r["fp"] for r in sw])
    fn = np.array([r["fn"] for r in sw])
    ax2.bar(conf, tp, 0.035, color=MAROON, label="true positives")
    ax2.bar(conf, fp, 0.035, bottom=tp, color=GOLD, label="false positives")
    ax2.bar(conf, -fn, 0.035, color=BLUE, alpha=0.55, label="missed ground truth")
    ax2.axhline(0, color="#b8b8b8", linewidth=0.9)
    ax2.axvline(best["conf"], color=INK, linestyle="--", linewidth=1.2)
    ax2.text(best["conf"] + 0.02, 250,
             f"at 0.35:\n{best['tp']} correct\n{best['fp']} false\n{best['fn']} missed",
             fontsize=9.5, color=INK)
    ax2.set_xlabel("Confidence threshold")
    ax2.set_ylabel("Boxes (165 ground-truth boxes in total)")
    ax2.set_title("B. The same sweep counted in boxes", fontsize=11)
    ax2.legend(loc="upper right", fontsize=9)
    grid(ax2)

    save(fig, "figure_09_confidence_sweep.png",
         "Greedy class-aware matching at IoU 0.50 on the 61 held-out test images. "
         "The threshold was read from these same predictions, so it is an operating "
         "point characterisation rather than an independent estimate.")


# ==========================================================================
# 10 — per-class AP, its support, and what the sparse classes do to the mean
# ==========================================================================
def fig_per_class():
    pc = [c for c in RF["per_class"] if c["ap50"] is not None]
    pc = sorted(pc, key=lambda c: c["ap50"])
    names = [f"{PRETTY.get(c['name'], c['name'])}  (n={c['n']})" for c in pc]
    ap = [c["ap50"] for c in pc]
    cols = [GOLD if c["n"] < 5 else MAROON for c in pc]

    ap_all = np.array([c["ap50"] for c in pc])
    n_all = np.array([c["n"] for c in pc])
    mean_all = ap_all.mean()
    mean_5 = ap_all[n_all >= 5].mean()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.2, 6.6),
                                   gridspec_kw={"width_ratios": [1.45, 1]})
    fig.suptitle("Per-class accuracy cannot be read without its support",
                 fontsize=14, fontweight="bold", y=1.0)

    y = np.arange(len(pc))
    ax1.barh(y, ap, 0.68, color=cols)
    for yi, v in zip(y, ap):
        ax1.text(v + 0.004, yi, f"{v:.3f}", va="center", fontsize=9, color=INK2)
    ax1.set_yticks(y); ax1.set_yticklabels(names, fontsize=9.5)
    ax1.axvline(mean_all, color=INK, linestyle="--", linewidth=1.3,
                label=f"mean over all 15 classes = {mean_all:.3f}")
    ax1.axvline(mean_5, color=BLUE, linestyle="-.", linewidth=1.3,
                label=f"mean over the 11 classes with n>=5 = {mean_5:.3f}")
    ax1.legend(loc="lower right", fontsize=9.5)
    ax1.set_xlim(0.78, 1.035)
    ax1.set_ylim(-0.9, len(pc) - 0.3)
    ax1.set_xlabel("AP@0.50 on held-out matches")
    ax1.set_title("A. Gold bars rest on fewer than five ground-truth boxes",
                  fontsize=11)
    grid(ax1, axis="x")

    cuts = [1, 2, 3, 5, 10]
    vals = [ap_all[n_all >= k].mean() for k in cuts]
    counts = [int((n_all >= k).sum()) for k in cuts]
    boxes = [int(n_all[n_all >= k].sum()) for k in cuts]
    xs = np.arange(len(cuts))
    ax2.bar(xs, vals, 0.55, color=[GOLD if k < 5 else MAROON for k in cuts])
    for xi, v in zip(xs, vals):
        ax2.text(xi, v + 0.0015, f"{v:.4f}", ha="center", fontsize=9.5, color=INK2)
    ax2.set_xticks(xs)
    ax2.set_xticklabels([f"n >= {k}\n{c} classes\n{bx} boxes"
                         for k, c, bx in zip(cuts, counts, boxes)], fontsize=9.5)
    ax2.set_ylim(0.84, 0.96)
    ax2.set_ylabel("mAP@0.50 over the retained classes")
    ax2.set_xlabel("Minimum ground-truth support required of a class")
    ax2.set_title("B. Four classes holding seven boxes move the headline\n"
                  f"by {(mean_all - mean_5) * 100:.1f} points", fontsize=11)
    grid(ax2)

    save(fig, "figure_10_per_class_and_support.png",
         "A class with a single test box scores either 1.000 or 0.000; the 95% "
         "Clopper-Pearson interval around a perfect one-box result runs from 0.025 "
         "to 1.000, so such a value carries almost no information.")


# ==========================================================================
# 12 — conditions of appearance
# ==========================================================================
def fig_conditions():
    if BD is None:
        print("  skipped conditions: breakdown_dump.json not present")
        return
    cam = BD["cuts"]["camera"]
    lig = BD["cuts"]["lighting"]
    mat = BD["cuts"]["match"]
    bins = BD["size_bins"]

    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.2),
                             gridspec_kw={"width_ratios": [1, 1, 1.15]})
    fig.suptitle("Where the detector is strong, and where it is not",
                 fontsize=14, fontweight="bold", y=1.0)

    def panel(ax, cut, keys, pretty, title):
        x = np.arange(len(keys))
        ax.bar(x - 0.19, [cut[k]["map50"] for k in keys], 0.38, color=MAROON,
               label="mAP@0.50")
        ax.bar(x + 0.19, [cut[k]["r"] for k in keys], 0.38, color=BLUE, alpha=0.8,
               label="recall at confidence 0.35")
        for i, k in enumerate(keys):
            ax.text(i - 0.19, cut[k]["map50"] + 0.015, f"{cut[k]['map50']:.3f}",
                    ha="center", fontsize=9, color=INK2)
            ax.text(i + 0.19, cut[k]["r"] + 0.015, f"{cut[k]['r']:.3f}",
                    ha="center", fontsize=9, color=INK2)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{pretty[k]}\n{cut[k]['n_images']} images\n"
                            f"{cut[k]['n_boxes']} boxes" for k in keys], fontsize=9.5)
        ax.set_ylim(0, 1.28)
        ax.set_title(title, fontsize=11)
        ax.legend(loc="upper left", fontsize=9)
        grid(ax)

    panel(axes[0], cam, [k for k in ("closeup", "medium", "wide") if k in cam],
          {"closeup": "Close-up", "medium": "Medium", "wide": "Wide"},
          "A. By camera distance")
    axes[0].set_ylabel("Held-out score")
    panel(axes[1], lig, [k for k in ("day", "floodlit") if k in lig],
          {"day": "Daylight", "floodlit": "Floodlit"}, "B. By lighting")

    ax = axes[2]
    lo = [b["lo"] for b in bins]
    labs = [f"{b['lo']}-{b['hi']}" if b["hi"] < 9999 else f"{b['lo']}+" for b in bins]
    rec = [b["recall"] for b in bins]
    cols = [MAROON if r >= 0.85 else GOLD if r >= 0.6 else BLUE for r in rec]
    x = np.arange(len(bins))
    ax.bar(x, rec, 0.6, color=cols)
    for i, b in enumerate(bins):
        ax.text(i, b["recall"] + 0.02, f"{b['recall']:.2f}", ha="center",
                fontsize=9.5, color=INK2)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{l}\nn={b['n']}" for l, b in zip(labs, bins)], fontsize=9)
    ax.set_xlabel("Ground-truth logo size, sqrt(area) in source pixels")
    ax.set_ylabel("Recall at confidence 0.35")
    ax.set_ylim(0, 1.28)
    ax.set_title("C. By how large the mark actually is", fontsize=11)
    grid(ax)

    matches = ", ".join(f"{k}: {v['map50']:.3f} ({v['n_boxes']} boxes)"
                        for k, v in sorted(mat.items()))
    save(fig, "figure_12_conditions.png",
         f"Per-match mAP@0.50 on the three held-out matches - {matches} - shows the "
         "aggregate is not carried by one easy match.")


# ==========================================================================
# 8 — training support does not predict held-out accuracy
# ==========================================================================
def fig_support_vs_ap():
    tr = DS["splits"]["train"]["per_class"]
    pc = [c for c in RF["per_class"] if c["ap50"] is not None]
    x = np.array([tr.get(c["name"], 0) for c in pc], float)
    y = np.array([c["ap50"] for c in pc])
    n = np.array([c["n"] for c in pc])

    from scipy.stats import pearsonr, spearmanr
    pr, pp = pearsonr(x, y)
    sr, sp = spearmanr(x, y)

    fig, ax = plt.subplots(figsize=(9.6, 6.0))
    # Label placement alternates above and below, in x order, so that the
    # crowded low-support cluster on the left stays readable.
    order = np.argsort(x)
    place = {int(i): (0, 13) if k % 2 == 0 else (0, -20)
             for k, i in enumerate(order)}
    for i, (xi, yi, ni, c) in enumerate(zip(x, y, n, pc)):
        col = GOLD if ni < 5 else MAROON
        ax.scatter(xi, yi, s=46 + ni * 5.5, color=col, alpha=0.9, zorder=3,
                   edgecolor="white", linewidth=1.1)
        if xi == x.min():                    # leftmost point: label outward
            ax.annotate(PRETTY.get(c["name"], c["name"]), (xi, yi),
                        textcoords="offset points", xytext=(-10, 0), ha="right",
                        va="center", fontsize=8.5, color=INK2)
        else:
            ax.annotate(PRETTY.get(c["name"], c["name"]), (xi, yi),
                        textcoords="offset points", xytext=place[i], ha="center",
                        fontsize=8.5, color=INK2)
    k, b = np.polyfit(x, y, 1)
    xs = np.linspace(0, x.max() * 1.08, 20)
    ax.plot(xs, k * xs + b, color=MUTED, linestyle="--", linewidth=1.4, zorder=2)
    ax.set_xlabel("Training boxes for that sponsor class")
    ax.set_ylabel("AP@0.50 on held-out matches")
    ax.set_title("More examples of the same sponsor did not buy accuracy",
                 fontsize=13)
    ax.text(0.98, 0.06,
            f"Pearson r = {pr:.3f} (p = {pp:.2f})\n"
            f"Spearman rho = {sr:.3f} (p = {sp:.2f})\n"
            f"r² = {pr ** 2:.3f}",
            transform=ax.transAxes, ha="right", fontsize=10, color=INK)
    ax.set_ylim(0.79, 1.045)
    grid(ax)

    save(fig, "figure_08_support_vs_ap.png",
         "Marker size is held-out support. The relationship is statistically "
         "indistinguishable from none, which is why collection effort went to new "
         "matches rather than to more frames of the matches already held.")


# ==========================================================================
# carried-over plates
# ==========================================================================
CARRY = {
    "carry_01_research_framework.png": "figure_01_research_framework.png",
    "carry_02_technical_workflow.png": "figure_02_technical_workflow.png",
    "carry_03_split_and_leakage.png": "figure_03_split_and_leakage.png",
    "carry_04_system_architecture.png": "figure_04_system_architecture.png",
    "carry_05_visibility_aggregation.png": "figure_05_visibility_aggregation.png",
    "carry_06_optimisation_and_resolution.png": "figure_07_optimisation_and_resolution.png",
    "carry_08_detection_evidence.png": "figure_13_detection_evidence.png",
}


def stage_media():
    for src, dst in CARRY.items():
        p = DATA / src
        if p.exists():
            shutil.copyfile(p, MEDIA / dst)
            print(f"  copied {dst}")


FIGURES = {
    "geometry": fig_input_geometry,
    "architecture": fig_architecture,
    "confidence": fig_confidence,
    "perclass": fig_per_class,
    "conditions": fig_conditions,
    "support": fig_support_vs_ap,
}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(FIGURES)
    stage_media()
    for name in wanted:
        print(name)
        FIGURES[name]()
