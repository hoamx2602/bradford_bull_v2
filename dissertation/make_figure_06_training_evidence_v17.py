"""Build Figure 6 from retained training logs and held-out RF-DETR outputs.

The script reads both W&B run files because training was resumed after epoch 26.
It runs the selected checkpoint on the 61-image match-disjoint test split at the
characterised confidence threshold, constructs an object-detection confusion
matrix, and combines that evidence with the recorded per-class AP@0.50 values.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from PIL import Image
from pycocotools.coco import COCO
from wandb.proto import wandb_internal_pb2
from wandb.sdk.internal.datastore import DataStore


ROOT = Path(r"D:\bradford_bull_v2")
RUN_DIR = ROOT / "runs" / "rfdetr_matchsplit_r896"
DATASET_DIR = ROOT / "datasets" / "auto_label_white_matchsplit" / "test"
ANN_FILE = DATASET_DIR / "_annotations.coco.json"
WEIGHTS = RUN_DIR / "checkpoint_best_total.pth"
EVAL_DUMP = ROOT / "dissertation" / "v16_data" / "eval_dump.json"
OUTPUT_DIR = ROOT / "dissertation" / "LogoLens_MSc_Dissertation_v17_media"
EVIDENCE_DIR = ROOT / "dissertation" / "v17_data"
OUTPUT_FIGURE = OUTPUT_DIR / "figure_07_training_and_heldout_evidence.png"
OUTPUT_PREDICTIONS = EVIDENCE_DIR / "rfdetr_test_predictions_conf035.json"
OUTPUT_SUMMARY = EVIDENCE_DIR / "figure_06_training_evidence.json"

WANDB_RUNS = [
    RUN_DIR / "wandb" / "run-20260810_223114-62qtzisa" / "run-62qtzisa.wandb",
    RUN_DIR / "wandb" / "run-20260810_235105-njzxe4fp" / "run-njzxe4fp.wandb",
]

CONFIDENCE = 0.35
IOU_THRESHOLD = 0.50
SELECTED_EPOCH = 36

NAVY = "#26364A"
BLUE = "#4C78A8"
GREEN = "#5B8E55"
ORANGE = "#E28E3B"
GREY = "#667085"


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


def read_wandb_history(paths: list[Path]) -> list[dict]:
    """Read scalar history directly from retained offline W&B binary logs."""
    records: list[dict] = []
    for path in paths:
        store = DataStore()
        store.open_for_scan(str(path))
        while True:
            payload = store.scan_data()
            if payload is None:
                break
            record = wandb_internal_pb2.Record()
            record.ParseFromString(payload)
            if not record.HasField("history"):
                continue
            row: dict = {}
            for item in record.history.item:
                key = item.key or "/".join(item.nested_key)
                try:
                    row[key] = json.loads(item.value_json)
                except json.JSONDecodeError:
                    row[key] = item.value_json
            records.append(row)
    return records


def training_series(records: list[dict]) -> dict[str, list[float]]:
    """Merge train and validation scalars by epoch across the resume boundary."""
    by_epoch: dict[int, dict[str, float]] = {}
    keep = ("train/loss", "val/loss", "val/mAP_50_95", "val/ema_mAP_50_95")
    for row in records:
        if "epoch" not in row:
            continue
        epoch = int(row["epoch"])
        by_epoch.setdefault(epoch, {})
        for key in keep:
            if key in row:
                by_epoch[epoch][key] = float(row[key])
    epochs = sorted(e for e, values in by_epoch.items() if all(k in values for k in keep))
    return {
        "epoch": epochs,
        "train_loss": [by_epoch[e]["train/loss"] for e in epochs],
        "val_loss": [by_epoch[e]["val/loss"] for e in epochs],
        "val_map": [by_epoch[e]["val/mAP_50_95"] for e in epochs],
        "ema_map": [by_epoch[e]["val/ema_mAP_50_95"] for e in epochs],
    }


def run_inference(coco: COCO) -> list[dict]:
    """Run the final selected RF-DETR checkpoint at the documented threshold."""
    from rfdetr import RFDETRSmall

    model = RFDETRSmall(pretrain_weights=str(WEIGHTS), resolution=896)
    predictions: list[dict] = []
    for image_id in coco.getImgIds():
        info = coco.loadImgs(image_id)[0]
        image = Image.open(DATASET_DIR / info["file_name"]).convert("RGB")
        detections = model.predict(image, threshold=CONFIDENCE)
        for box, class_id, score in zip(
            detections.xyxy, detections.class_id, detections.confidence
        ):
            x1, y1, x2, y2 = (float(v) for v in box)
            predictions.append(
                {
                    "image_id": int(image_id),
                    "category_id": int(class_id),
                    "bbox": [x1, y1, x2 - x1, y2 - y1],
                    "score": float(score),
                }
            )
    return predictions


def bbox_iou(a: list[float], b: list[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    intersection = ix * iy
    union = aw * ah + bw * bh - intersection
    return intersection / (union + 1e-9)


def detection_confusion_matrix(
    coco: COCO, predictions: list[dict], category_ids: list[int]
) -> np.ndarray:
    """Create a detection confusion matrix at the documented operating point.

    Same-class pairs are assigned first by descending IoU, reproducing the
    threshold-specific TP/FP/FN counts. Remaining boxes are then paired without
    a class constraint so that genuine wrong-brand overlaps appear off-diagonal.
    Unmatched ground truth enters the no-object column and unmatched detections
    enter the no-object row.
    """
    category_index = {category_id: i for i, category_id in enumerate(category_ids)}
    no_object = len(category_ids)
    matrix = np.zeros((no_object + 1, no_object + 1), dtype=int)
    predictions_by_image: dict[int, list[dict]] = {}
    for prediction in predictions:
        predictions_by_image.setdefault(prediction["image_id"], []).append(prediction)

    for image_id in coco.getImgIds():
        ground_truth = coco.loadAnns(coco.getAnnIds(imgIds=[image_id]))
        detections = predictions_by_image.get(image_id, [])
        candidates = []
        for gt_index, gt in enumerate(ground_truth):
            for det_index, detection in enumerate(detections):
                overlap = bbox_iou(gt["bbox"], detection["bbox"])
                if overlap >= IOU_THRESHOLD:
                    same_class = gt["category_id"] == detection["category_id"]
                    candidates.append((same_class, overlap, gt_index, det_index))
        used_gt: set[int] = set()
        used_det: set[int] = set()
        for same_class_pass in (True, False):
            for same_class, _, gt_index, det_index in sorted(candidates, reverse=True):
                if same_class != same_class_pass:
                    continue
                if gt_index in used_gt or det_index in used_det:
                    continue
                gt_class = ground_truth[gt_index]["category_id"]
                det_class = detections[det_index]["category_id"]
                if gt_class not in category_index or det_class not in category_index:
                    continue
                matrix[category_index[gt_class], category_index[det_class]] += 1
                used_gt.add(gt_index)
                used_det.add(det_index)
        for gt_index, gt in enumerate(ground_truth):
            if gt_index not in used_gt and gt["category_id"] in category_index:
                matrix[category_index[gt["category_id"]], no_object] += 1
        for det_index, detection in enumerate(detections):
            if det_index not in used_det and detection["category_id"] in category_index:
                matrix[no_object, category_index[detection["category_id"]]] += 1
    return matrix


def style_axis(axis: plt.Axes) -> None:
    axis.set_facecolor("white")
    axis.grid(True, color="#D9D9D9", linewidth=0.7, alpha=0.58)
    axis.set_axisbelow(True)
    for spine in axis.spines.values():
        spine.set_color("#B9B9B9")
        spine.set_linewidth(0.8)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    series = training_series(read_wandb_history(WANDB_RUNS))
    with contextlib.redirect_stdout(io.StringIO()):
        coco = COCO(str(ANN_FILE))
    predictions = run_inference(coco)
    OUTPUT_PREDICTIONS.write_text(
        json.dumps(
            {
                "weights": str(WEIGHTS),
                "split": str(DATASET_DIR),
                "confidence": CONFIDENCE,
                "iou_threshold": IOU_THRESHOLD,
                "predictions": predictions,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    gt_category_ids = {
        annotation["category_id"]
        for annotation in coco.loadAnns(coco.getAnnIds())
    }
    predicted_category_ids = {prediction["category_id"] for prediction in predictions}
    active_category_ids = gt_category_ids | predicted_category_ids
    categories = [
        category
        for category in coco.loadCats(coco.getCatIds())
        if category["name"] != "Auto-Label-White"
        and category["id"] in active_category_ids
    ]
    categories.sort(key=lambda c: c["id"])
    category_ids = [c["id"] for c in categories]
    matrix = detection_confusion_matrix(coco, predictions, category_ids)

    eval_data = json.loads(EVAL_DUMP.read_text(encoding="utf-8"))
    rfdetr = eval_data["models"]["RF-DETR Small"]
    per_class = [
        row
        for row in rfdetr["per_class"]
        if row["name"] != "Auto-Label-White" and row["n"] > 0
    ]

    # One publication-style 2 x 2 figure, with space for panel labels below plots.
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 10.5,
        }
    )
    figure = plt.figure(figsize=(18, 14.2), facecolor="white")
    grid = figure.add_gridspec(
        2,
        2,
        height_ratios=[0.80, 1.35],
        width_ratios=[1.0, 1.0],
        hspace=0.43,
        wspace=0.26,
    )

    # Panel (a): composite loss curves.
    loss_axis = figure.add_subplot(grid[0, 0])
    style_axis(loss_axis)
    loss_axis.plot(series["epoch"], series["train_loss"], color=BLUE, linewidth=1.8, label="Train")
    loss_axis.plot(series["epoch"], series["val_loss"], color=ORANGE, linewidth=1.8, label="Validation")
    loss_axis.axvline(SELECTED_EPOCH, color=GREEN, linewidth=1.5, linestyle=":", label="Selected epoch")
    loss_axis.set_xlabel("Epoch")
    loss_axis.set_ylabel("Loss")
    loss_axis.set_xlim(0, 51)
    loss_axis.set_ylim(0, 38)
    loss_axis.set_xticks([0, 10, 20, 30, 36, 40, 51])
    loss_axis.legend(loc="upper right", frameon=True, fontsize=8.5)
    loss_axis.text(
        0.5,
        -0.25,
        "(a) Composite detection loss",
        transform=loss_axis.transAxes,
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        family="DejaVu Serif",
    )

    # Panel (b): regular and EMA validation metrics used for selection.
    metric_axis = figure.add_subplot(grid[0, 1])
    style_axis(metric_axis)
    metric_axis.plot(series["epoch"], series["val_map"], color=BLUE, linewidth=1.8, label="Validation mAP@[.50:.95]")
    metric_axis.plot(series["epoch"], series["ema_map"], color=ORANGE, linewidth=1.8, label="EMA validation mAP@[.50:.95]")
    metric_axis.axvline(SELECTED_EPOCH, color=GREEN, linewidth=1.5, linestyle=":", label="Selected epoch")
    selected_value = series["ema_map"][series["epoch"].index(SELECTED_EPOCH)]
    metric_axis.scatter([SELECTED_EPOCH], [selected_value], color=GREEN, s=38, zorder=5)
    metric_axis.annotate(
        "epoch 36  |  0.741",
        xy=(SELECTED_EPOCH, selected_value),
        xytext=(26.5, 0.60),
        arrowprops={"arrowstyle": "->", "color": GREEN, "lw": 1.0},
        color=NAVY,
        fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": "#B9B9B9"},
    )
    metric_axis.set_xlabel("Epoch")
    metric_axis.set_ylabel("Metric value")
    metric_axis.set_xlim(0, 51)
    metric_axis.set_ylim(0, 0.80)
    metric_axis.set_xticks([0, 10, 20, 30, 36, 40, 51])
    metric_axis.legend(loc="lower right", frameon=True, fontsize=8.2)
    metric_axis.text(
        0.5,
        -0.25,
        "(b) Validation performance and checkpoint selection",
        transform=metric_axis.transAxes,
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        family="DejaVu Serif",
    )

    # Panel (c): row-normalised object-detection confusion matrix with raw counts.
    matrix_axis = figure.add_subplot(grid[1, 0])
    row_totals = matrix.sum(axis=1, keepdims=True)
    normalised = np.divide(matrix, row_totals, out=np.zeros_like(matrix, dtype=float), where=row_totals != 0)
    cmap = LinearSegmentedColormap.from_list(
        "academic_blue", ["#FFFFFF", "#DCEAF4", "#7CAAC8", "#3D6E9E"]
    )
    matrix_axis.imshow(normalised, cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
    labels = [DISPLAY_NAMES[c["name"]] for c in categories] + ["No object"]
    matrix_axis.set_xticks(range(len(labels)), labels, rotation=52, ha="right", fontsize=7.2)
    matrix_axis.set_yticks(range(len(labels)), labels, fontsize=7.2)
    matrix_axis.set_xlabel("Predicted class")
    matrix_axis.set_ylabel("Ground-truth class")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            count = int(matrix[row, column])
            if count == 0:
                continue
            matrix_axis.text(
                column,
                row,
                str(count),
                ha="center",
                va="center",
                fontsize=7.4,
                color="white" if normalised[row, column] > 0.56 else NAVY,
                fontweight="bold" if row == column else "normal",
            )
    for spine in matrix_axis.spines.values():
        spine.set_color("#B9B9B9")
    matrix_axis.text(
        0.5,
        -0.29,
        "(c) Held-out confusion matrix",
        transform=matrix_axis.transAxes,
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        family="DejaVu Serif",
    )

    # Panel (d): per-brand AP@0.50 with support encoded by colour.
    ap_rows = sorted(
        per_class,
        key=lambda row: row["ap50"],
    )
    brand_labels = [f'{DISPLAY_NAMES[row["name"]]}  (n={row["n"]})' for row in ap_rows]
    values = [float(row["ap50"]) for row in ap_rows]
    colours = [ORANGE if row["n"] < 5 else BLUE for row in ap_rows]
    ap_axis = figure.add_subplot(grid[1, 1])
    style_axis(ap_axis)
    bars = ap_axis.barh(range(len(ap_rows)), values, color=colours, height=0.66)
    ap_axis.set_yticks(range(len(ap_rows)), brand_labels, fontsize=7.8)
    ap_axis.set_xlim(0, 1.04)
    ap_axis.set_xlabel("AP@0.50")
    ap_axis.grid(axis="x", color="#D9D9D9", linewidth=0.7, alpha=0.58)
    ap_axis.grid(axis="y", visible=False)
    ap_axis.axvline(float(rfdetr["map50"]), color=GREEN, linestyle=":", linewidth=1.5)
    ap_axis.text(float(rfdetr["map50"]) - 0.008, len(ap_rows) - 0.10, "mean = 0.933", color=GREEN, ha="right", va="top", fontsize=8.5, fontweight="bold")
    for bar, row, value in zip(bars, ap_rows, values):
        x = min(value + 0.012, 1.005)
        ap_axis.text(x, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=7.4, color=NAVY)
    ap_axis.legend(
        handles=[
            Line2D([0], [0], color=BLUE, lw=7, label="n ≥ 5 boxes"),
            Line2D([0], [0], color=ORANGE, lw=7, label="n < 5 boxes — interpret cautiously"),
        ],
        loc="lower right",
        ncol=2,
        frameon=True,
        fontsize=7.5,
    )
    ap_axis.text(
        0.5,
        -0.18,
        "(d) Per-brand held-out AP@0.50",
        transform=ap_axis.transAxes,
        ha="center",
        va="top",
        fontsize=12,
        fontweight="bold",
        family="DejaVu Serif",
    )

    figure.subplots_adjust(left=0.085, right=0.985, top=0.975, bottom=0.12)
    figure.savefig(OUTPUT_FIGURE, dpi=210, bbox_inches="tight", facecolor="white")
    plt.close(figure)

    summary = {
        "training": {
            "epochs": series["epoch"],
            "initial_train_loss": series["train_loss"][0],
            "final_train_loss": series["train_loss"][-1],
            "initial_val_loss": series["val_loss"][0],
            "final_val_loss": series["val_loss"][-1],
            "selected_epoch": SELECTED_EPOCH,
            "selected_ema_val_map_50_95": series["ema_map"][series["epoch"].index(SELECTED_EPOCH)],
        },
        "held_out": {
            "images": len(coco.getImgIds()),
            "ground_truth_boxes": len(coco.getAnnIds()),
            "predictions_at_confidence_035": len(predictions),
            "map50": rfdetr["map50"],
            "map75": rfdetr["map75"],
            "map50_95": rfdetr["map"],
            "confusion_matrix_labels": labels,
            "confusion_matrix_counts": matrix.tolist(),
        },
    }
    OUTPUT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FIGURE}")
    print(f"Wrote {OUTPUT_PREDICTIONS}")
    print(f"Wrote {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
