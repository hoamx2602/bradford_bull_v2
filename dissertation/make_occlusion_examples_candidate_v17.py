"""Build the Section 5.4 plate of qualitative held-out occlusion examples.

The plate is deliberately labelled as qualitative candidate evidence.  It does
not substitute for rating every held-out ground-truth instance under a fixed
occlusion protocol.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pycocotools.coco import COCO


ROOT = Path(r"D:\bradford_bull_v2")
sys.path.insert(0, str(ROOT / "dissertation"))
import make_figure_09_detection_evidence_v17 as figure_09  # noqa: E402


PREDICTIONS = ROOT / "dissertation" / "v17_data" / "rfdetr_test_predictions_conf035.json"
OUTPUT = (
    ROOT
    / "dissertation"
    / "LogoLens_MSc_Dissertation_v17_media"
    / "figure_08_heldout_occlusion_examples.png"
)
OUTPUT_JSON = ROOT / "dissertation" / "v17_data" / "figure_08_occlusion_examples.json"

# Hand-reviewed candidate labels.  The levels follow the dissertation's
# retained audit scale: 0 clear, 1 partly covered, 2 heavily covered.
SELECTIONS = [
    {
        "image_id": 7,
        "annotation_id": 32,
        "level": 0,
        "level_label": "Clear",
        "rationale": "The complete Top Notch mark is visible without foreground obstruction.",
    },
    {
        "image_id": 61,
        "annotation_id": 164,
        "level": 1,
        "level_label": "Partially occluded",
        "rationale": "Another player's arm covers part of the Aon mark while the remaining letters are visible.",
    },
    {
        "image_id": 53,
        "annotation_id": 152,
        "level": 1,
        "level_label": "Partially occluded",
        "rationale": "The player's hand and body pose obscure part of the Aon shorts mark.",
    },
    {
        "image_id": 37,
        "annotation_id": 134,
        "level": 2,
        "level_label": "Heavily occluded",
        "rationale": "A foreground head obscures most of the small Fairway mark.",
    },
]

CANVAS_WIDTH = 3200
MARGIN = 88
GUTTER = 56
TOP_HEIGHT = 118
PANEL_WIDTH = (CANVAS_WIDTH - 2 * MARGIN - GUTTER) // 2
PANEL_HEADER = 112
PANEL_IMAGE_HEIGHT = 850
ROW_GAP = 70
FOOTER_HEIGHT = 150
INK = "#172033"
MUTED = "#5C667A"
BORDER = "#CBD5E1"
SURFACE = "#F7F9FC"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(path, size=size)


def dashed_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    colour: str,
    width: int = 6,
    dash: int = 22,
    gap: int = 11,
) -> None:
    x1, y1, x2, y2 = box
    for start in range(x1, x2, dash + gap):
        draw.line((start, y1, min(start + dash, x2), y1), fill=colour, width=width)
        draw.line((start, y2, min(start + dash, x2), y2), fill=colour, width=width)
    for start in range(y1, y2, dash + gap):
        draw.line((x1, start, x1, min(start + dash, y2)), fill=colour, width=width)
        draw.line((x2, start, x2, min(start + dash, y2)), fill=colour, width=width)


def context_crop(source: Image.Image, bbox: list[float]) -> Image.Image:
    x, y, width, height = bbox
    centre_x = x + width / 2
    centre_y = y + height / 2
    side = max(max(width, height) * 4.2, 260)
    crop_width = min(side * 1.4, source.width)
    crop_height = min(side, source.height)
    left = min(max(0, centre_x - crop_width / 2), source.width - crop_width)
    top = min(max(0, centre_y - crop_height / 2), source.height - crop_height)
    return source.crop((int(left), int(top), int(left + crop_width), int(top + crop_height)))


def target_match(record: dict, annotation_id: int) -> tuple[dict, dict | None, float | None]:
    ground_truth_index = next(
        index
        for index, annotation in enumerate(record["ground_truth"])
        if annotation["id"] == annotation_id
    )
    ground_truth = record["ground_truth"][ground_truth_index]
    for match in record["matches"]:
        if match["ground_truth_index"] == ground_truth_index:
            prediction = record["predictions"][match["prediction_index"]]
            return ground_truth, prediction, match["iou"]
    return ground_truth, None, None


def render_panel_frame(
    record: dict,
    annotation: dict,
    prediction: dict | None,
    categories: dict[int, dict],
) -> Image.Image:
    source = Image.open(figure_09.DATASET_DIR / record["file_name"]).convert("RGB")
    frame = ImageOps.fit(
        source,
        (PANEL_WIDTH, PANEL_IMAGE_HEIGHT),
        method=Image.Resampling.LANCZOS,
    )
    scale_x = PANEL_WIDTH / source.width
    scale_y = PANEL_IMAGE_HEIGHT / source.height
    x, y, width, height = annotation["bbox"]
    box = (
        int(x * scale_x),
        int(y * scale_y),
        int((x + width) * scale_x),
        int((y + height) * scale_y),
    )
    colour = figure_09.brand_colour(annotation["category_id"], categories)
    draw = ImageDraw.Draw(frame)
    if prediction is None:
        dashed_rectangle(draw, box, colour)
    else:
        draw.rectangle(box, outline=colour, width=6)

    zoom = context_crop(source, annotation["bbox"])
    zoom_size = (470, 335)
    zoom = ImageOps.fit(zoom, zoom_size, method=Image.Resampling.LANCZOS)
    zoom_draw = ImageDraw.Draw(zoom)
    zoom_draw.rectangle((2, 2, zoom_size[0] - 3, zoom_size[1] - 3), outline="white", width=6)
    zoom_draw.rectangle((8, 8, zoom_size[0] - 9, zoom_size[1] - 9), outline=colour, width=5)
    inset_x = PANEL_WIDTH - zoom_size[0] - 24
    inset_y = PANEL_IMAGE_HEIGHT - zoom_size[1] - 24
    draw.rounded_rectangle(
        (inset_x - 8, inset_y - 8, inset_x + zoom_size[0] + 8, inset_y + zoom_size[1] + 8),
        radius=10,
        fill="white",
        outline=BORDER,
        width=3,
    )
    frame.paste(zoom, (inset_x, inset_y))
    # Link the source box to the enlarged crop as a conventional academic
    # callout.  A white underlay keeps the two legs visible on busy footage.
    source_upper = (box[2], box[1])
    source_lower = (box[2], box[3])
    inset_upper = (inset_x, inset_y)
    inset_lower = (inset_x, inset_y + zoom_size[1])
    draw.line((source_upper, inset_upper), fill="white", width=11)
    draw.line((source_lower, inset_lower), fill="white", width=11)
    draw.line((source_upper, inset_upper), fill=colour, width=5)
    draw.line((source_lower, inset_lower), fill=colour, width=5)
    return frame


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        coco = COCO(str(figure_09.ANNOTATIONS))
    categories = {row["id"]: row for row in coco.loadCats(coco.getCatIds())}
    prediction_dump = json.loads(PREDICTIONS.read_text(encoding="utf-8"))
    records = {
        record["image_id"]: record
        for record in figure_09.build_frame_records(coco, prediction_dump["predictions"])
    }

    canvas_height = (
        MARGIN
        + TOP_HEIGHT
        + 2 * (PANEL_HEADER + PANEL_IMAGE_HEIGHT)
        + ROW_GAP
        + FOOTER_HEIGHT
        + MARGIN
    )
    canvas = Image.new("RGB", (CANVAS_WIDTH, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (MARGIN, MARGIN - 12),
        "Held-out examples across occlusion conditions",
        font=font(48, bold=True),
        fill=INK,
    )
    draw.text(
        (MARGIN, MARGIN + 51),
        "RF-DETR outcomes at confidence 0.35; qualitative cases rather than an aggregate benchmark",
        font=font(25),
        fill=MUTED,
    )

    evidence_rows: list[dict] = []
    start_y = MARGIN + TOP_HEIGHT
    for index, selection in enumerate(SELECTIONS):
        record = records[selection["image_id"]]
        annotation, prediction, overlap = target_match(record, selection["annotation_id"])
        class_name = figure_09.display_name(annotation["category_id"], categories)
        outcome = "Missed" if prediction is None else "Detected"
        score_text = "no prediction" if prediction is None else f"confidence {prediction['score']:.3f}"
        column = index % 2
        row = index // 2
        x = MARGIN + column * (PANEL_WIDTH + GUTTER)
        y = start_y + row * (PANEL_HEADER + PANEL_IMAGE_HEIGHT + ROW_GAP)
        draw.rounded_rectangle(
            (x, y, x + PANEL_WIDTH, y + PANEL_HEADER + PANEL_IMAGE_HEIGHT),
            radius=16,
            fill="white",
            outline=BORDER,
            width=3,
        )
        draw.rounded_rectangle(
            (x + 1, y + 1, x + PANEL_WIDTH - 1, y + PANEL_HEADER + 16),
            radius=15,
            fill=SURFACE,
        )
        draw.rectangle(
            (x + 1, y + PANEL_HEADER - 16, x + PANEL_WIDTH - 1, y + PANEL_HEADER),
            fill=SURFACE,
        )
        letter = chr(ord("A") + index)
        badge = (x + 24, y + 31, x + 72, y + 79)
        draw.ellipse(badge, fill="#E6EEF8")
        draw.text(
            ((badge[0] + badge[2]) / 2, (badge[1] + badge[3]) / 2),
            letter,
            font=font(29, bold=True),
            fill=INK,
            anchor="mm",
        )
        draw.text(
            (x + 92, y + 20),
            f"{selection['level_label']} — {class_name}",
            font=font(31, bold=True),
            fill=INK,
        )
        draw.text(
            (x + 92, y + 63),
            f"{outcome} | {score_text}",
            font=font(23),
            fill=MUTED,
        )
        panel_frame = render_panel_frame(record, annotation, prediction, categories)
        canvas.paste(panel_frame, (x, y + PANEL_HEADER))

        evidence_rows.append(
            {
                **selection,
                "file_name": record["file_name"],
                "class_name": categories[annotation["category_id"]]["name"],
                "bbox": annotation["bbox"],
                "outcome": outcome.lower(),
                "confidence": None if prediction is None else prediction["score"],
                "iou": overlap,
            }
        )

    footer_top = canvas_height - MARGIN - FOOTER_HEIGHT + 18
    draw.line((MARGIN, footer_top - 16, CANVAS_WIDTH - MARGIN, footer_top - 16), fill=BORDER, width=2)
    draw.text(
        (MARGIN, footer_top),
        "Solid box = matched ground truth   |   dashed box = missed ground truth   |   colour = sponsor class",
        font=font(24, bold=True),
        fill=INK,
    )
    note = (
        "Quantitative clear-versus-occluded reporting requires full held-out annotation "
        "and, ideally, a second rater."
    )
    draw.text((MARGIN, footer_top + 59), note, font=font(23), fill=MUTED)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, optimize=True)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "weights": prediction_dump["weights"],
                "confidence": prediction_dump["confidence"],
                "iou_threshold": prediction_dump["iou_threshold"],
                "scope": "qualitative examples from the held-out test split; not an aggregate occlusion benchmark",
                "examples": evidence_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {OUTPUT_JSON}")
    for row in evidence_rows:
        print(
            f"image {row['image_id']} ann {row['annotation_id']} | {row['level_label']} | "
            f"{row['class_name']} | {row['outcome']} | {row['confidence']}"
        )


if __name__ == "__main__":
    main()
