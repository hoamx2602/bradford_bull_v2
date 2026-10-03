"""Render held-out frame contact sheets for manual occlusion-example selection."""

from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from pycocotools.coco import COCO


ROOT = Path(r"D:\bradford_bull_v2")
DATASET = ROOT / "datasets" / "auto_label_white_matchsplit" / "test"
ANNOTATIONS = DATASET / "_annotations.coco.json"
OUTPUT_DIR = ROOT / "dissertation" / "v17_data" / "occlusion_frame_search"
CANDIDATE_IMAGE_IDS = [7, 16, 23, 28, 37, 57, 61]

THUMBNAIL = (560, 315)
COLUMNS = 3
ROWS = 7
MARGIN = 34
GAP = 24
TITLE_HEIGHT = 58
INK = "#172033"
BORDER = "#CBD5E1"
BOX = "#E45756"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"
    return ImageFont.truetype(path, size=size)


def context_crop(source: Image.Image, bbox: list[float]) -> Image.Image:
    x, y, width, height = bbox
    centre_x = x + width / 2
    centre_y = y + height / 2
    side = max(max(width, height) * 3.6, 210)
    crop_width = min(side * 1.35, source.width)
    crop_height = min(side, source.height)
    left = min(max(0, centre_x - crop_width / 2), source.width - crop_width)
    top = min(max(0, centre_y - crop_height / 2), source.height - crop_height)
    right = left + crop_width
    bottom = top + crop_height
    crop = source.crop((int(left), int(top), int(right), int(bottom)))
    size = (430, 318)
    crop = crop.resize(size, Image.Resampling.LANCZOS)
    scale_x = size[0] / crop_width
    scale_y = size[1] / crop_height
    projected = (
        int((x - left) * scale_x),
        int((y - top) * scale_y),
        int((x + width - left) * scale_x),
        int((y + height - top) * scale_y),
    )
    ImageDraw.Draw(crop).rectangle(projected, outline=BOX, width=5)
    return crop


def render_annotation_candidates(coco: COCO) -> None:
    categories = {row["id"]: row["name"] for row in coco.loadCats(coco.getCatIds())}
    items: list[dict] = []
    for image_id in CANDIDATE_IMAGE_IDS:
        info = coco.loadImgs(image_id)[0]
        for annotation in coco.loadAnns(coco.getAnnIds(imgIds=[image_id])):
            if annotation["category_id"] == 0:
                continue
            items.append({"image": info, "annotation": annotation})

    columns = 4
    tile_width, tile_height = 460, 382
    rows = math.ceil(len(items) / columns)
    canvas = Image.new(
        "RGB",
        (2 * MARGIN + columns * tile_width + (columns - 1) * GAP,
         2 * MARGIN + 72 + rows * tile_height + (rows - 1) * GAP),
        "white",
    )
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (MARGIN, MARGIN - 4),
        "Candidate held-out logo crops for occlusion review",
        font=font(34, bold=True),
        fill=INK,
    )
    rows_json: list[dict] = []
    for index, item in enumerate(items):
        info = item["image"]
        annotation = item["annotation"]
        source = Image.open(DATASET / info["file_name"]).convert("RGB")
        crop = context_crop(source, annotation["bbox"])
        column = index % columns
        row = index // columns
        x = MARGIN + column * (tile_width + GAP)
        y = MARGIN + 72 + row * (tile_height + GAP)
        draw.rounded_rectangle(
            (x, y, x + tile_width, y + tile_height),
            radius=10,
            fill="#F8FAFC",
            outline=BORDER,
            width=2,
        )
        class_name = categories[annotation["category_id"]]
        draw.text(
            (x + 12, y + 10),
            f"image {info['id']:02d}  |  ann {annotation['id']}  |  {class_name}",
            font=font(19, bold=True),
            fill=INK,
        )
        canvas.paste(crop, (x + 15, y + 51))
        rows_json.append(
            {
                "image_id": info["id"],
                "file_name": info["file_name"],
                "annotation_id": annotation["id"],
                "category_id": annotation["category_id"],
                "class_name": class_name,
                "bbox": annotation["bbox"],
            }
        )
    output = OUTPUT_DIR / "candidate_logo_crops.png"
    output_json = OUTPUT_DIR / "candidate_logo_crops.json"
    canvas.save(output, optimize=True)
    output_json.write_text(json.dumps(rows_json, indent=2), encoding="utf-8")
    print(f"wrote: {output}")
    print(f"wrote: {output_json}")


def main() -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        coco = COCO(str(ANNOTATIONS))
    images = sorted(coco.loadImgs(coco.getImgIds()), key=lambda row: row["id"])
    per_page = COLUMNS * ROWS
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for page_index in range(math.ceil(len(images) / per_page)):
        subset = images[page_index * per_page : (page_index + 1) * per_page]
        width = 2 * MARGIN + COLUMNS * THUMBNAIL[0] + (COLUMNS - 1) * GAP
        height = 2 * MARGIN + 72 + ROWS * (TITLE_HEIGHT + THUMBNAIL[1]) + (ROWS - 1) * GAP
        canvas = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (MARGIN, MARGIN - 4),
            f"Held-out frame search for occlusion examples — page {page_index + 1}",
            font=font(34, bold=True),
            fill=INK,
        )

        for offset, info in enumerate(subset):
            column = offset % COLUMNS
            row = offset // COLUMNS
            x = MARGIN + column * (THUMBNAIL[0] + GAP)
            y = MARGIN + 72 + row * (TITLE_HEIGHT + THUMBNAIL[1] + GAP)
            frame = Image.open(DATASET / info["file_name"]).convert("RGB")
            thumbnail = ImageOps.fit(frame, THUMBNAIL, method=Image.Resampling.LANCZOS)
            annotation_count = len(coco.getAnnIds(imgIds=[info["id"]]))
            camera = next(
                (token.removeprefix("cam-") for token in info["file_name"].split("__") if token.startswith("cam-")),
                "unknown",
            )
            draw.rounded_rectangle(
                (x, y, x + THUMBNAIL[0], y + TITLE_HEIGHT + THUMBNAIL[1]),
                radius=12,
                fill="#F8FAFC",
                outline=BORDER,
                width=2,
            )
            draw.text(
                (x + 16, y + 13),
                f"image {info['id']:02d}  |  {camera}  |  GT {annotation_count}",
                font=font(23, bold=True),
                fill=INK,
            )
            canvas.paste(thumbnail, (x, y + TITLE_HEIGHT))

        output = OUTPUT_DIR / f"heldout_frames_page_{page_index + 1}.png"
        canvas.save(output, optimize=True)
        print(f"wrote: {output}")
    render_annotation_candidates(coco)


if __name__ == "__main__":
    main()
