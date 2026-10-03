"""Export the reusable source components used in dissertation Figure 8."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(r"D:\bradford_bull_v2")
DATASET = ROOT / "datasets" / "auto_label_white_matchsplit" / "test"
EVIDENCE = ROOT / "dissertation" / "v17_data" / "figure_08_occlusion_examples.json"
COMPOSITE = (
    ROOT
    / "dissertation"
    / "LogoLens_MSc_Dissertation_v17_media"
    / "figure_08_occlusion_examples_v2.png"
)
OUTPUT = ROOT / "dissertation" / "figure_08_source_images"

LABELS = [
    ("A", "clear_top_notch"),
    ("B", "partial_aon_detected"),
    ("C", "partial_aon_missed"),
    ("D", "heavy_fairway_detected"),
]

COLOURS = {
    "top_notch_home": "#59A14F",
    "aon_home": "#0072B2",
    "fairway_home": "#2F4B7C",
}

# Coordinates in the publication composite before any display scaling.
PANEL_RECTS = {
    "A": (88, 206, 1572, 1168),
    "B": (1628, 206, 3112, 1168),
    "C": (88, 1238, 1572, 2200),
    "D": (1628, 1238, 3112, 2200),
}


def context_bounds(image: Image.Image, bbox: list[float]) -> tuple[int, int, int, int]:
    x, y, width, height = bbox
    centre_x = x + width / 2
    centre_y = y + height / 2
    side = max(max(width, height) * 4.2, 260)
    crop_width = min(side * 1.4, image.width)
    crop_height = min(side, image.height)
    left = min(max(0, centre_x - crop_width / 2), image.width - crop_width)
    top = min(max(0, centre_y - crop_height / 2), image.height - crop_height)
    return (
        int(left),
        int(top),
        int(left + crop_width),
        int(top + crop_height),
    )


def dashed_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    colour: str,
    width: int = 8,
    dash: int = 28,
    gap: int = 14,
) -> None:
    x1, y1, x2, y2 = box
    for start in range(x1, x2, dash + gap):
        draw.line((start, y1, min(start + dash, x2), y1), fill=colour, width=width)
        draw.line((start, y2, min(start + dash, x2), y2), fill=colour, width=width)
    for start in range(y1, y2, dash + gap):
        draw.line((x1, start, x1, min(start + dash, y2)), fill=colour, width=width)
        draw.line((x2, start, x2, min(start + dash, y2)), fill=colour, width=width)


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    composite = Image.open(COMPOSITE).convert("RGB")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    scale_x = composite.width / 3200
    scale_y = composite.height / 2438

    for (panel, slug), example in zip(LABELS, evidence["examples"], strict=True):
        source_path = DATASET / example["file_name"]
        source = Image.open(source_path).convert("RGB")
        prefix = f"{panel}_{slug}"

        # Exact dataset frame, copied without recompression.
        shutil.copy2(source_path, OUTPUT / f"{prefix}_source_full.jpg")

        # Clean close-up used to construct the magnified inset.
        crop_box = context_bounds(source, example["bbox"])
        source.crop(crop_box).save(OUTPUT / f"{prefix}_logo_crop_clean.png")

        # Full-resolution source with only the target annotation overlaid.
        boxed = source.copy()
        x, y, width, height = example["bbox"]
        target = (int(x), int(y), int(x + width), int(y + height))
        colour = COLOURS[example["class_name"]]
        draw = ImageDraw.Draw(boxed)
        if example["outcome"] == "missed":
            dashed_rectangle(draw, target, colour)
        else:
            draw.rectangle(target, outline=colour, width=8)
        boxed.save(OUTPUT / f"{prefix}_source_boxed.png")

        # Exact panel crop from the final publication composite.
        left, top, right, bottom = PANEL_RECTS[panel]
        scaled_rect = (
            round(left * scale_x),
            round(top * scale_y),
            round(right * scale_x),
            round(bottom * scale_y),
        )
        composite.crop(scaled_rect).save(OUTPUT / f"{prefix}_panel_complete.png")

    print(f"Exported {len(LABELS)} source-image sets to: {OUTPUT}")


if __name__ == "__main__":
    main()
