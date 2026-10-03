"""Regenerate every figure the dissertation draws for itself.

Run:  python make_figures.py            (all figures)
      python make_figures.py class_dist  (one figure, by name)

Figures produced by the training frameworks themselves - the confusion matrix,
the precision-recall curves, the label analysis and the qualitative detection
sample - are authentic tool output and are deliberately NOT redrawn here.

Every number below is either read from a logged run under logo_detection/runs
and training-result/, or is a measurement already reported in the text; none is
invented for the sake of the picture.
"""
from __future__ import annotations

import csv
import json
import re
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch

from figstyle import (AQUA, AXIS, BLUE, FILL_MUTED, GRID, INK, INK2, MUTED,
                      ORANGE, RAMP, SURFACE, arrow, blank, chrome, node, note,
                      save, use_style)

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
FIG = ROOT / "figures"
RUNS = REPO / "logo_detection" / "runs"
RFDETR = REPO / "training-result"

FIG.mkdir(exist_ok=True)


# ==========================================================================
# Data loaded from logged runs
# ==========================================================================

BRAND_ORDER = ['acs_group', 'aon', 'atm', 'bartercard', 'cch', 'chadlaw',
               'ellgren', 'em_workwear', 'fairway', 'floor_tonic', 'klg',
               'mcp', 'mna_cladding', 'mna_support_service',
               'paints_lacquers', 'romantica', 'top_notch']


def rfdetr_best_row():
    rows = list(csv.DictReader(open(RFDETR / "metrics.csv", encoding="utf-8")))
    best, best_map = None, -1.0
    for r in rows:
        v = r.get("val/mAP_50", "")
        if v and float(v) > best_map:
            best_map, best = float(v), r
    return rows, best


def frame_profile():
    """Per-frame logo counts and per-instance geometry, from the annotations.

    Returns (logos_per_frame, brands_per_frame, area_pct_of_frame, height_px).
    """
    per_img, brands, areas, heights = [], [], [], []
    for split in ["train", "valid", "test"]:
        jp = RFDETR / "data" / split / "_annotations.coco.json"
        j = json.loads(jp.read_text(encoding="utf-8"))
        cats = {c["id"]: c["name"] for c in j["categories"]}
        size = {im["id"]: (im["width"], im["height"]) for im in j["images"]}
        by = defaultdict(list)
        for a in j["annotations"]:
            by[a["image_id"]].append(a)
        for iid, (w, h) in size.items():
            anns = by.get(iid, [])
            per_img.append(len(anns))
            brands.append(len({cats[a["category_id"]].rsplit("_", 1)[0] for a in anns}))
            for a in anns:
                bw, bh = a["bbox"][2], a["bbox"][3]
                areas.append(bw * bh / (w * h) * 100)
                heights.append(bh)
    return (np.array(per_img), np.array(brands),
            np.array(areas), np.array(heights))


def class_counts():
    """Reproduce the clip-aware split built in train_colab_rfdetr.ipynb, so
    per-class instance counts pair exactly with the per-class AP logged for
    that run. Returns (train_counts, val_counts) keyed by brand."""
    idx = {b: i for i, b in enumerate(BRAND_ORDER)}

    def brand_of(name):
        return re.sub(r"_(home|away)$", "", name)

    def group_key(stem):
        m = re.match(r"^(M\d+)", stem) or re.match(r"^(clip_\d+)", stem)
        return m.group(1) if m else stem

    all_imgs = []
    for jp in sorted((RFDETR / "data").glob("*/_annotations.coco.json")):
        j = json.loads(jp.read_text(encoding="utf-8"))
        cat = {c["id"]: idx.get(brand_of(c["name"])) for c in j["categories"]}
        anns = defaultdict(list)
        for a in j["annotations"]:
            b = cat.get(a["category_id"])
            if b is not None:
                anns[a["image_id"]].append(b)
        for im in j["images"]:
            all_imgs.append((im["file_name"], anns.get(im["id"], [])))

    groups = defaultdict(lambda: {"n": 0, "c": Counter()})
    for fn, bs in all_imgs:
        g = groups[group_key(Path(fn).stem)]
        g["n"] += 1
        g["c"].update(bs)
    keys, total = sorted(groups), len(all_imgs)
    totals = Counter()
    for g in groups.values():
        totals.update(g["c"])

    def one(seed):
        order = list(keys)
        random.Random(seed).shuffle(order)
        val, n = set(), 0
        for k in order:
            if n >= 0.18 * total:
                break
            val.add(k)
            n += groups[k]["n"]
        return val

    def score(vs):
        tr = Counter()
        for k, g in groups.items():
            if k not in vs:
                tr.update(g["c"])
        bad = sum(1 for c in totals if tr[c] < 0.6 * totals[c])
        nval = sum(groups[k]["n"] for k in vs)
        return (bad, abs(nval / total - 0.18))

    best = min((one(s) for s in range(300)), key=score)
    tr, va = Counter(), Counter()
    for k, g in groups.items():
        (va if k in best else tr).update(g["c"])
    return ({b: tr[idx[b]] for b in BRAND_ORDER},
            {b: va[idx[b]] for b in BRAND_ORDER})


# ==========================================================================
# Chapter 3 - method diagrams
# ==========================================================================

def frameselect():
    """Figure 1 - the eight-step high-value frame selection procedure."""
    fig, ax = blank((7.4, 3.5))
    steps = [
        ("1  Adaptive\nsampling", "~2 fps to 1 / 3 s"),
        ("2  Static-overlay\nmask", "temporal std. dev."),
        ("3  Shot-type\ngate", "green-pixel ratio"),
        ("4  Person\ndetection", "≥ 2 large boxes"),
        ("5  Target-colour\nfilter", "HSV kit match"),
        ("6  Torso sharpness\nscore", "weighted Laplacian"),
        ("7  De-duplication", "temporal NMS + pHash"),
        ("8  Export", "full resolution"),
    ]
    xs = np.linspace(0.075, 0.925, 4)
    nodes = []
    for i, (title, sub) in enumerate(steps):
        row, col = divmod(i, 4)
        x = xs[col] if row == 0 else xs[3 - col]
        y = 0.70 if row == 0 else 0.29
        nodes.append(node(ax, x, y, title, face=BLUE, size=8, weight="bold"))
        # Row 1 annotates above and row 2 below, which keeps the vertical
        # connector between the rows clear of any text.
        dy, va = (0.16, "bottom") if row == 0 else (-0.16, "top")
        ax.text(x, y + dy, sub, ha="center", va=va, fontsize=7.2, color=MUTED)

    for i in range(7):
        if i == 3:
            continue
        arrow(fig, ax, nodes[i], nodes[i + 1], side="h")
    ax.annotate("", xy=(xs[3], 0.42), xytext=(xs[3], 0.58), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.2))

    ax.text(0.5, 0.03, "~100,000 frames per match  →  ~200 high-value frames for annotation",
            ha="center", va="center", fontsize=8.5, color=INK2, style="italic")
    ax.set_ylim(-0.02, 0.94)
    save(fig, FIG / "fig_frameselect.png")


def labelassist():
    """Figure 3 - the model-assisted annotation loop."""
    fig, ax = blank((7.0, 3.3))
    seed = node(ax, 0.16, 0.78, "Seed set\n50-80 frames\nannotated by hand", face=ORANGE, size=8)
    train = node(ax, 0.50, 0.78, "Train assisting\ndetector", face=BLUE, size=8)
    assist = node(ax, 0.84, 0.78, "Label Assist\npre-labels new frames", face=BLUE, size=8)
    correct = node(ax, 0.84, 0.30, "Annotator accepts,\ncorrects or adds", face=BLUE, size=8)
    pool = node(ax, 0.34, 0.30, "Corrected frames\njoin the training pool", face=AQUA, size=8)

    arrow(fig, ax, seed, train, side="h")
    arrow(fig, ax, train, assist, side="h")
    arrow(fig, ax, assist, correct)
    arrow(fig, ax, correct, pool, side="h")
    ax.annotate("", xy=(0.50, 0.66), xytext=(0.34, 0.42), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.2,
                                connectionstyle="arc3,rad=0.25"))
    ax.text(0.545, 0.54, "each pass improves\nthe suggestions", ha="left", va="center",
            fontsize=7.4, color=MUTED, style="italic")
    ax.text(0.5, 0.045, "5-10× faster than drawing every box from scratch",
            ha="center", va="center", fontsize=8.5, color=INK2, style="italic")
    ax.set_ylim(0.0, 0.95)
    save(fig, FIG / "fig_labelassist.png")


# ==========================================================================
# Chapter 4 - system diagrams
# ==========================================================================

def system_arch():
    """Figure 5 - static structure of the system."""
    fig, ax = blank((7.2, 4.2))
    ax.add_patch(FancyBboxPatch((0.03, 0.06), 0.40, 0.76, boxstyle="round,pad=0.012,rounding_size=0.02",
                                facecolor="#f5f7fa", edgecolor=GRID, linewidth=0.9, zorder=0))
    ax.add_patch(FancyBboxPatch((0.53, 0.06), 0.44, 0.76, boxstyle="round,pad=0.012,rounding_size=0.02",
                                facecolor="#f5f7fa", edgecolor=GRID, linewidth=0.9, zorder=0))
    ax.text(0.23, 0.86, "FRONTEND  ·  Next.js dashboard", ha="center", fontsize=8.5,
            color=INK2, weight="bold")
    ax.text(0.75, 0.86, "BACKEND  ·  FastAPI service", ha="center", fontsize=8.5,
            color=INK2, weight="bold")

    up = node(ax, 0.23, 0.72, "Upload &\njob submission", face=BLUE, size=8)
    views = node(ax, 0.23, 0.46, "Overview  ·  Match view\nReport  ·  3D kit model", face=BLUE, size=8)
    api = node(ax, 0.75, 0.59, "HTTP API\ncreate · poll · fetch", face=ORANGE, size=8)
    orch = node(ax, 0.75, 0.38, "Pipeline orchestrator", face=BLUE, size=8, weight="bold")

    infra = [("Database", 0.60), ("File storage", 0.75), ("Job queue", 0.90)]
    boxes = []
    for label, x in infra:
        boxes.append(node(ax, x, 0.22, label, face="#eef1f5", fg=INK2, size=7.6, pad=0.4))
    zoo = node(ax, 0.75, 0.115, "Model zoo   detector · tracker · pose · segmentation",
               face="#eef1f5", fg=INK2, size=7.6, pad=0.4)

    # Request and response leave the API box at different heights, so the two
    # arrows share no corridor.
    for (x0, y0), (x1, y1) in [((0.325, 0.70), (0.655, 0.625)),
                               ((0.655, 0.555), (0.375, 0.475))]:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=2,
                    arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.2))
    arrow(fig, ax, api, orch)
    for b in boxes:
        arrow(fig, ax, orch, b)
    arrow(fig, ax, orch, zoo)
    ax.text(0.49, 0.685, "jobs", ha="center", va="bottom", fontsize=7.2, color=MUTED)
    ax.text(0.51, 0.495, "results", ha="center", va="bottom", fontsize=7.2, color=MUTED)
    ax.text(0.5, 0.025, "every infrastructure dependency sits behind an interface and is swappable by configuration",
            ha="center", va="center", fontsize=7.6, color=MUTED, style="italic")
    ax.set_ylim(0.0, 0.92)
    save(fig, FIG / "fig_system_arch.png")


def pipeline():
    """Figure 6 - what happens when a video is uploaded."""
    fig, ax = blank((7.4, 3.8))
    stages = ["1 frames", "2 team", "3 detect", "4 exposure",
              "5 pricing", "6 preview", "7 bodyseg", "8 done"]
    xs = np.linspace(0.075, 0.925, 8)
    tops = []
    for x, s in zip(xs, stages):
        face = ORANGE if s.endswith("detect") else BLUE
        tops.append(node(ax, x, 0.80, s.replace(" ", "\n", 1), face=face, size=7.8, pad=0.45))
    for a, b in zip(tops, tops[1:]):
        arrow(fig, ax, a, b, side="h", lw=1.0)
    ax.text(0.5, 0.955, "job progress →", ha="center", fontsize=7.4, color=MUTED)

    sub = ["Logo detection", "Visibility scoring", "Team attribution", "Slot assignment"]
    sxs = np.linspace(0.16, 0.84, 4)
    subs = [node(ax, x, 0.30, t, face="#eef1f5", fg=INK2, size=8, pad=0.45) for x, t in zip(sxs, sub)]
    for a, b in zip(subs, subs[1:]):
        arrow(fig, ax, a, b, side="h", lw=1.0)
    for target in (sxs[0], sxs[-1]):
        ax.annotate("", xy=(target, 0.40), xytext=(xs[2], 0.70), zorder=1,
                    arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.9,
                                    linestyle=(0, (3, 3))))
    ax.text(0.5, 0.475, "expands, per sampled frame (2 fps), into", ha="center",
            fontsize=7.4, color=MUTED, style="italic",
            bbox=dict(boxstyle="square,pad=0.25", facecolor=SURFACE, edgecolor="none"))
    ax.text(0.5, 0.13, "optional stages degrade gracefully: a failure is logged and the job returns a partial result",
            ha="center", va="center", fontsize=7.6, color=MUTED, style="italic")
    ax.set_ylim(0.06, 1.0)
    save(fig, FIG / "fig_pipeline.png")


def three_tier():
    """Figure 8 - the three-tier valuation model."""
    fig, ax = blank((6.8, 3.2))
    rows = [
        (0.78, "Tier 1  ·  Visibility, per detection",
         "size  ×  position  ×  clarity  ×  oriented-box correction", RAMP[0], INK),
        (0.50, "Tier 2  ·  Exposure, per brand over time",
         "Σ  duration  ×  mean visibility  ×  duration weight", RAMP[2], "white"),
        (0.22, "Tier 3  ·  Estimated media value",
         "exposure / 30  ×  CPM / 1000  ×  audience  ×  scenario", RAMP[4], "white"),
    ]
    ns = []
    for y, title, formula, face, fg in rows:
        ns.append(node(ax, 0.5, y, f"{title}\n{formula}", face=face, fg=fg, size=8.5, pad=0.8))
    arrow(fig, ax, ns[0], ns[1])
    arrow(fig, ax, ns[1], ns[2])
    for y, lab in [(0.64, "adds temporal and recall structure"),
                   (0.36, "adds broadcast and competitive context")]:
        ax.text(0.53, y, lab, ha="left", va="center", fontsize=7.6, color=MUTED, style="italic")
    ax.text(0.5, 0.045, "raw detections → spatial quality → temporal structure → monetary estimate",
            ha="center", va="center", fontsize=8, color=INK2, style="italic")
    ax.set_ylim(0.0, 0.94)
    save(fig, FIG / "fig_three_tier.png")


# ==========================================================================
# Chapter 5 - results
# ==========================================================================

def class_dist():
    """Figure 12 - per-class instance counts in the training split."""
    tr, _ = class_counts()
    items = sorted(tr.items(), key=lambda kv: kv[1])
    names = [k.replace("_", " ") for k, _ in items]
    vals = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    y = np.arange(len(vals))
    ax.barh(y, vals, height=0.66, color=BLUE, zorder=2)
    ax.set_yticks(y, names)
    ax.set_xlabel("annotated instances in the training split")
    ax.set_xlim(0, max(vals) * 1.12)
    for yi, v in zip(y, vals):
        ax.text(v + max(vals) * 0.012, yi, f"{v:,}", va="center", fontsize=7.8, color=INK2)
    chrome(ax, axis="x")
    note(ax, max(vals) * 0.99, 3.4,
         f"{len(vals)} classes · {sum(vals):,} instances\n"
         f"imbalance {max(vals) / min(vals):.1f}×  ({names[-1]} : {names[0]})",
         color=INK2, size=8.2, ha="right", va="center")
    save(fig, FIG / "fig_class_dist.png")


# Frame stems, chosen for being wide enough that no individual is identifiable.
# The export appends a random suffix, so these are matched as prefixes.
SELECTED_FRAMES = [
    "clip_032_08-10_0000150_t00005000ms",
    "clip_030_07-57_0000060_t00002000ms",
    "clip_038_10-01_0000120_t00004000ms",
    "clip_036_09-39_0000120_t00004000ms",
    "clip_030_07-57_0000210_t00007000ms",
    "clip_024_05-55_0000090_t00003000ms",
]


def selected_frames():
    """Examples of the frames the selection procedure keeps for annotation.

    Deliberately wide shots, in which no individual is identifiable, and with
    the broadcast watermark and the score/clock graphic blurred out, following
    the same figure policy applied to the qualitative detection output.
    """
    from PIL import Image, ImageFilter

    found = []
    for stem in SELECTED_FRAMES:
        hits = [p for split in ("train", "valid", "test")
                for p in (RFDETR / "data" / split).glob(stem + "*")]
        if not hits:
            raise SystemExit(f"frame not found: {stem}")
        found.append(hits[0])

    def redact(im):
        w, h = im.size
        # Broadcast watermark, top right; score and clock graphic, bottom left.
        for box in [(int(w * 0.74), 0, w, int(h * 0.12)),
                    (0, int(h * 0.84), int(w * 0.44), h)]:
            region = im.crop(box).filter(ImageFilter.GaussianBlur(14))
            im.paste(region, box[:2])
        return im

    tiles = []
    for p in found:
        with Image.open(p) as im:
            tiles.append(redact(im.convert("RGB").copy()))

    tw = 640
    tiles = [t.resize((tw, int(t.height * tw / t.width)), Image.LANCZOS) for t in tiles]
    th = max(t.height for t in tiles)
    gap = 8
    sheet = Image.new("RGB", (tw * 3 + gap * 2, th * 2 + gap), SURFACE)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * (tw + gap), (i // 3) * (th + gap)))
    sheet.save(FIG / "fig_selected_frames.png", quality=90)
    print(f"  wrote fig_selected_frames.png  ({sheet.width}x{sheet.height})")


def roboflow():
    """The Roboflow annotation interface with Label Assist enabled.

    Screenshot supplied by the author. The broadcast watermark and the caption
    naming the match officials are blurred, following the figure policy: the
    predicted boxes and the Label Assist controls are the object of study, an
    individual's name is not.
    """
    from PIL import Image, ImageFilter

    src = FIG / "_source" / "roboflow_raw.jpg"
    im = Image.open(src).convert("RGB")
    w, h = im.size
    # Fractions of the frame, so the boxes survive a change of source resolution.
    for fx0, fy0, fx1, fy1 in [(0.70, 0.13, 0.90, 0.24),   # BullsTV watermark
                               (0.13, 0.76, 0.79, 0.91)]:  # officials' name caption
        box = (int(w * fx0), int(h * fy0), int(w * fx1), int(h * fy1))
        im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(16)), box[:2])
    im.save(FIG / "fig_roboflow.png", quality=92)
    print(f"  wrote fig_roboflow.png  ({im.width}x{im.height})")


def kit_reference():
    """The club's official home and away kit renders, side by side.

    These are the reference images the attribution stage bootstraps from, and
    they double as a map of where each sponsor sits on the strip. The squad
    surname printed on the back view is redacted, in line with the figure
    policy of Section 3.6: the sponsor marks are the object of study, an
    individual's name is not.
    """
    from PIL import Image, ImageDraw

    KIT = REPO / "KIT"
    # Measured on the 3508x2481 renders; the two views differ only in y.
    NAME_BOX = {"Home Kit.jpg": (2380, 605, 2945, 705),
                "Away Kit.jpg": (2380, 660, 2945, 760)}

    panels = []
    for name in ("Home Kit.jpg", "Away Kit.jpg"):
        im = Image.open(KIT / name).convert("RGB")
        x0, y0, x1, y1 = NAME_BOX[name]
        # Fill with the shirt colour sampled just above the lettering, so the
        # redaction reads as blank fabric rather than as a black bar.
        patch = im.crop((x0, y0 - 60, x1, y0 - 30)).resize((1, 1), Image.BOX)
        ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], fill=patch.getpixel((0, 0)))
        panels.append(im)

    w = 1500
    scaled = [p.resize((w, int(p.height * w / p.width)), Image.LANCZOS) for p in panels]
    gap = 16
    sheet = Image.new("RGB", (w * 2 + gap, max(p.height for p in scaled)), SURFACE)
    sheet.paste(scaled[0], (0, 0))
    sheet.paste(scaled[1], (w + gap, 0))
    sheet.save(FIG / "fig_kit_reference.png", quality=92)
    print(f"  wrote fig_kit_reference.png  ({sheet.width}x{sheet.height})")


def content_profile():
    """What a broadcast frame actually contains: how many logos, how much of
    the screen they occupy, and at what resolution they are rendered."""
    per_img, brands, areas, heights = frame_profile()

    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.9))

    # (a) logos per frame
    ax = axes[0]
    capped = np.clip(per_img, 0, 10)
    counts = [np.sum(capped == k) for k in range(11)]
    x = np.arange(11)
    colors = [FILL_MUTED] + [BLUE] * 10
    ax.bar(x, counts, width=0.78, color=colors, zorder=2)
    ax.set_xticks([0, 2, 4, 6, 8, 10], ["0", "2", "4", "6", "8", "10+"])
    ax.set_xlabel("sponsor logos in the frame")
    ax.set_ylabel("frames")
    note(ax, 10.4, max(counts) * 0.92,
         f"{(per_img >= 2).mean() * 100:.0f}% of frames\ncarry two or more",
         color=INK2, size=8, ha="right", va="top")
    chrome(ax)

    # (b) screen coverage per logo
    ax = axes[1]
    bins = np.logspace(np.log10(0.01), np.log10(15), 34)
    ax.hist(areas, bins=bins, color=BLUE, zorder=2)
    ax.set_xscale("log")
    ax.set_xticks([0.01, 0.1, 1, 10], ["0.01", "0.1", "1", "10"])
    ax.set_xlabel("share of frame area (%, log scale)")
    ax.set_ylabel("logo instances")
    med = np.median(areas)
    ax.axvline(med, color=MUTED, linewidth=0.9, zorder=3)
    note(ax, 13, ax.get_ylim()[1] * 0.95,
         f"median {med:.2f}%\n{(areas < 1).mean() * 100:.0f}% under 1%",
         color=INK2, size=8, va="top", ha="right")
    chrome(ax)

    # (c) rendered resolution of the mark
    ax = axes[2]
    CAP = 160
    ax.hist(np.clip(heights, 0, CAP), bins=32, color=BLUE, zorder=2)
    ax.set_xlabel("mark height in the frame (pixels)")
    ax.set_ylabel("logo instances")
    ax.set_xticks([0, 50, 100, 150], ["0", "50", "100", "150+"])
    med = np.median(heights)
    ax.axvline(med, color=MUTED, linewidth=0.9, zorder=3)
    note(ax, CAP * 0.99, ax.get_ylim()[1] * 0.95,
         f"median {med:.0f} px\n{(heights < 32).mean() * 100:.0f}% under 32 px",
         color=INK2, size=8, va="top", ha="right")
    chrome(ax)

    fig.tight_layout()
    save(fig, FIG / "fig_content_profile.png")


def split_protocol():
    """Figure 14 - the effect of the evaluation protocol."""
    labels = ["Random-frame\n(leakage)", "Clip-disjoint", "Extended clip-aware\n(headline)"]
    vals = [0.862, 0.702, 0.745]
    # Emphasis, not a value ramp: the reported result carries the hue and the
    # two comparison bars recede.
    colors = [FILL_MUTED, FILL_MUTED, BLUE]

    fig, ax = plt.subplots(figsize=(5.8, 3.3))
    x = np.arange(3)
    ax.bar(x, vals, width=0.5, color=colors, zorder=2)
    ax.set_xticks(x, labels)
    ax.set_ylabel("mAP@0.5")
    ax.set_ylim(0, 1.14)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.022, f"{v:.3f}", ha="center", fontsize=9.5, color=INK, weight="bold")
    chrome(ax)
    # The like-for-like leakage measurement is random against clip-disjoint on
    # the same data; the extended set is a larger collection and is not part of
    # that comparison.
    ax.annotate("", xy=(1, 1.005), xytext=(0, 1.005), zorder=3,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.0))
    ax.text(0.5, 1.03, "leakage inflates mAP by 0.160", ha="center", fontsize=8.2, color=INK2)
    save(fig, FIG / "fig_split_protocol.png")


def training_curves():
    """Figure 15 - training dynamics of the clip-disjoint run."""
    rows = list(csv.DictReader(open(RUNS / "logo_yolo26m_clipsplit" / "results.csv", encoding="utf-8")))
    ep = [float(r["epoch"]) for r in rows]

    def col(name):
        return [float(r[name]) for r in rows]

    def smooth(v, w=9):
        return np.convolve(v, np.ones(w) / w, mode="valid")

    def draw(ax, series, label, c):
        v = col(series)
        ax.plot(ep, v, color=c, linewidth=0.8, alpha=0.22, zorder=2)
        s = smooth(v)
        ax.plot(ep[len(ep) - len(s):], s, color=c, label=label, zorder=3)

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0))
    a = axes[0]
    for name, label, c in [("metrics/mAP50(B)", "mAP@0.5", BLUE),
                           ("metrics/precision(B)", "precision", ORANGE),
                           ("metrics/recall(B)", "recall", AQUA)]:
        draw(a, name, label, c)
    best = max(col("metrics/mAP50(B)"))
    a.axhline(best, color=MUTED, linewidth=0.8, zorder=1)
    note(a, 3, best + 0.05, f"best mAP@0.5 = {best:.3f}", size=8)
    a.set_xlabel("epoch")
    a.set_ylabel("validation metric")
    a.set_ylim(0, 1.0)
    a.legend(loc="lower right")
    chrome(a)

    b = axes[1]
    draw(b, "train/box_loss", "train box loss", BLUE)
    draw(b, "val/box_loss", "validation box loss", ORANGE)
    b.set_xlabel("epoch")
    b.set_ylabel("box loss")
    b.legend(loc="upper right")
    note(b, 92, 0.95, "the validation loss plateaus\nrather than rising", size=8, color=INK2)
    chrome(b)
    fig.tight_layout()
    save(fig, FIG / "fig_training_curves.png")


def rfdetr_perclass():
    """Figure 19 - RF-DETR per-class AP at the best checkpoint."""
    _, best = rfdetr_best_row()
    ap = {b: float(best[f"val/AP/{b}"]) for b in BRAND_ORDER}
    items = sorted(ap.items(), key=lambda kv: kv[1])
    names = [k.replace("_", " ") for k, _ in items]
    vals = [v for _, v in items]
    mean = float(best["val/mAP_50_95"])

    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    y = np.arange(len(vals))
    ax.barh(y, vals, height=0.66, color=BLUE, zorder=2)
    ax.set_yticks(y, names)
    ax.set_xlabel("AP@[.5:.95]")
    ax.set_xlim(0, max(vals) * 1.18)
    for yi, v in zip(y, vals):
        ax.text(v + 0.008, yi, f"{v:.3f}", va="center", fontsize=7.8, color=INK2)
    ax.axvline(mean, color=MUTED, linewidth=0.9, zorder=3, ymin=0.03)
    note(ax, mean, -0.95, f"mean {mean:.3f}", size=8, ha="center")
    ax.set_ylim(-1.35, len(vals) - 0.4)
    chrome(ax, axis="x")
    save(fig, FIG / "fig_rfdetr_perclass.png")


def rfdetr_curve():
    """Figure 20 - RF-DETR validation mAP over training."""
    rows, best = rfdetr_best_row()
    ep, m50, m5095 = [], [], []
    for r in rows:
        if r.get("val/mAP_50", ""):
            ep.append(float(r["epoch"]))
            m50.append(float(r["val/mAP_50"]))
            m5095.append(float(r["val/mAP_50_95"]))

    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    ax.plot(ep, m50, color=BLUE, label="mAP@0.5")
    ax.plot(ep, m5095, color=ORANGE, label="mAP@[.5:.95]")
    be = float(best["epoch"])
    bv = float(best["val/mAP_50"])
    ax.plot([be], [bv], marker="o", color=BLUE, markersize=6,
            markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
    ax.annotate(f"best checkpoint\nepoch {be:.0f}, {bv:.3f}", xy=(be, bv),
                xytext=(be + 4, 0.90), fontsize=8, color=MUTED, va="top",
                arrowprops=dict(arrowstyle="-", color=AXIS, linewidth=0.9,
                                shrinkA=0, shrinkB=4))
    ax.set_xlabel("epoch")
    ax.set_ylabel("validation mAP")
    ax.set_ylim(0, 0.95)
    ax.legend(loc="lower right")
    chrome(ax)
    save(fig, FIG / "fig_rfdetr_curve.png")


def data_efficiency():
    """NEW - Figure for RQ3: labelled data per class against per-class AP."""
    tr, va = class_counts()
    _, best = rfdetr_best_row()
    ap = {b: float(best[f"val/AP/{b}"]) for b in BRAND_ORDER}

    n = np.array([tr[b] for b in BRAND_ORDER], float)
    a = np.array([ap[b] for b in BRAND_ORDER], float)
    x = np.log10(n)
    slope, intercept = np.polyfit(x, a, 1)
    r = np.corrcoef(x, a)[0, 1]

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4), sharey=True,
                             gridspec_kw={"width_ratios": [1.7, 1]})

    # (a) AP against training instances, log x
    ax = axes[0]
    xs = np.linspace(x.min() - 0.06, x.max() + 0.06, 100)
    ax.plot(10 ** xs, intercept + slope * xs, color=MUTED, linewidth=1.2, zorder=2)
    ax.scatter(n, a, s=34, color=BLUE, zorder=3, edgecolor=SURFACE, linewidth=1.4)
    ax.set_xscale("log")
    ax.set_xlabel("annotated training instances per class (log scale)")
    ax.set_ylabel("AP@[.5:.95]")
    ax.set_ylim(0.26, 0.70)
    ax.set_xlim(150, 2400)
    ax.set_xticks([200, 500, 1000, 2000], ["200", "500", "1,000", "2,000"])
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.tick_params(axis="x", which="minor", length=2)
    for label, dx, dy, ha in [("klg", -7, 5, "right"), ("mcp", -7, 4, "right"),
                              ("fairway", 8, -1, "left"), ("cch", 8, 1, "left")]:
        i = BRAND_ORDER.index(label)
        ax.annotate(label, (n[i], a[i]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=7.6, color=MUTED, ha=ha, va="center")
    note(ax, 2300, 0.315, f"r = {r:+.2f}    R² = {r * r:.2f}\n+{slope:.3f} AP per 10× of data",
         color=INK2, size=8.2, va="top", ha="right")
    chrome(ax)

    # (b) the practical consequence, as a dot plot so it can share the y axis
    ax = axes[1]
    thr = 500
    groups = [(a[n < thr], f"< {thr}", FILL_MUTED), (a[n >= thr], f"≥ {thr}", BLUE)]
    for xi, (grp, lab, c) in enumerate(groups):
        jitter = np.linspace(-0.13, 0.13, len(grp))
        ax.scatter(np.full(len(grp), xi) + jitter, grp, s=26, color=BLUE,
                   alpha=0.5, zorder=3, edgecolor=SURFACE, linewidth=1.0)
        ax.plot([xi - 0.26, xi + 0.26], [grp.mean()] * 2, color=INK, linewidth=2.0, zorder=4)
        ax.text(xi, grp.mean() + 0.022, f"{grp.mean():.3f}", ha="center",
                fontsize=9, color=INK, weight="bold", zorder=5)
    ax.set_xticks([0, 1], [f"< {thr}\n({(n < thr).sum()} classes)",
                           f"≥ {thr}\n({(n >= thr).sum()} classes)"])
    ax.set_xlim(-0.55, 1.55)
    ax.set_xlabel("training instances per class")
    note(ax, 0.5, 0.685, "+0.084 mean AP\n(Welch p = 0.009)", color=INK2, size=8,
         ha="center", va="top")
    chrome(ax)
    ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    save(fig, FIG / "fig_data_efficiency.png")


def occlusion():
    """Figure for the occlusion audit: what drives it, and what it does not explain."""
    AUD = ROOT / "occlusion_audit"
    rows = {int(r["id"]): r for r in csv.DictReader(
        open(AUD / "sample.csv", encoding="utf-8"))}
    lab = {int(r["id"]): int(r["occlusion"]) for r in csv.DictReader(
        open(AUD / "labels.csv", encoding="utf-8"))}
    ids = sorted(lab)
    lv = np.array([lab[i] for i in ids])
    h = np.array([float(rows[i]["height_px"]) for i in ids])
    occ = lv >= 1

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2),
                             gridspec_kw={"width_ratios": [1, 1.15]})

    # (a) occlusion rate by rendered size
    ax = axes[0]
    bands = [(0, 32, "<32"), (32, 48, "32-48"), (48, 72, "48-72"), (72, 1e9, "72+")]
    rates, labels, ns = [], [], []
    for lo, hi, name in bands:
        m = (h >= lo) & (h < hi)
        rates.append(occ[m].mean() * 100)
        labels.append(name)
        ns.append(int(m.sum()))
    x = np.arange(len(bands))
    ax.bar(x, rates, width=0.6, color=BLUE, zorder=2)
    for xi, v in zip(x, rates):
        ax.text(xi, v + 1.6, f"{v:.0f}%", ha="center", fontsize=9, color=INK, weight="bold")
    ax.axhline(occ.mean() * 100, color=MUTED, linewidth=0.9, zorder=3)
    note(ax, -0.45, occ.mean() * 100 + 3.0, f"overall {occ.mean()*100:.0f}%",
         size=8, ha="left")
    ax.set_xticks(x, [f"{lab}\nn={n}" for lab, n in zip(labels, ns)])
    ax.set_xlabel("mark height in the frame (pixels)")
    ax.set_ylabel("logos partly or heavily covered (%)")
    ax.set_ylim(0, 68)
    chrome(ax)

    # (b) per-class occlusion against the data-efficiency residual
    ax = axes[1]
    occ_cls = {r["brand"]: float(r["occluded_rate"]) * 100 for r in csv.DictReader(
        open(AUD / "occlusion_by_class.csv", encoding="utf-8"))}
    tr, _ = class_counts()
    _, best = rfdetr_best_row()
    ap = np.array([float(best[f"val/AP/{b}"]) for b in BRAND_ORDER])
    n_tr = np.array([tr[b] for b in BRAND_ORDER], float)
    slope, intercept = np.polyfit(np.log10(n_tr), ap, 1)
    resid = ap - (intercept + slope * np.log10(n_tr))
    rate = np.array([occ_cls[b] for b in BRAND_ORDER])

    ax.axhline(0, color=AXIS, linewidth=0.9, zorder=1)
    ax.scatter(rate, resid, s=34, color=BLUE, zorder=3,
               edgecolor=SURFACE, linewidth=1.4)
    fit = np.polyfit(rate, resid, 1)
    xs = np.linspace(-4, 84, 50)
    ax.plot(xs, np.polyval(fit, xs), color=MUTED, linewidth=1.2, zorder=2)
    r = np.corrcoef(rate, resid)[0, 1]
    for label, dx, dy, ha in [("fairway", 6, 0, "left"), ("floor_tonic", -7, 6, "right")]:
        i = BRAND_ORDER.index(label)
        ax.annotate(label, (rate[i], resid[i]), textcoords="offset points",
                    xytext=(dx, dy), fontsize=7.6, color=MUTED, ha=ha, va="center")
    ax.set_xlabel("logos covered, per class (%)")
    ax.set_ylabel("accuracy above/below the\ndata-efficiency fit (AP)")
    ax.set_xlim(-6, 86)
    note(ax, 84, -0.075, f"r = {r:+.2f}  (p = 0.45)\nno association",
         color=INK2, size=8.2, ha="right", va="center")
    chrome(ax)
    fig.tight_layout()
    save(fig, FIG / "fig_occlusion.png")


def audit():
    """Figure 21 - the stratified manual audit of team attribution."""
    groups = [("Overall", 91.8), ("Target team", 90.7), ("Other", 92.9)]
    fig, ax = plt.subplots(figsize=(5.6, 2.5))
    y = np.arange(3)[::-1]
    vals = [g[1] for g in groups]
    ax.barh(y, vals, height=0.46, color=[BLUE, FILL_MUTED, FILL_MUTED], zorder=2)
    ax.set_yticks(y, [g[0] for g in groups])
    ax.set_xlim(0, 116)
    ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xlabel("attribution correct (%)")
    for yi, v in zip(y, vals):
        ax.text(v + 1.6, yi, f"{v:.1f}%", va="center", fontsize=9, color=INK, weight="bold")
    ax.axvline(90, color=MUTED, linewidth=0.9, zorder=3, ymax=0.86)
    note(ax, 88.4, 1.25, "90% audit threshold", size=8, ha="center", va="center", rotation=90)
    ax.text(0, 2.62, "169 of 184 sampled detections · 3 frames × 9 matches",
            fontsize=8, color=MUTED, va="center")
    ax.set_ylim(-0.6, 2.95)
    chrome(ax, axis="x")
    save(fig, FIG / "fig_audit.png")


def team_filter():
    """Figure 22 - how much the attribution filter removes."""
    total, dropped = 25153, 11161
    kept = total - dropped
    fig, ax = plt.subplots(figsize=(6.6, 2.5))

    # "Removed" is drawn first so that the boundary between the two segments
    # falls at 44% on the axis, in line with the aggregate marker below it.
    d_pct, k_pct = dropped / total * 100, kept / total * 100
    ax.barh([1], [d_pct], height=0.42, color=BLUE, zorder=2)
    ax.barh([1], [k_pct], left=d_pct + 0.6, height=0.42, color=FILL_MUTED, zorder=2)
    ax.text(d_pct / 2, 1, f"removed  {dropped:,}", ha="center", va="center",
            fontsize=8.5, color="white", weight="bold")
    ax.text(d_pct + k_pct / 2, 1, f"kept and credited  {kept:,}", ha="center", va="center",
            fontsize=8.5, color=INK2, weight="bold")

    ax.plot([21, 78], [0.22, 0.22], color=AXIS, linewidth=1.6, zorder=2,
            solid_capstyle="butt")
    ax.scatter([44], [0.22], s=42, color=BLUE, zorder=3,
               edgecolor=SURFACE, linewidth=1.6)
    for v, lab in [(21, "21%"), (78, "78%")]:
        ax.text(v, -0.06, lab, ha="center", va="top", fontsize=7.8, color=MUTED)
    ax.text(44, 0.42, "44% aggregate", ha="center", va="bottom", fontsize=8, color=INK2)
    ax.text(0, -0.42, "per-match removal rate across nine matches", fontsize=8,
            color=MUTED, style="italic")

    ax.set_xlim(0, 101)
    ax.set_ylim(-0.55, 1.45)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.text(0, 1.35, f"{total:,} raw detections across nine matches", fontsize=8, color=MUTED)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, FIG / "fig_team_filter.png")


def confidence():
    """Figure 23 - quality-weighting discounts uncertain detections."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0),
                             gridspec_kw={"width_ratios": [1, 1.5]})

    ax = axes[0]
    vals = [29.0, 9.5]
    x = np.arange(2)
    ax.bar(x, vals, width=0.5, color=[FILL_MUTED, BLUE], zorder=2)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 0.9, f"{v:.1f}%", ha="center", fontsize=9.5, color=INK, weight="bold")
    ax.set_xticks(x, ["share of\nraw detections", "share of\nquality exposure"])
    ax.set_ylim(0, 36)
    ax.set_ylabel("%")
    ax.set_title("detections below 0.4 confidence", fontsize=8.5, color=INK2, pad=8)
    ax.annotate("", xy=(0.82, 12.5), xytext=(0.18, 28), zorder=3,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.1,
                                connectionstyle="arc3,rad=-0.25"))
    note(ax, 0.5, 22.5, "discounted", color=INK2, size=8, ha="center")
    chrome(ax)

    ax = axes[1]
    bands = [("< 0.4", 9.5, RAMP[0]), ("0.4 - 0.8", 26.5, RAMP[2]), ("≥ 0.8", 64.0, RAMP[4])]
    left = 0.0
    for label, v, c in bands:
        ax.barh([0], [v], left=left, height=0.42, color=c, zorder=2)
        # A value only goes inside a segment when it fits there.
        if v >= 20:
            ax.text(left + v / 2, 0, f"{v:.1f}%", ha="center", va="center", fontsize=8.5,
                    color="white", weight="bold")
            ax.text(left + v / 2, -0.31, label, ha="center", va="top", fontsize=8, color=INK2)
        else:
            ax.text(left + v / 2, -0.31, f"{label}\n{v:.1f}%", ha="center", va="top",
                    fontsize=8, color=INK2)
        left += v + 0.7
    ax.set_xlim(0, 103)
    ax.set_ylim(-0.95, 0.5)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.set_title("share of quality exposure by detection confidence", fontsize=8.5,
                 color=INK2, pad=8)
    for s in ("left", "right", "top", "bottom"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    save(fig, FIG / "fig_confidence.png")


def sensitivity():
    """Figure 24 - the two thresholds are not equally consequential."""
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)

    ax = axes[0]
    xs, ys = [0.02, 0.05, 0.10], [100, 29, 2]
    ax.plot(xs, ys, color=BLUE, marker="o", markeredgecolor=SURFACE, markeredgewidth=1.6)
    for xi, yi, ha in zip(xs, ys, ["left", "center", "right"]):
        ax.text(xi, yi + 5, f"{yi}%", ha=ha, fontsize=8.5, color=INK2)
    ax.set_xlabel("visibility floor")
    ax.set_ylabel("quality exposure retained (%)")
    ax.set_xticks(xs, ["0.02", "0.05", "0.10"])
    note(ax, 0.055, 62, "a floor of 0.10 removes\n98% of genuine signal", color=INK2, size=8, va="center")
    chrome(ax)

    ax = axes[1]
    xs, ys = [0.25, 0.40, 0.60], [100, 98, 95.5]
    ax.plot(xs, ys, color=ORANGE, marker="s", markeredgecolor=SURFACE, markeredgewidth=1.6)
    for xi, yi, ha in zip(xs, ys, ["left", "center", "right"]):
        ax.text(xi, yi + 5, f"{yi:g}%", ha=ha, fontsize=8.5, color=INK2)
    ax.set_xlabel("confidence floor")
    ax.set_xticks(xs, ["0.25", "0.40", "0.60"])
    note(ax, 0.28, 62, "under 5% lost across\nthe whole sweep", color=INK2, size=8, va="center")
    chrome(ax)
    ax.set_ylim(-6, 118)
    fig.tight_layout()
    save(fig, FIG / "fig_sensitivity.png")


def sampling_bias():
    """Figure 25 - sparse sampling over-measures exposure."""
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    labels = ["native\n50 fps", "deployed\n2 fps"]
    vals = [100, 163]
    x = np.arange(2)
    ax.bar(x, vals, width=0.48, color=[FILL_MUTED, BLUE], zorder=2)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 4, f"{v}", ha="center", fontsize=9.5, color=INK, weight="bold")
    ax.set_xticks(x, labels)
    ax.set_ylabel("measured exposure (native = 100)")
    ax.set_ylim(0, 215)
    ax.set_yticks(np.arange(0, 176, 25))
    ax.annotate("", xy=(1, 188), xytext=(0, 188), zorder=3,
                arrowprops=dict(arrowstyle="-|>", color=MUTED, linewidth=1.0))
    ax.text(0.5, 194, "+63% over-measurement", ha="center", fontsize=8.5, color=INK2)
    chrome(ax)
    save(fig, FIG / "fig_sampling_bias.png")


# ==========================================================================

FIGURES = {
    "frameselect": frameselect,
    "labelassist": labelassist,
    "system_arch": system_arch,
    "pipeline": pipeline,
    "three_tier": three_tier,
    "class_dist": class_dist,
    "content_profile": content_profile,
    "split_protocol": split_protocol,
    "training_curves": training_curves,
    "rfdetr_perclass": rfdetr_perclass,
    "rfdetr_curve": rfdetr_curve,
    "data_efficiency": data_efficiency,
    "occlusion": occlusion,
    "audit": audit,
    "team_filter": team_filter,
    "confidence": confidence,
    "sensitivity": sensitivity,
    "sampling_bias": sampling_bias,
}


def main():
    use_style()
    wanted = sys.argv[1:] or list(FIGURES)
    for name in wanted:
        if name not in FIGURES:
            raise SystemExit(f"unknown figure {name!r}; choose from {', '.join(FIGURES)}")
        print(name)
        FIGURES[name]()


if __name__ == "__main__":
    main()
