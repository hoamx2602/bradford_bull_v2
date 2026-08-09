from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from docx import Document
from PIL import Image, ImageDraw


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def paragraph_text(paragraph) -> str:
    return re.sub(r"\s+", " ", paragraph.text).strip()


def iter_block_items(doc: Document):
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield "paragraph", child
        elif child.tag.endswith("}tbl"):
            yield "table", child


def paragraph_from_element(doc: Document, element):
    from docx.text.paragraph import Paragraph

    return Paragraph(element, doc)


def table_text(element) -> str:
    rows = []
    for row in element.findall(".//w:tr", NS):
        cells = []
        for cell in row.findall("./w:tc", NS):
            texts = [t.text or "" for t in cell.findall(".//w:t", NS)]
            cells.append(" ".join(texts).strip())
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def relationship_targets(docx_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(docx_path) as zf:
        rel_xml = zf.read("word/_rels/document.xml.rels")
    root = ET.fromstring(rel_xml)
    out = {}
    for rel in root.findall("rel:Relationship", NS):
        out[rel.attrib["Id"]] = rel.attrib.get("Target", "")
    return out


def image_order(docx_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml")
    rels = relationship_targets(docx_path)
    root = ET.fromstring(xml)
    images = []
    for idx, drawing in enumerate(root.findall(".//w:drawing", NS), start=1):
        blip = drawing.find(".//a:blip", NS)
        doc_pr = drawing.find(".//wp:docPr", NS)
        rid = blip.attrib.get(f"{{{NS['r']}}}embed") if blip is not None else None
        target = rels.get(rid or "", "")
        images.append(
            {
                "index": idx,
                "rid": rid or "",
                "target": target,
                "name": doc_pr.attrib.get("name", "") if doc_pr is not None else "",
                "descr": doc_pr.attrib.get("descr", "") if doc_pr is not None else "",
            }
        )
    return images


def export_media(docx_path: Path, out_dir: Path) -> list[dict[str, object]]:
    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    records = []
    with zipfile.ZipFile(docx_path) as zf:
        for name in zf.namelist():
            if not name.startswith("word/media/"):
                continue
            dest = media_dir / Path(name).name
            dest.write_bytes(zf.read(name))
            record: dict[str, object] = {"file": str(dest), "source": name}
            try:
                with Image.open(dest) as im:
                    record.update({"width": im.width, "height": im.height, "mode": im.mode})
            except Exception as exc:  # pragma: no cover - diagnostic only
                record["error"] = str(exc)
            records.append(record)
    return records


def make_contact_sheet(media: list[dict[str, object]], out_dir: Path) -> None:
    if not media:
        return
    thumb_w, thumb_h = 260, 190
    image_h = 150
    cols = 3
    rows = (len(media) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (240, 240, 240))
    draw_font = None

    for idx, record in enumerate(media, start=1):
        try:
            image = Image.open(record["file"]).convert("RGB")
        except Exception:
            image = Image.new("RGB", (thumb_w, image_h), (255, 255, 255))
        image.thumbnail((thumb_w, image_h))
        tile = Image.new("RGB", (thumb_w, thumb_h), "white")
        tile.paste(image, ((thumb_w - image.width) // 2, 10))
        draw = ImageDraw.Draw(tile)
        label = f"image{idx} {record.get('width', '?')}x{record.get('height', '?')}"
        draw.text((8, 166), label, fill=(0, 0, 0), font=draw_font)
        sheet.paste(tile, (((idx - 1) % cols) * thumb_w, ((idx - 1) // cols) * thumb_h))

    sheet.save(out_dir / "contact_sheet.jpg", quality=92)


def inspect_docx(docx_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = Document(docx_path)

    blocks = []
    outline = []
    captions = []
    tables = []
    body_paragraphs = []

    for block_index, (kind, element) in enumerate(iter_block_items(doc), start=1):
        if kind == "paragraph":
            p = paragraph_from_element(doc, element)
            text = paragraph_text(p)
            style = p.style.name if p.style is not None else ""
            if not text:
                continue
            rec = {"index": block_index, "kind": kind, "style": style, "text": text}
            blocks.append(rec)
            if style.lower().startswith("heading"):
                outline.append(rec)
            if re.match(r"^(figure|fig\.|table)\s+\d", text, re.I):
                captions.append(rec)
            if style.lower() in {"normal", "body text", "paragraph"} and len(text) > 80:
                body_paragraphs.append(rec)
        else:
            text = table_text(element)
            if text:
                rec = {"index": block_index, "kind": kind, "style": "Table", "text": text}
                blocks.append(rec)
                tables.append(rec)

    images = image_order(docx_path)
    media = export_media(docx_path, out_dir)
    make_contact_sheet(media, out_dir)

    (out_dir / "blocks.json").write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "outline.json").write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "captions.json").write_text(json.dumps(captions, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "images.json").write_text(json.dumps(images, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "media.json").write_text(json.dumps(media, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        f"Document: {docx_path}",
        f"Blocks: {len(blocks)}",
        f"Headings: {len(outline)}",
        f"Captions: {len(captions)}",
        f"Tables: {len(tables)}",
        f"Images in flow: {len(images)}",
        f"Media files: {len(media)}",
        "",
        "OUTLINE",
    ]
    summary_lines += [f"- {h['style']}: {h['text']}" for h in outline]
    summary_lines += ["", "CAPTIONS"]
    summary_lines += [f"- {c['text']}" for c in captions]
    (out_dir / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    parser.add_argument("--out", type=Path, default=Path("dissertation_review"))
    args = parser.parse_args()
    inspect_docx(args.docx, args.out)


if __name__ == "__main__":
    main()
