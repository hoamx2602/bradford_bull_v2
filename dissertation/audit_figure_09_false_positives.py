"""Create a review sheet for every unmatched RF-DETR prediction at Figure 9's operating point.

This is an annotation-quality audit, not a second metric calculation.  Each
panel preserves the source pixels and shows both a contextual crop and a tight
crop of one prediction that the COCO evaluator counts as a false positive.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pycocotools.coco import COCO
from collections import Counter


ROOT = Path(r"D:\bradford_bull_v2")
sys.path.insert(0, str(ROOT / "dissertation"))
import make_figure_09_detection_evidence_v17 as figure_09  # noqa: E402


PREDICTIONS = ROOT / "dissertation" / "v17_data" / "rfdetr_test_predictions_conf035.json"
OUTPUT = ROOT / "dissertation" / "v17_data" / "figure_09_false_positive_audit.png"
OUTPUT_JSON = ROOT / "dissertation" / "v17_data" / "figure_09_false_positive_audit.json"

PANEL_WIDTH = 1380
PANEL_HEIGHT = 430
COLUMNS = 2
MARGIN = 42
GAP = 30
CONTEXT_SIZE = (890, 334)
ZOOM_SIZE = (360, 334)
INK = "#172033"
MUTED = "#5C667A"
BORDER = "#CBD5E1"

# Visual review decisions made against the source-resolution context and tight
# crops.  "Plausible annotation omission" deliberately does not assert that a
# blurred mark is definitively the predicted class; it records that the box
# encloses a sponsor-like kit mark with no reference annotation.
AUDIT_DECISIONS = {
    "FP01": (
        "plausible_annotation_omission",
        "Sponsor-like lower-back kit mark; no overlapping ground-truth box.",
    ),
    "FP02": (
        "indeterminate",
        "The small blurred sock mark is not legible enough for a defensible class judgement.",
    ),
    "FP03": (
        "plausible_annotation_omission",
        "The box encloses a visible Aon wordmark on the shorts, absent from the annotations.",
    ),
    "FP04": (
        "indeterminate",
        "The motion-blurred chest patch is not legible enough for a defensible class judgement.",
    ),
    "FP05": (
        "plausible_annotation_omission",
        "Sponsor-like lower-back kit mark; no overlapping ground-truth box.",
    ),
    "FP06": (
        "plausible_annotation_omission",
        "Sponsor-like upper-chest kit mark; no overlapping ground-truth box.",
    ),
    "FP07": (
        "verified_model_error",
        "Opponent-kit wordmark is predicted as Top Notch although it is visibly a different mark.",
    ),
    "FP08": (
        "plausible_annotation_omission",
        "Sponsor-like side/back kit mark; no overlapping ground-truth box.",
    ),
    "FP09": (
        "duplicate_detection",
        "Second ASC Group prediction overlaps an already matched same-class ground-truth box (IoU 0.797).",
    ),
    "FP10": (
        "plausible_annotation_omission",
        "Sponsor-like upper-chest kit mark; no overlapping ground-truth box.",
    ),
    "FP11": (
        "verified_model_error",
        "Prediction overlaps MNA Cladding ground truth (IoU 0.860) but assigns Romantica.",
    ),
    "FP12": (
        "plausible_annotation_omission",
        "Partially visible edge-of-frame kit logo; no overlapping ground-truth box.",
    ),
    "FP13": (
        "verified_model_error",
        "Opponent-kit graphic is predicted as Top Notch although it is visibly a different mark.",
    ),
    "FP14": (
        "plausible_annotation_omission",
        "Visible sponsor-like upper-back mark; no overlapping ground-truth box.",
    ),
}

STATUS_LABELS = {
    "plausible_annotation_omission": "Plausible annotation omission",
    "indeterminate": "Indeterminate from source frame",
    "verified_model_error": "Verified model error",
    "duplicate_detection": "Duplicate detection",
}
STATUS_COLOURS = {
    "plausible_annotation_omission": "#9A6700",
    "indeterminate": "#64748B",
    "verified_model_error": "#B42318",
    "duplicate_detection": "#6941C6",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(path, size=size)


def crop_box(
    image_width: int,
    image_height: int,
    bbox: list[float],
    width_multiplier: float,
    height_multiplier: float,
    target_ratio: float,
) -> tuple[int, int, int, int]:
    x, y, width, height = bbox
    centre_x = x + width / 2
    centre_y = y + height / 2
    crop_width = max(width * width_multiplier, 300)
    crop_height = max(height * height_multiplier, 190)
    if crop_width / crop_height < target_ratio:
        crop_width = crop_height * target_ratio
    else:
        crop_height = crop_width / target_ratio
    crop_width = min(crop_width, image_width)
    crop_height = min(crop_height, image_height)
    left = min(max(0, centre_x - crop_width / 2), image_width - crop_width)
    top = min(max(0, centre_y - crop_height / 2), image_height - crop_height)
    return (
        int(round(left)),
        int(round(top)),
        int(round(left + crop_width)),
        int(round(top + crop_height)),
    )


def annotated_crop(
    source: Image.Image,
    bbox: list[float],
    crop: tuple[int, int, int, int],
    size: tuple[int, int],
    colour: str,
) -> Image.Image:
    left, top, right, bottom = crop
    piece = source.crop(crop).resize(size, Image.Resampling.LANCZOS)
    scale_x = size[0] / (right - left)
    scale_y = size[1] / (bottom - top)
    x, y, width, height = bbox
    projected = (
        int((x - left) * scale_x),
        int((y - top) * scale_y),
        int((x + width - left) * scale_x),
        int((y + height - top) * scale_y),
    )
    draw = ImageDraw.Draw(piece)
    draw.rectangle(projected, outline=colour, width=5)
    return piece


def main() -> None:
    coco = COCO(str(figure_09.ANNOTATIONS))
    categories = {row["id"]: row for row in coco.loadCats(coco.getCatIds())}
    prediction_dump = json.loads(PREDICTIONS.read_text(encoding="utf-8"))
    records = figure_09.build_frame_records(coco, prediction_dump["predictions"])

    candidates: list[dict] = []
    for record in records:
        for prediction_index in record["false_positive_indices"]:
            prediction = record["predictions"][prediction_index]
            candidates.append(
                {
                    "score": prediction["score"],
                    "record": record,
                    "prediction": prediction,
                    "prediction_index": prediction_index,
                }
            )
    candidates.sort(key=lambda item: (-item["score"], item["record"]["image_id"]))

    rows = (len(candidates) + COLUMNS - 1) // COLUMNS
    canvas_width = 2 * MARGIN + COLUMNS * PANEL_WIDTH + (COLUMNS - 1) * GAP
    canvas_height = 2 * MARGIN + 80 + rows * PANEL_HEIGHT + (rows - 1) * GAP
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (MARGIN, MARGIN - 5),
        "Audit of all unmatched RF-DETR predictions (confidence >= 0.35)",
        font=font(38, bold=True),
        fill=INK,
    )
    draw.text(
        (canvas_width - MARGIN, MARGIN + 5),
        "Context crop  |  tight crop; box colour = predicted sponsor class",
        font=font(22),
        fill=MUTED,
        anchor="ra",
    )

    audit_rows: list[dict] = []
    for rank, item in enumerate(candidates, start=1):
        audit_id = f"FP{rank:02d}"
        review_status, review_rationale = AUDIT_DECISIONS[audit_id]
        record = item["record"]
        prediction = item["prediction"]
        source = Image.open(figure_09.DATASET_DIR / record["file_name"]).convert("RGB")
        colour = figure_09.brand_colour(prediction["category_id"], categories)
        context_box = crop_box(
            source.width,
            source.height,
            prediction["bbox"],
            width_multiplier=7.0,
            height_multiplier=7.0,
            target_ratio=CONTEXT_SIZE[0] / CONTEXT_SIZE[1],
        )
        zoom_box = crop_box(
            source.width,
            source.height,
            prediction["bbox"],
            width_multiplier=2.4,
            height_multiplier=2.4,
            target_ratio=ZOOM_SIZE[0] / ZOOM_SIZE[1],
        )
        context = annotated_crop(source, prediction["bbox"], context_box, CONTEXT_SIZE, colour)
        zoom = annotated_crop(source, prediction["bbox"], zoom_box, ZOOM_SIZE, colour)

        column = (rank - 1) % COLUMNS
        row = (rank - 1) // COLUMNS
        x = MARGIN + column * (PANEL_WIDTH + GAP)
        y = MARGIN + 80 + row * (PANEL_HEIGHT + GAP)
        draw.rounded_rectangle(
            (x, y, x + PANEL_WIDTH, y + PANEL_HEIGHT),
            radius=14,
            fill="#F8FAFC",
            outline=BORDER,
            width=2,
        )
        name = figure_09.display_name(prediction["category_id"], categories)
        heading = (
            f"FP{rank:02d}  |  predicted {name}  |  confidence {prediction['score']:.3f}  "
            f"|  image {record['image_id']}"
        )
        draw.text((x + 20, y + 14), heading, font=font(24, bold=True), fill=INK)
        draw.text(
            (x + PANEL_WIDTH - 20, y + 17),
            f"frame GT/TP/FP/FN = {len(record['ground_truth'])}/{record['tp']}/{record['fp']}/{record['fn']}",
            font=font(19),
            fill=MUTED,
            anchor="ra",
        )
        draw.text(
            (x + 20, y + 44),
            STATUS_LABELS[review_status],
            font=font(18, bold=True),
            fill=STATUS_COLOURS[review_status],
        )
        canvas.paste(context, (x + 20, y + 68))
        canvas.paste(zoom, (x + 20 + CONTEXT_SIZE[0] + 24, y + 68))

        audit_rows.append(
            {
                "audit_id": audit_id,
                "image_id": record["image_id"],
                "file_name": record["file_name"],
                "predicted_category_id": prediction["category_id"],
                "predicted_class": categories[prediction["category_id"]]["name"],
                "confidence": prediction["score"],
                "bbox": prediction["bbox"],
                "frame_counts": {
                    "gt": len(record["ground_truth"]),
                    "tp": record["tp"],
                    "fp": record["fp"],
                    "fn": record["fn"],
                },
                "review_status": review_status,
                "review_rationale": review_rationale,
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, optimize=True)
    status_counts = Counter(row["review_status"] for row in audit_rows)
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "weights": prediction_dump["weights"],
                "confidence": prediction_dump["confidence"],
                "iou_threshold": prediction_dump["iou_threshold"],
                "candidate_count": len(audit_rows),
                "status_counts": dict(status_counts),
                "candidates": audit_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote: {OUTPUT}")
    print(f"wrote: {OUTPUT_JSON}")
    print(f"candidates: {len(audit_rows)}")
    print(f"status counts: {dict(status_counts)}")


if __name__ == "__main__":
    main()
