"""Regenerate the representative RF-DETR success and failure cases.

The figure is built from a fresh inference pass over the 61-image held-out
test split using the selected (best EMA) RF-DETR Small checkpoint.  Cases are
selected by the rules stated in Section 3.4, rather than by manual curation.

Visual encoding deliberately preserves the source frames' natural colour.
Box colour identifies the sponsor class, while line pattern and the label prefix
identify the outcome: solid for a correct prediction, short-dashed plus ``FP``
for a false positive, and long-dashed plus ``Missed`` for missed ground truth.
"""

from __future__ import annotations

import contextlib
import io
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pycocotools.coco import COCO


ROOT = Path(r"D:\bradford_bull_v2")
DATASET_DIR = ROOT / "datasets" / "auto_label_white_matchsplit" / "test"
ANNOTATIONS = DATASET_DIR / "_annotations.coco.json"
WEIGHTS = ROOT / "runs" / "rfdetr_matchsplit_r896" / "checkpoint_best_total.pth"
OUTPUT = (
    ROOT
    / "dissertation"
    / "LogoLens_MSc_Dissertation_v17_media"
    / "figure_09_detection_evidence.png"
)
EVIDENCE = ROOT / "dissertation" / "v17_data" / "figure_09_detection_evidence.json"
FALSE_POSITIVE_AUDIT = (
    ROOT / "dissertation" / "v17_data" / "figure_09_false_positive_audit.json"
)
MISSED_GROUND_TRUTH_AUDIT = (
    ROOT / "dissertation" / "v17_data" / "figure_09_missed_ground_truth_audit.json"
)

CONFIDENCE = 0.35
IOU_THRESHOLD = 0.50
SELECTED_EPOCH = 36

CANVAS_WIDTH = 3200
OUTER_MARGIN = 88
GUTTER = 56
TOP_TITLE_HEIGHT = 112
PANEL_HEADER_HEIGHT = 100
PANEL_IMAGE_HEIGHT = 850
ROW_GAP = 70
FOOTER_HEIGHT = 158
PANEL_WIDTH = (CANVAS_WIDTH - 2 * OUTER_MARGIN - GUTTER) // 2

INK = "#172033"
MUTED = "#5C667A"
LIGHT_SURFACE = "#F7F9FC"
BORDER = "#CBD5E1"
STATUS_INK = "#475569"

DISPLAY_NAMES = {
    "aon_home": "Aon",
    "asc_group_home": "ASC Group",
    "atm_home": "ATM",
    "bartercard_home": "Bartercard",
    "cch_home": "CCH",
    "chadlaw_home": "Chadlaw",
    "ellgren_home": "Ellgren",
    "em_workwear_home": "EM Workwear",
    "fairway_home": "Fairway",
    "klg_home": "KLG",
    "mcp_home": "MCP",
    "mna_cladding_home": "MNA Cladding",
    "mna_support_service_home": "MNA Support",
    "paints_lacquers_home": "Paints & Lacquers",
    "romantica_home": "Romantica",
    "top_notch_home": "Top Notch",
}

# A fixed, publication-friendly categorical palette.  Colours identify sponsor
# classes consistently across all four panels; they do not encode correctness.
BRAND_COLOURS = {
    "aon_home": "#0072B2",
    "asc_group_home": "#E69F00",
    "atm_home": "#009E73",
    "bartercard_home": "#CC79A7",
    "cch_home": "#8C564B",
    "chadlaw_home": "#D55E00",
    "ellgren_home": "#56B4E9",
    "em_workwear_home": "#7A5195",
    "fairway_home": "#2F4B7C",
    "klg_home": "#F05A67",
    "mcp_home": "#00A087",
    "mna_cladding_home": "#F39C34",
    "mna_support_service_home": "#6C5CE7",
    "paints_lacquers_home": "#C44E52",
    "romantica_home": "#4E79A7",
    "top_notch_home": "#59A14F",
}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf")
        if bold
        else ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf")
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size=size)


def bbox_iou(a: list[float], b: list[float]) -> float:
    """IoU for COCO-format [x, y, width, height] boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    intersection_width = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    intersection_height = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    intersection = intersection_width * intersection_height
    union = aw * ah + bw * bh - intersection
    return intersection / (union + 1e-9)


def run_inference(coco: COCO) -> list[dict]:
    """Run the selected checkpoint once over every held-out test image."""
    from rfdetr import RFDETRSmall

    model = RFDETRSmall(pretrain_weights=str(WEIGHTS), resolution=896)
    predictions: list[dict] = []
    image_ids = sorted(coco.getImgIds())
    for index, image_id in enumerate(image_ids, start=1):
        info = coco.loadImgs(image_id)[0]
        image = Image.open(DATASET_DIR / info["file_name"]).convert("RGB")
        detections = model.predict(image, threshold=CONFIDENCE)
        for box, category_id, score in zip(
            detections.xyxy, detections.class_id, detections.confidence
        ):
            x1, y1, x2, y2 = (float(value) for value in box)
            predictions.append(
                {
                    "image_id": int(image_id),
                    "category_id": int(category_id),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                    "score": float(score),
                }
            )
        if index % 10 == 0 or index == len(image_ids):
            print(f"inference: {index}/{len(image_ids)} images")
    return predictions


def match_image(ground_truth: list[dict], predictions: list[dict]) -> dict:
    """Greedily match predictions to same-class ground truth by confidence."""
    ordered_predictions = sorted(
        enumerate(predictions), key=lambda item: (-item[1]["score"], item[0])
    )
    used_ground_truth: set[int] = set()
    matched_predictions: set[int] = set()
    matches: list[dict] = []

    for prediction_index, prediction in ordered_predictions:
        candidates: list[tuple[float, int]] = []
        for ground_truth_index, annotation in enumerate(ground_truth):
            if ground_truth_index in used_ground_truth:
                continue
            if annotation["category_id"] != prediction["category_id"]:
                continue
            overlap = bbox_iou(annotation["bbox"], prediction["bbox"])
            if overlap >= IOU_THRESHOLD:
                candidates.append((overlap, ground_truth_index))
        if not candidates:
            continue
        overlap, ground_truth_index = max(candidates)
        used_ground_truth.add(ground_truth_index)
        matched_predictions.add(prediction_index)
        matches.append(
            {
                "prediction_index": prediction_index,
                "ground_truth_index": ground_truth_index,
                "iou": overlap,
            }
        )

    false_positive_indices = [
        index for index in range(len(predictions)) if index not in matched_predictions
    ]
    missed_ground_truth_indices = [
        index for index in range(len(ground_truth)) if index not in used_ground_truth
    ]
    return {
        "matches": matches,
        "matched_prediction_indices": sorted(matched_predictions),
        "false_positive_indices": false_positive_indices,
        "missed_ground_truth_indices": missed_ground_truth_indices,
        "tp": len(matches),
        "fp": len(false_positive_indices),
        "fn": len(missed_ground_truth_indices),
    }


def build_frame_records(coco: COCO, predictions: list[dict]) -> list[dict]:
    predictions_by_image: dict[int, list[dict]] = defaultdict(list)
    for prediction in predictions:
        if prediction["category_id"] != 0:
            predictions_by_image[prediction["image_id"]].append(prediction)

    records: list[dict] = []
    for image_id in sorted(coco.getImgIds()):
        image_info = coco.loadImgs(image_id)[0]
        ground_truth = [
            annotation
            for annotation in coco.loadAnns(coco.getAnnIds(imgIds=[image_id]))
            if annotation["category_id"] != 0
        ]
        image_predictions = predictions_by_image.get(image_id, [])
        matching = match_image(ground_truth, image_predictions)
        records.append(
            {
                "image_id": image_id,
                "file_name": image_info["file_name"],
                "width": image_info["width"],
                "height": image_info["height"],
                "ground_truth": ground_truth,
                "predictions": image_predictions,
                **matching,
            }
        )
    return records


def select_cases(records: list[dict]) -> list[tuple[str, dict]]:
    """Apply the four pre-declared qualitative selection rules."""
    perfect = [
        record
        for record in records
        if record["ground_truth"] and record["fp"] == 0 and record["fn"] == 0
    ]
    if len(perfect) < 2:
        raise RuntimeError("The held-out split does not contain two perfect frames.")

    clear_success = max(
        perfect,
        key=lambda record: (
            max((item["score"] for item in record["predictions"]), default=0.0),
            record["tp"],
            -record["image_id"],
        ),
    )
    multi_logo = max(
        (record for record in perfect if record["image_id"] != clear_success["image_id"]),
        key=lambda record: (
            record["tp"],
            min((item["score"] for item in record["predictions"]), default=0.0),
            -record["image_id"],
        ),
    )
    selected_ids = {clear_success["image_id"], multi_logo["image_id"]}

    if not MISSED_GROUND_TRUTH_AUDIT.exists():
        raise FileNotFoundError(
            "Run audit_figure_09_missed_ground_truth.py before selecting the verified miss panel."
        )
    missed_audit = json.loads(MISSED_GROUND_TRUTH_AUDIT.read_text(encoding="utf-8"))
    invalid_miss_image_ids = {
        row["image_id"]
        for row in missed_audit["candidates"]
        if row["review_status"] == "invalid_non_kit_annotation"
    }
    records_by_image_id = {record["image_id"]: record for record in records}
    miss_candidates: list[tuple[float, int, dict]] = []
    for row in missed_audit["candidates"]:
        if row["review_status"] != "verified_in_scope_kit_logo":
            continue
        if row["image_id"] in selected_ids or row["image_id"] in invalid_miss_image_ids:
            continue
        record = records_by_image_id[row["image_id"]]
        miss_candidates.append((row["relative_area"], row["image_id"], record))
    if not miss_candidates:
        raise RuntimeError("The held-out split does not contain a missed object.")
    difficult_miss = min(miss_candidates, key=lambda item: (item[0], item[1]))[2]
    selected_ids.add(difficult_miss["image_id"])

    if not FALSE_POSITIVE_AUDIT.exists():
        raise FileNotFoundError(
            "Run audit_figure_09_false_positives.py before selecting the verified false-positive panel."
        )
    audit = json.loads(FALSE_POSITIVE_AUDIT.read_text(encoding="utf-8"))
    verified_error_image_ids = {
        row["image_id"]
        for row in audit["candidates"]
        if row["review_status"] in {"verified_model_error", "duplicate_detection"}
    }
    false_positive_candidates: list[tuple[float, int, dict]] = []
    for record in records:
        if (
            record["image_id"] in selected_ids
            or record["image_id"] not in verified_error_image_ids
            or record["fp"] == 0
        ):
            continue
        highest_unmatched_score = max(
            record["predictions"][index]["score"]
            for index in record["false_positive_indices"]
        )
        false_positive_candidates.append(
            (highest_unmatched_score, -record["image_id"], record)
        )
    if not false_positive_candidates:
        raise RuntimeError("The held-out split does not contain a false positive.")
    false_positive = max(false_positive_candidates, key=lambda item: (item[0], item[1]))[2]

    return [
        ("clear_success", clear_success),
        ("multi_logo", multi_logo),
        ("difficult_miss", difficult_miss),
        ("false_positive", false_positive),
    ]


def dashed_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    colour: str,
    width: int = 5,
    dash: int = 18,
    gap: int = 10,
) -> None:
    x1, y1, x2, y2 = box
    for start in range(x1, x2, dash + gap):
        draw.line((start, y1, min(start + dash, x2), y1), fill=colour, width=width)
        draw.line((start, y2, min(start + dash, x2), y2), fill=colour, width=width)
    for start in range(y1, y2, dash + gap):
        draw.line((x1, start, x1, min(start + dash, y2)), fill=colour, width=width)
        draw.line((x2, start, x2, min(start + dash, y2)), fill=colour, width=width)


def text_chip(
    draw: ImageDraw.ImageDraw,
    anchor: tuple[int, int],
    text: str,
    colour: str,
    image_width: int,
    image_height: int,
) -> None:
    label_font = font(24, bold=True)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=label_font)
    text_width, text_height = right - left, bottom - top
    x, y = anchor
    x = min(max(4, x), image_width - text_width - 20)
    if y - text_height - 17 >= 3:
        y = y - text_height - 17
    else:
        y = min(image_height - text_height - 13, y + 7)
    draw.rounded_rectangle(
        (x, y, x + text_width + 16, y + text_height + 10),
        radius=6,
        fill=colour,
    )
    draw.text((x + 8, y + 3), text, font=label_font, fill="white")


def display_name(category_id: int, categories: dict[int, dict]) -> str:
    raw_name = categories[category_id]["name"]
    return DISPLAY_NAMES.get(raw_name, raw_name.replace("_", " ").title())


def brand_colour(category_id: int, categories: dict[int, dict]) -> str:
    raw_name = categories[category_id]["name"]
    return BRAND_COLOURS.get(raw_name, "#64748B")


def render_annotated_frame(record: dict, categories: dict[int, dict]) -> Image.Image:
    source = Image.open(DATASET_DIR / record["file_name"]).convert("RGB")
    frame = ImageOps.fit(
        source,
        (PANEL_WIDTH, PANEL_IMAGE_HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    scale_x = PANEL_WIDTH / source.width
    scale_y = PANEL_IMAGE_HEIGHT / source.height
    draw = ImageDraw.Draw(frame)

    matched = set(record["matched_prediction_indices"])
    false_positives = set(record["false_positive_indices"])
    for index, prediction in enumerate(record["predictions"]):
        x, y, width, height = prediction["bbox"]
        box = (
            int(x * scale_x),
            int(y * scale_y),
            int((x + width) * scale_x),
            int((y + height) * scale_y),
        )
        colour = brand_colour(prediction["category_id"], categories)
        if index in matched:
            prefix = ""
            draw.rectangle(box, outline=colour, width=5)
        elif index in false_positives:
            prefix = "FP · "
            dashed_rectangle(draw, box, colour, width=6, dash=10, gap=7)
        else:
            continue
        label = (
            f"{prefix}{display_name(prediction['category_id'], categories)} "
            f"{prediction['score']:.2f}"
        )
        text_chip(draw, (box[0], box[1]), label, colour, frame.width, frame.height)

    for ground_truth_index in record["missed_ground_truth_indices"]:
        annotation = record["ground_truth"][ground_truth_index]
        x, y, width, height = annotation["bbox"]
        box = (
            int(x * scale_x),
            int(y * scale_y),
            int((x + width) * scale_x),
            int((y + height) * scale_y),
        )
        colour = brand_colour(annotation["category_id"], categories)
        dashed_rectangle(draw, box, colour, width=6, dash=24, gap=12)
        label = f"Missed · {display_name(annotation['category_id'], categories)}"
        text_chip(draw, (box[0], box[1]), label, colour, frame.width, frame.height)
    return frame


def panel_heading(case_name: str, record: dict) -> tuple[str, str]:
    if case_name == "clear_success":
        title = "Clear success"
    elif case_name == "multi_logo":
        title = "Dense multi-logo frame"
    elif case_name == "difficult_miss":
        title = "Verified small-logo miss"
    else:
        title = "Verified false-positive case"
    metrics = (
        f"GT {len(record['ground_truth'])}   |   TP {record['tp']}   |   "
        f"FP {record['fp']}   |   FN {record['fn']}"
    )
    return title, metrics


def make_figure(cases: list[tuple[str, dict]], categories: dict[int, dict]) -> None:
    canvas_height = (
        OUTER_MARGIN
        + TOP_TITLE_HEIGHT
        + 2 * (PANEL_HEADER_HEIGHT + PANEL_IMAGE_HEIGHT)
        + ROW_GAP
        + FOOTER_HEIGHT
        + OUTER_MARGIN
    )
    canvas = Image.new("RGB", (CANVAS_WIDTH, canvas_height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = font(48, bold=True)
    subtitle_font = font(25)
    panel_title_font = font(31, bold=True)
    panel_metrics_font = font(24)
    panel_letter_font = font(30, bold=True)

    draw.text(
        (OUTER_MARGIN, OUTER_MARGIN - 12),
        "Representative RF-DETR outcomes on the held-out test set",
        font=title_font,
        fill=INK,
    )
    draw.text(
        (OUTER_MARGIN, OUTER_MARGIN + 51),
        "Natural-colour frames; predictions shown at the dissertation operating point",
        font=subtitle_font,
        fill=MUTED,
    )

    start_y = OUTER_MARGIN + TOP_TITLE_HEIGHT
    for index, (case_name, record) in enumerate(cases):
        column = index % 2
        row = index // 2
        x = OUTER_MARGIN + column * (PANEL_WIDTH + GUTTER)
        y = start_y + row * (PANEL_HEADER_HEIGHT + PANEL_IMAGE_HEIGHT + ROW_GAP)
        title, metrics = panel_heading(case_name, record)

        draw.rounded_rectangle(
            (x, y, x + PANEL_WIDTH, y + PANEL_HEADER_HEIGHT + PANEL_IMAGE_HEIGHT),
            radius=16,
            fill="white",
            outline=BORDER,
            width=3,
        )
        draw.rounded_rectangle(
            (x + 1, y + 1, x + PANEL_WIDTH - 1, y + PANEL_HEADER_HEIGHT + 16),
            radius=15,
            fill=LIGHT_SURFACE,
        )
        draw.rectangle(
            (x + 1, y + PANEL_HEADER_HEIGHT - 16, x + PANEL_WIDTH - 1, y + PANEL_HEADER_HEIGHT),
            fill=LIGHT_SURFACE,
        )
        letter = chr(ord("A") + index)
        badge_box = (x + 24, y + 25, x + 72, y + 73)
        badge_centre = (
            (badge_box[0] + badge_box[2]) / 2,
            (badge_box[1] + badge_box[3]) / 2,
        )
        draw.ellipse(badge_box, fill="#E6EEF8")
        draw.text(
            badge_centre,
            letter,
            font=panel_letter_font,
            fill=INK,
            anchor="mm",
        )
        draw.text((x + 90, y + 22), title, font=panel_title_font, fill=INK)
        metric_width = draw.textbbox((0, 0), metrics, font=panel_metrics_font)[2]
        draw.text(
            (x + PANEL_WIDTH - metric_width - 27, y + 31),
            metrics,
            font=panel_metrics_font,
            fill=MUTED,
        )

        annotated = render_annotated_frame(record, categories)
        canvas.paste(annotated, (x, y + PANEL_HEADER_HEIGHT))

    footer_top = canvas_height - OUTER_MARGIN - FOOTER_HEIGHT + 22
    draw.line(
        (OUTER_MARGIN, footer_top - 20, CANVAS_WIDTH - OUTER_MARGIN, footer_top - 20),
        fill=BORDER,
        width=2,
    )
    legend_font = font(24, bold=True)
    x = OUTER_MARGIN
    sample_colours = list(BRAND_COLOURS.values())[:6]
    for index, colour in enumerate(sample_colours):
        left = x + index * 22
        draw.rounded_rectangle(
            (left, footer_top + 3, left + 17, footer_top + 27),
            radius=3,
            fill=colour,
        )
    draw.text((x + 148, footer_top), "Colour = sponsor class", font=legend_font, fill=INK)

    legend_items = [
        ("solid", "Correct prediction"),
        ("short", "FP · false positive"),
        ("long", "Missed · ground truth"),
    ]
    x = OUTER_MARGIN + 690
    for pattern, label in legend_items:
        if pattern == "solid":
            draw.line((x, footer_top + 15, x + 62, footer_top + 15), fill=STATUS_INK, width=7)
        else:
            dash, gap = (10, 7) if pattern == "short" else (24, 12)
            for start in range(x, x + 62, dash + gap):
                draw.line(
                    (start, footer_top + 15, min(start + dash, x + 62), footer_top + 15),
                    fill=STATUS_INK,
                    width=7,
                )
        draw.text((x + 76, footer_top), label, font=legend_font, fill=INK)
        x += 510

    method = (
        "RF-DETR Small  |  selected EMA checkpoint (epoch 36)  |  "
        "confidence >= 0.35  |  IoU >= 0.50"
    )
    method_font = font(24)
    method_width = draw.textbbox((0, 0), method, font=method_font)[2]
    draw.text(
        (CANVAS_WIDTH - OUTER_MARGIN - method_width, footer_top + 68),
        method,
        font=method_font,
        fill=MUTED,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, optimize=True)


def serialisable_case(case_name: str, record: dict) -> dict:
    smallest_missed_area = None
    if record["missed_ground_truth_indices"]:
        smallest_missed_area = min(
            record["ground_truth"][index]["bbox"][2]
            * record["ground_truth"][index]["bbox"][3]
            / (record["width"] * record["height"])
            for index in record["missed_ground_truth_indices"]
        )
    highest_false_positive_score = None
    if record["false_positive_indices"]:
        highest_false_positive_score = max(
            record["predictions"][index]["score"]
            for index in record["false_positive_indices"]
        )
    return {
        "case": case_name,
        "image_id": record["image_id"],
        "file_name": record["file_name"],
        "ground_truth_count": len(record["ground_truth"]),
        "tp": record["tp"],
        "fp": record["fp"],
        "fn": record["fn"],
        "maximum_prediction_confidence": max(
            (prediction["score"] for prediction in record["predictions"]), default=None
        ),
        "highest_false_positive_score": highest_false_positive_score,
        "smallest_missed_relative_area": smallest_missed_area,
        "ground_truth": record["ground_truth"],
        "predictions": record["predictions"],
        "matching": {
            "matches": record["matches"],
            "matched_prediction_indices": record["matched_prediction_indices"],
            "false_positive_indices": record["false_positive_indices"],
            "missed_ground_truth_indices": record["missed_ground_truth_indices"],
        },
    }


def main() -> None:
    if not WEIGHTS.exists():
        raise FileNotFoundError(f"Checkpoint not found: {WEIGHTS}")
    with contextlib.redirect_stdout(io.StringIO()):
        coco = COCO(str(ANNOTATIONS))
    categories = {category["id"]: category for category in coco.loadCats(coco.getCatIds())}
    predictions = run_inference(coco)
    records = build_frame_records(coco, predictions)
    cases = select_cases(records)
    make_figure(cases, categories)

    total_tp = sum(record["tp"] for record in records)
    total_fp = sum(record["fp"] for record in records)
    total_fn = sum(record["fn"] for record in records)
    evidence = {
        "model": "RF-DETR Small",
        "weights": str(WEIGHTS),
        "selected_epoch": SELECTED_EPOCH,
        "split": str(DATASET_DIR),
        "test_images": len(records),
        "confidence": CONFIDENCE,
        "iou_threshold": IOU_THRESHOLD,
        "selection_rules": {
            "clear_success": "Perfect frame with the strongest maximum confidence.",
            "multi_logo": "Largest matched-object count among the remaining perfect frames.",
            "difficult_miss": "Smallest visually verified in-scope kit-logo miss from a frame without an invalid missed annotation.",
            "false_positive": "Highest-confidence frame among visually verified model errors after auditing every unmatched prediction.",
        },
        "false_positive_audit": str(FALSE_POSITIVE_AUDIT),
        "missed_ground_truth_audit": str(MISSED_GROUND_TRUTH_AUDIT),
        "visual_encoding": {
            "colour": "Sponsor class, using the fixed BRAND_COLOURS palette in the generator.",
            "correct_prediction": "Solid box and class-coloured label.",
            "false_positive": "Short-dashed box and label prefixed FP.",
            "missed_ground_truth": "Long-dashed box and label prefixed Missed.",
        },
        "aggregate_operating_point": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
        "cases": [serialisable_case(case_name, record) for case_name, record in cases],
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    print(f"wrote: {OUTPUT}")
    print(f"wrote: {EVIDENCE}")
    print(f"aggregate: TP={total_tp}, FP={total_fp}, FN={total_fn}")
    for case_name, record in cases:
        print(
            f"{case_name}: image {record['image_id']} | GT={len(record['ground_truth'])} "
            f"TP={record['tp']} FP={record['fp']} FN={record['fn']} | {record['file_name']}"
        )


if __name__ == "__main__":
    main()
