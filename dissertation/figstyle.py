"""Shared plotting style for every figure drawn for the dissertation.

One place defines the palette, the type sizes and the chart chrome, so that
all figures read as a single system when they sit next to each other in the
document. Figures carry no title of their own: the numbered caption in the
document does that job, and a title inside the image duplicates it.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patheffects import withStroke

# Categorical slots, in fixed order. Validated for colour-vision deficiency
# on a white surface (worst all-pairs deutan dE 9.2, normal-vision dE 24.0).
BLUE = "#2a78d6"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
SERIES = [BLUE, ORANGE, AQUA]

# Ordinal ramp (one hue, light to dark) for ordered stages such as tiers.
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]

INK = "#0b0b0b"          # primary text
INK2 = "#52514e"         # secondary text
MUTED = "#898781"        # axis labels, annotations
GRID = "#e1e0d9"         # hairline gridlines
AXIS = "#c3c2b7"         # baseline / axis rule
SURFACE = "#ffffff"
FILL_MUTED = "#dedcd4"   # a neutral fill for the "rest" of a comparison

DPI = 200


def use_style() -> None:
    plt.rcParams.update({
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.5,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK2,
        "ytick.labelcolor": INK2,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "grid.linestyle": "-",
        "lines.linewidth": 1.8,
        "lines.markersize": 5,
        "legend.frameon": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def chrome(ax, axis: str = "y", spine_left: bool = True) -> None:
    """Recessive grid on the value axis only; drop the spine it duplicates."""
    ax.grid(axis=axis, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    if axis == "y" and not spine_left:
        ax.spines["left"].set_visible(False)
    if axis == "x":
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)


def note(ax, x, y, text, color=MUTED, size=8, **kw):
    """A quiet annotation that stays legible over a mark."""
    kw.setdefault("ha", "left")
    kw.setdefault("va", "center")
    t = ax.text(x, y, text, color=color, fontsize=size, **kw)
    t.set_path_effects([withStroke(linewidth=2.4, foreground=SURFACE)])
    return t


def save(fig, path, pad=0.18):
    fig.savefig(path, bbox_inches="tight", pad_inches=pad, facecolor=SURFACE)
    plt.close(fig)
    print(f"  wrote {path.name}")


# --------------------------------------------------------------------------
# Flow-diagram helpers
#
# Nodes are drawn as text with an auto-sizing rounded bbox, so a label can
# never overflow its box. Arrows are then routed between the boxes' measured
# edges rather than between guessed coordinates.
# --------------------------------------------------------------------------

def node(ax, x, y, text, face=BLUE, fg="white", size=8.5, weight="normal",
         pad=0.55, ec=None, lw=0):
    t = ax.text(x, y, text, ha="center", va="center", fontsize=size,
                color=fg, weight=weight, zorder=3,
                bbox=dict(boxstyle=f"round,pad={pad},rounding_size=0.25",
                          facecolor=face, edgecolor=ec or face, linewidth=lw))
    return t


def _box(fig, ax, t):
    """Measured extent of a node's bbox, in data coordinates."""
    fig.canvas.draw()
    bb = t.get_bbox_patch().get_window_extent(fig.canvas.get_renderer())
    return bb.transformed(ax.transData.inverted())


def arrow(fig, ax, a, b, color=MUTED, lw=1.2, side="v", rad=0.0):
    """Route an arrow between the edges of two nodes."""
    ba, bb = _box(fig, ax, a), _box(fig, ax, b)
    if side == "v":
        start = ((ba.x0 + ba.x1) / 2, ba.y0 if ba.y0 > bb.y1 else ba.y1)
        end = ((bb.x0 + bb.x1) / 2, bb.y1 if ba.y0 > bb.y1 else bb.y0)
    else:
        start = (ba.x1 if ba.x1 < bb.x0 else ba.x0, (ba.y0 + ba.y1) / 2)
        end = (bb.x0 if ba.x1 < bb.x0 else bb.x1, (bb.y0 + bb.y1) / 2)
    ax.annotate("", xy=end, xytext=start, zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=color, linewidth=lw,
                                shrinkA=1.5, shrinkB=1.5,
                                connectionstyle=f"arc3,rad={rad}"))


def blank(figsize):
    """A bare canvas in 0..1 coordinates, for diagrams."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax
