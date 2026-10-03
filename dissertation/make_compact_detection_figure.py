"""Create one print-ready qualitative logo-detection figure.

The dissertation previously used three consecutive full-width detection
figures.  This script reruns the clip-disjoint checkpoint on two images from
the retained validation export and combines the complementary cases into one
shared-legend plate.  The plate is qualitative evidence only; reported metrics
come from the leakage-controlled evaluation described in the dissertation.

* panel A: a dense, multi-player, multi-brand frame;
* panel B: a difficult perspective case with a confidence gradient.

Run from the repository root with the project's model environment::

    conda run -n bradford_bulls_logo python \
        dissertation/make_compact_detection_figure.py
"""
from __future__ import annotations

import glob
from collections import defaultdict
from pathlib import Path

import torch
from PIL import Image, ImageDraw
from ultralytics import YOLO

from make_detection_figures import (
    BRAND_COLOUR,
    CONF,
    DATA,
    DISPLAY,
    FALLBACK,
    IMGSZ,
    WEIGHTS,
    brand_of,
    font,
    halo_text,
    redact,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures" / "fig_detection_evidence_compact.png"
PANEL_WIDTH = 1600
PANEL_HEIGHT = 900
GAP = 12
LEGEND_PAD = 24
LEGEND_LINE = 58

PANELS = (
    (
        "clip_001_00-10_0000450_t00015000ms",
        "A",
        "Dense multi-player scene",
    ),
    (
        "clip_002_00-39_0000350_t00014000ms",
        "B",
        "Close-up and scale variation",
    ),
)


def find_frame(stem: str) -> Path:
    hits = glob.glob(str(DATA / "valid" / (stem + "*")))
    if hits:
        return Path(hits[0])
    raise FileNotFoundError(f"Validation frame not found: {stem}")


def annotate(src: Path, boxes: list[tuple[float, float, float, float, str, float]],
             panel: str, title: str) -> Image.Image:
    im = redact(Image.open(src).convert("RGB"))
    draw = ImageDraw.Draw(im)
    label_font = font(34)

    for x1, y1, x2, y2, brand, confidence in sorted(boxes, key=lambda box: box[1]):
        colour = BRAND_COLOUR.get(brand, FALLBACK)
        pad = 5
        draw.rectangle((x1 - pad, y1 - pad, x2 + pad, y2 + pad),
                       outline=colour, width=6)
        text = f"{confidence:.2f}"
        left, top, right, bottom = draw.textbbox((0, 0), text, font=label_font)
        text_width, text_height = right - left, bottom - top
        tx = min(max(x1 - pad, 4), im.width - text_width - 6)
        ty = y1 - pad - text_height - 12
        if ty < 4:
            ty = y2 + pad + 6
        halo_text(draw, (tx, ty), text, label_font, colour)

    # A compact opaque panel label remains legible over either grass or kit.
    title_font = font(34)
    panel_font = font(42)
    title_width = draw.textbbox((0, 0), title, font=title_font)[2]
    draw.rounded_rectangle((22, 20, 100 + title_width, 88), radius=12,
                           fill=(255, 255, 255), outline=(170, 170, 165), width=2)
    draw.text((40, 27), panel, font=panel_font, fill=(10, 10, 10))
    draw.text((94, 33), title, font=title_font, fill=(35, 35, 35))

    return im.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)


def infer(model: YOLO, src: Path, device: int | str):
    result = model.predict(src, imgsz=IMGSZ, conf=CONF, device=device,
                           verbose=False)[0]
    return [
        (
            *(float(value) for value in box.xyxy[0]),
            brand_of(model.names[int(box.cls)]),
            float(box.conf),
        )
        for box in result.boxes
    ]


def build_legend(brands: list[str]) -> Image.Image:
    columns = 3
    rows = (len(brands) + columns - 1) // columns
    height = 2 * LEGEND_PAD + rows * LEGEND_LINE
    legend = Image.new("RGB", (PANEL_WIDTH, height), "white")
    draw = ImageDraw.Draw(legend)
    legend_font = font(34)
    column_width = PANEL_WIDTH // columns

    for index, brand in enumerate(brands):
        x = LEGEND_PAD + (index % columns) * column_width
        y = LEGEND_PAD + (index // columns) * LEGEND_LINE
        draw.rounded_rectangle((x, y + 3, x + 42, y + 39), radius=6,
                               fill=BRAND_COLOUR.get(brand, FALLBACK),
                               outline=(115, 115, 115), width=2)
        draw.text((x + 58, y), DISPLAY.get(brand, brand),
                  font=legend_font, fill=(15, 15, 15))
    return legend


def main() -> None:
    model = YOLO(str(WEIGHTS))
    device: int | str = 0 if torch.cuda.is_available() else "cpu"
    annotated: list[Image.Image] = []
    brand_scores: dict[str, list[float]] = defaultdict(list)

    for stem, panel, title in PANELS:
        src = find_frame(stem)
        boxes = infer(model, src, device)
        for *_, brand, confidence in boxes:
            brand_scores[brand].append(confidence)
        annotated.append(annotate(src, boxes, panel, title))
        print(f"panel {panel}: {len(boxes)} detections from {src.name}")

    brands = sorted(brand_scores, key=lambda b: (-len(brand_scores[b]), -max(brand_scores[b])))
    legend = build_legend(brands)
    canvas = Image.new(
        "RGB",
        (PANEL_WIDTH, 2 * PANEL_HEIGHT + GAP + legend.height),
        (228, 228, 225),
    )
    canvas.paste(annotated[0], (0, 0))
    canvas.paste(annotated[1], (0, PANEL_HEIGHT + GAP))
    canvas.paste(legend, (0, 2 * PANEL_HEIGHT + GAP))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=True)
    print(f"wrote {OUT} ({canvas.width}x{canvas.height}, {len(brands)} brands)")


if __name__ == "__main__":
    main()
