"""Build the dissertation DOCX from the Markdown source.

    python md2docx.py [output.docx]

The existing document is used as the style template, so page setup, fonts and
the Heading/normal style definitions carry over unchanged; only the body is
rebuilt from the Markdown.

Markdown supported: ATX headings, paragraphs with **bold** / *italic* /
`code`, pipe tables, block quotes, ordered and unordered lists, horizontal
rules (rendered as page breaks in the front matter), stand-alone images with
their alt text as the caption, and the [[TOC]] directive, which becomes a
real Word table-of-contents field.

An image line must sit on a line of its own with a blank line either side:
the pattern is anchored, so an image sharing a line with text is silently
left as text. The build prints the image count as a check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "LogoLens_MSc_Dissertation.md"
TEMPLATE = ROOT / "LogoLens_MSc_Dissertation_v3.docx"
DEFAULT_OUT = ROOT / "LogoLens_MSc_Dissertation_v4.docx"

TEXT_WIDTH_IN = 6.0
MAX_IMAGE_HEIGHT_IN = 7.0
BODY_STYLE = "normal"

AUTHOR = "MAI XUAN HOA"
TITLE = ("LOGOLENS: A LOW-COST COMPUTER-VISION SYSTEM FOR MEASURING AND "
         "VALUING SPONSOR-LOGO EXPOSURE IN SPORTS BROADCASTS")


# --------------------------------------------------------------------------
# Document scaffolding
# --------------------------------------------------------------------------

def new_document() -> Document:
    doc = Document(TEMPLATE)
    body = doc.element.body
    for child in list(body):
        if child.tag == qn("w:sectPr"):
            continue
        body.remove(child)
    return doc


def para(doc, text="", style=BODY_STYLE, align=None, size=None, bold=None,
         italic=None, space_after=None):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    if text:
        r = p.add_run(text)
        if size is not None:
            r.font.size = Pt(size)
        if bold is not None:
            r.bold = bold
        if italic is not None:
            r.italic = italic
    return p


def page_break(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def toc_field(doc):
    """A real TOC field. Word fills it in on 'Update Field'."""
    p = doc.add_paragraph()
    r = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Right-click and choose “Update Field” to build the table of contents."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for el in (begin, instr, sep, placeholder, end):
        r._r.append(el)


def cover_page(doc):
    """The University of Bradford cover sheet."""
    C = WD_ALIGN_PARAGRAPH.CENTER
    para(doc, align=C)
    para(doc, "UNIVERSITY OF BRADFORD", align=C, size=20, bold=True)
    para(doc, "FACULTY OF MANAGEMENT, SCIENCES AND ENGINEERING", align=C, size=16, bold=True)
    para(doc, align=C)
    para(doc, "MSc Thesis", align=C, size=14, bold=True)
    para(doc, align=C)
    para(doc, AUTHOR, align=C, size=16, bold=True)
    para(doc, align=C)
    para(doc, TITLE, align=C, size=18, bold=True)
    para(doc, align=C)
    para(doc, f"Words: {body_word_count():,}", align=C, size=12)
    page_break(doc)


def body_word_count() -> int:
    """Words in Chapters 1-7, excluding figures, tables and Markdown marks."""
    text = SRC.read_text(encoding="utf-8")
    # Heading punctuation has varied between drafts ("Chapter 1." / "Chapter 1:").
    start = re.search(r"^# Chapter 1[.:] Introduction", text, re.M)
    body = text[start.end():].split("# References", 1)[0] if start else text
    lines = [l for l in body.split("\n")
             if not l.startswith("![") and not l.startswith("|")]
    return len(re.sub(r"[*`#>]", "", "\n".join(lines)).split())


# --------------------------------------------------------------------------
# Inline formatting
# --------------------------------------------------------------------------

INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[\[[^\]]+\]\])")


def add_runs(p, text):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            p.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            r = p.add_run(piece[1:-1])
            r.font.name = "Consolas"
            r.font.size = Pt(9.5)
        elif piece.startswith("*") and piece.endswith("*"):
            p.add_run(piece[1:-1]).italic = True
        else:
            p.add_run(piece)


# --------------------------------------------------------------------------
# Block rendering
# --------------------------------------------------------------------------

IMAGE = re.compile(r"^!\[(.*)\]\(([^)]+)\)$")


def add_image(doc, caption, path, counter):
    src = ROOT / path
    if not src.exists():
        raise SystemExit(f"missing image: {src}")
    with Image.open(src) as im:
        w, h = im.size
    # Fill the text column, unless that would make the image taller than the
    # page allows, in which case fit to height instead.
    width = TEXT_WIDTH_IN
    if width * h / w > MAX_IMAGE_HEIGHT_IN:
        width = MAX_IMAGE_HEIGHT_IN * w / h
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(src), width=Inches(width))
    cap = doc.add_paragraph(style=BODY_STYLE)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(14)
    r = cap.add_run(f"Figure {counter}. ")
    r.bold = True
    r.font.size = Pt(9.5)
    for run_text, italic, bold in split_caption(caption):
        rr = cap.add_run(run_text)
        rr.italic = italic
        rr.bold = bold
        rr.font.size = Pt(9.5)


def split_caption(text):
    for piece in INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            yield piece[2:-2], True, True
        elif piece.startswith("*") and piece.endswith("*"):
            yield piece[1:-1], True, False
        elif piece.startswith("`") and piece.endswith("`"):
            yield piece[1:-1], True, False
        else:
            yield piece, True, False


BORDER_COLOR = "c3c2b7"


def set_table_borders(table):
    """Hairline borders set directly on the table, so the build does not
    depend on a named table style existing in the template."""
    tblPr = table._tbl.tblPr
    for existing in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(existing)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "6")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), BORDER_COLOR)
        borders.append(el)
    tblPr.append(borders)


def add_table(doc, rows):
    header, body_rows = rows[0], rows[1:]
    t = doc.add_table(rows=1, cols=len(header))
    set_table_borders(t)
    is_wide = len(header) >= 10
    t.autofit = not is_wide
    def fill(cell, text, bold=False):
        p = cell.paragraphs[0]
        p.text = ""
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        add_runs(p, text)
        for r in p.runs:
            r.font.size = Pt(6.5 if is_wide else 9.5)
            if bold:
                r.bold = True

    for cell, text in zip(t.rows[0].cells, header):
        fill(cell, text, bold=True)
    for row in body_rows:
        cells = t.add_row().cells
        for cell, text in zip(cells, row):
            fill(cell, text)
    if is_wide:
        first_width = Inches(1.18)
        other_width = Inches((TEXT_WIDTH_IN - 1.18) / (len(header) - 1))
        for cell in t.columns[0].cells:
            cell.width = first_width
        for column_index in range(1, len(header)):
            for cell in t.columns[column_index].cells:
                cell.width = other_width
    doc.add_paragraph(style=BODY_STYLE).paragraph_format.space_after = Pt(6)


def add_list_item(doc, marker, text, align):
    p = doc.add_paragraph(style=BODY_STYLE)
    p.alignment = align
    pf = p.paragraph_format
    pf.left_indent = Inches(0.35)
    pf.first_line_indent = Inches(-0.35)
    pf.space_after = Pt(4)
    p.add_run(f"{marker}\t")
    add_runs(p, text)
    return p


def parse_table_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert():
    global SRC
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    if len(sys.argv) > 2:                 # optional: build from another source
        SRC = Path(sys.argv[2])
    lines = SRC.read_text(encoding="utf-8").split("\n")
    doc = new_document()
    cover_page(doc)

    figure_no = 0
    images_written = 0
    i = 0
    in_front_matter = True
    J = WD_ALIGN_PARAGRAPH.JUSTIFY
    C = WD_ALIGN_PARAGRAPH.CENTER

    # The title block runs until the first horizontal rule.
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i].strip()
        if line:
            text = line.replace("[Insert full name]", AUTHOR)
            p = doc.add_paragraph(style=BODY_STYLE)
            p.alignment = C
            add_runs(p, text)
            if i == 0:
                for r in p.runs:
                    r.bold = True
                    r.font.size = Pt(19)
        i += 1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            if in_front_matter:
                page_break(doc)
            i += 1
            continue

        if stripped == "[[TOC]]":
            toc_field(doc)
            i += 1
            continue

        m = IMAGE.match(stripped)
        if m:
            figure_no += 1
            add_image(doc, m.group(1), m.group(2), figure_no)
            images_written += 1
            i += 1
            continue

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped[level:].strip()
            if text.startswith("Chapter") or text.startswith("References") \
                    or text.startswith("Appendices"):
                page_break(doc)
            if level == 1:
                in_front_matter = False
            h = doc.add_heading(level=min(level, 3))
            add_runs(h, text)
            i += 1
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                if not re.match(r"^\|[\s:|-]+\|$", row):
                    rows.append(parse_table_row(row))
                i += 1
            if rows:
                add_table(doc, rows)
            continue

        if stripped.startswith("> "):
            p = doc.add_paragraph(style=BODY_STYLE)
            p.alignment = J
            p.paragraph_format.left_indent = Inches(0.3)
            add_runs(p, stripped[2:])
            for r in p.runs:
                r.italic = True
                r.font.size = Pt(9.5)
            i += 1
            continue

        # The template carries no list styles, so lists are laid out with a
        # hanging indent and an explicit marker.
        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            add_list_item(doc, f"{m.group(1)}.", m.group(2), J)
            i += 1
            continue

        if stripped.startswith("- "):
            add_list_item(doc, "•", stripped[2:], J)
            i += 1
            continue

        # A standalone italic line directly after a table is its caption.
        p = doc.add_paragraph(style=BODY_STYLE)
        p.alignment = C if re.match(r"^\*Table \d", stripped) else J
        add_runs(p, stripped)
        if p.alignment == C:
            for r in p.runs:
                r.font.size = Pt(9.5)
        i += 1

    doc.save(out)

    expected = sum(1 for l in lines if IMAGE.match(l.strip()))
    check = Document(out)
    print(f"wrote {out.name}")
    print(f"  images: {images_written} written, {expected} in source, "
          f"{len(check.inline_shapes)} embedded")
    print(f"  paragraphs {len(check.paragraphs)}, tables {len(check.tables)}")
    print(f"  body word count on cover: {body_word_count():,}")
    if images_written != expected or len(check.inline_shapes) != expected:
        raise SystemExit("image count mismatch - check for an image line that "
                         "shares a line with text")


if __name__ == "__main__":
    convert()
