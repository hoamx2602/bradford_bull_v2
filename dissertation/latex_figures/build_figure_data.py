"""Build editable LaTeX/PGFPlots data from retained dissertation evidence."""

from __future__ import annotations

import csv
import json
import sys
from colorsys import rgb_to_hsv
from pathlib import Path

from PIL import Image


ROOT = Path(r"D:\bradford_bull_v2")
HERE = ROOT / "dissertation" / "latex_figures"
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT / "dissertation"))
import make_figure_06_training_evidence_v17 as training_figure  # noqa: E402


DISPLAY_NAMES = {
    "aon_home": "Aon",
    "asc_group_home": "ASC Group",
    "atm_home": "ATM",
    "bartercard_home": "Bartercard",
    "chadlaw_home": "Chadlaw",
    "ellgren_home": "Ellgren",
    "em_workwear_home": "EM Workwear",
    "fairway_home": "Fairway",
    "klg_home": "KLG",
    "mcp_home": "MCP",
    "mna_cladding_home": "MNA Cladding",
    "mna_support_service_home": "MNA Support",
    "paints_lacquers_home": "Paints and Lacquers",
    "romantica_home": "Romantica",
    "top_notch_home": "Top Notch",
}


def write_training_csv() -> None:
    series = training_figure.training_series(
        training_figure.read_wandb_history(training_figure.WANDB_RUNS)
    )
    with (DATA / "fig07_training.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["epoch", "train_loss", "val_loss", "val_map", "ema_map"])
        for values in zip(
            series["epoch"],
            series["train_loss"],
            series["val_loss"],
            series["val_map"],
            series["ema_map"],
            strict=True,
        ):
            writer.writerow([values[0], *(f"{value:.8f}" for value in values[1:])])


def write_per_brand_csv() -> None:
    evidence = json.loads(
        (ROOT / "dissertation" / "v16_data" / "eval_dump.json").read_text(
            encoding="utf-8"
        )
    )
    rows = [
        row
        for row in evidence["models"]["RF-DETR Small"]["per_class"]
        if row["name"] != "Auto-Label-White" and row["n"] > 0
    ]
    rows.sort(key=lambda row: row["ap50"])
    with (DATA / "fig07_per_brand.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["index", "brand", "support", "ap50", "sparse"])
        for index, row in enumerate(rows):
            writer.writerow(
                [
                    index,
                    DISPLAY_NAMES[row["name"]],
                    row["n"],
                    f'{row["ap50"]:.8f}',
                    int(row["n"] < 5),
                ]
            )


def write_confusion_cells() -> None:
    summary = json.loads(
        (ROOT / "dissertation" / "v17_data" / "figure_06_training_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    matrix = summary["held_out"]["confusion_matrix_counts"]
    lines = ["% Auto-generated non-zero confusion-matrix cells: x, y, intensity, raw count."]
    size = len(matrix)
    for row_index, row in enumerate(matrix):
        denominator = sum(row) or 1
        y = size - 1 - row_index
        for column_index, count in enumerate(row):
            if not count:
                continue
            intensity = round(15 + 75 * count / denominator)
            lines.append(
                f"\\llcmcell{{{column_index}}}{{{y}}}{{{intensity}}}{{{count}}}"
            )
    (DATA / "fig07_confusion_cells.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_detection_overlays() -> None:
    evidence = json.loads(
        (ROOT / "dissertation" / "v17_data" / "figure_09_detection_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    coco = json.loads(
        (
            ROOT
            / "datasets"
            / "auto_label_white_matchsplit"
            / "test"
            / "_annotations.coco.json"
        ).read_text(encoding="utf-8")
    )
    categories = {row["id"]: row["name"] for row in coco["categories"]}
    palette = {
        "aon_home": "LLAon",
        "asc_group_home": "LLAsc",
        "atm_home": "LLAtm",
        "bartercard_home": "LLBarter",
        "cch_home": "LLCch",
        "chadlaw_home": "LLChadlaw",
        "ellgren_home": "LLEllgren",
        "em_workwear_home": "LLEm",
        "fairway_home": "LLFairway",
        "klg_home": "LLKlg",
        "mcp_home": "LLMcp",
        "mna_cladding_home": "LLMnaClad",
        "mna_support_service_home": "LLMnaSupport",
        "paints_lacquers_home": "LLPaints",
        "romantica_home": "LLRomantica",
        "top_notch_home": "LLTopNotch",
    }
    short = {
        "aon_home": "Aon",
        "asc_group_home": "ASC",
        "atm_home": "ATM",
        "bartercard_home": "Barter",
        "cch_home": "CCH",
        "chadlaw_home": "Chadlaw",
        "ellgren_home": "Ellgren",
        "em_workwear_home": "EM",
        "fairway_home": "Fairway",
        "klg_home": "KLG",
        "mcp_home": "MCP",
        "mna_cladding_home": "MNA-C",
        "mna_support_service_home": "MNA-S",
        "paints_lacquers_home": "P\\&L",
        "romantica_home": "Romantica",
        "top_notch_home": "Top Notch",
    }
    dimensions = {
        "clear_success": (1920, 1080),
        "multi_logo": (1920, 1080),
        "difficult_miss": (1920, 1080),
        "false_positive": (1920, 1080),
    }
    panel_names = {
        "clear_success": "A",
        "multi_logo": "B",
        "difficult_miss": "C",
        "false_positive": "D",
    }
    for case in evidence["cases"]:
        panel = panel_names[case["case"]]
        width, height = dimensions[case["case"]]
        matched = set(case["matching"]["matched_prediction_indices"])
        false_positive = set(case["matching"]["false_positive_indices"])
        missed = set(case["matching"]["missed_ground_truth_indices"])
        lines = [f"% Auto-generated overlays for Figure 9 panel {panel}."]
        for index, prediction in enumerate(case["predictions"]):
            if index not in matched and index not in false_positive:
                continue
            x, y, box_width, box_height = prediction["bbox"]
            category = categories[prediction["category_id"]]
            status = "fp" if index in false_positive else "tp"
            prefix = "FP " if status == "fp" else ""
            label = f'{prefix}{short[category]} {prediction["score"]:.2f}'
            lines.append(
                "\\lldetbox"
                f"{{{x / width:.6f}}}"
                f"{{{1 - (y + box_height) / height:.6f}}}"
                f"{{{(x + box_width) / width:.6f}}}"
                f"{{{1 - y / height:.6f}}}"
                f"{{{palette[category]}}}"
                f"{{{label}}}"
                f"{{{status}}}"
            )
        for index in missed:
            ground_truth = case["ground_truth"][index]
            x, y, box_width, box_height = ground_truth["bbox"]
            category = categories[ground_truth["category_id"]]
            lines.append(
                "\\lldetbox"
                f"{{{x / width:.6f}}}"
                f"{{{1 - (y + box_height) / height:.6f}}}"
                f"{{{(x + box_width) / width:.6f}}}"
                f"{{{1 - y / height:.6f}}}"
                f"{{{palette[category]}}}"
                f"{{Missed {short[category]}}}"
                "{miss}"
            )
        (DATA / f"fig09_{panel}_boxes.tex").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )


def write_timeline_segments() -> None:
    screenshot = Path(
        r"C:\Users\nguye\AppData\Local\Temp\codex-clipboard-f46d96a5-0163-4b00-9598-0f9389ebb94f.png"
    )
    if not screenshot.exists():
        raise FileNotFoundError(screenshot)
    image = Image.open(screenshot).convert("RGB")
    brands = [
        ("Paints and Lacquers", "LLPaints"),
        ("MCP", "LLMcp"),
        ("KLG", "LLKlg"),
        ("Romantica", "LLRomantica"),
        ("Bartercard", "LLBarter"),
        ("Fairway", "LLFairway"),
        ("Floor Tonic", "LLFloorTonic"),
        ("ASC Group", "LLAsc"),
        ("Ellgren", "LLEllgren"),
        ("ATM Hospitality", "LLAtm"),
        ("Aon", "LLAon"),
        ("MNA Support", "LLMnaSupport"),
        ("CCH", "LLCch"),
        ("Chadlaw", "LLChadlaw"),
        ("MNA Cladding", "LLMnaClad"),
        ("EM Workwear", "LLEm"),
        ("Top Notch", "LLTopNotch"),
    ]
    x_origin = 151
    pixels_per_second = 14.7
    lines = [
        "% Auto-generated transcription of the supplied visibility-timeline screenshot.",
        "% Times are recovered from the displayed pixel positions and are illustrative.",
    ]
    for row, (brand, colour) in enumerate(brands):
        y = 47 + 28 * row
        coloured_pixels: list[int] = []
        for x in range(x_origin, 1210):
            if 517 <= x <= 522:  # exclude the red UI playhead
                continue
            red, green, blue = image.getpixel((x, y))
            _, saturation, value = rgb_to_hsv(red / 255, green / 255, blue / 255)
            if saturation > 0.45 and value > 0.35:
                coloured_pixels.append(x)
        runs: list[tuple[int, int]] = []
        if coloured_pixels:
            start = previous = coloured_pixels[0]
            for x in coloured_pixels[1:]:
                if x > previous + 1:
                    if previous - start + 1 >= 3:
                        runs.append((start, previous))
                    start = x
                previous = x
            if previous - start + 1 >= 3:
                runs.append((start, previous))
        lines.append(f"\\lltimelabel{{{row}}}{{{brand}}}{{{colour}}}")
        for start, end in runs:
            start_seconds = (start - x_origin) / pixels_per_second
            end_seconds = (end + 1 - x_origin) / pixels_per_second
            lines.append(
                f"\\llsegment{{{row}}}{{{start_seconds:.2f}}}{{{end_seconds:.2f}}}{{{colour}}}"
            )
    (DATA / "fig10_segments.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    write_training_csv()
    write_per_brand_csv()
    write_confusion_cells()
    write_detection_overlays()
    write_timeline_segments()
    print(f"Wrote LaTeX figure data to {DATA}")


if __name__ == "__main__":
    main()
