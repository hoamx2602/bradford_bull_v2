"""Render the qualitative detection and team-attribution figures.

Detection figures. The framework's validation mosaic tiles four frames into one
1920x1078 image, leaving each mark a few dozen pixels across with the text
labels overlapping. The predictions in it are the same ones this script
produces - checked frame by frame, the counts match - but they cannot be read.
This re-runs the same clip-disjoint weights at deployment resolution and
renders one frame per figure.

Boxes are coloured by brand rather than numbered, because the same sponsor
appears several times in a frame and a colour groups those repeats at a glance
where a running number would not. Colour alone cannot carry identity for six
categories - no six-colour set clears the all-pairs separation checks - so each
box also carries a short brand label, and the legend gives the full mapping.

Held-out status: the clip-disjoint validation clips are read off the mosaic
headers (clip_002_00-32, clip_040_10-57, clip_042_10-51); the first and third
are present in the local export, so every frame used here was unseen during
training of these weights. Frames were chosen by detection count and by image
sharpness, measured as the Laplacian variance of the frame.

    python make_detection_figures.py
"""
from __future__ import annotations

import glob
import os
from collections import defaultdict
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FIG = ROOT / "figures"
REPO = ROOT.parent
WEIGHTS = REPO / "logo_detection" / "runs" / "logo_yolo26m_clipsplit" / "weights" / "best.pt"
DATA = REPO / "training-result" / "data"
TEAMDET = REPO / "backend" / "data" / "uploads" / "ab08a6d4e29e4e2aa28a0a8fe1a5858e.mp4"

# frame stem -> output name. Picked by detection count then sharpness.
FRAMES = {
    "clip_042_10-51_0000030_t00001000ms": "fig_detect_a.png",
    "clip_002_00-32_0000060_t00002000ms": "fig_detect_b.png",
    "clip_002_00-32_0000090_t00003000ms": "fig_detect_c.png",
}

CONF, IMGSZ = 0.25, 1280

# One colour per brand, fixed across every figure so a sponsor keeps its colour.
BRAND_COLOUR = {
    "klg": (42, 120, 214),              # blue
    "paints_lacquers": (235, 104, 52),  # orange
    "mcp": (237, 161, 0),               # yellow
    "acs_group": (74, 58, 167),         # violet
    "aon": (27, 175, 122),              # aqua
    "bartercard": (232, 123, 164),      # magenta
    "atm": (227, 73, 72),               # red
    "ellgren": (0, 131, 0),             # green
}
FALLBACK = (120, 120, 120)

DISPLAY = {
    "klg": "KLG", "mcp": "MCP", "aon": "Aon", "atm": "ATM",
    "acs_group": "ACS Group", "paints_lacquers": "Paints & Lacquers",
    "bartercard": "Bartercard", "ellgren": "Ellgren", "romantica": "Romantica",
    "chadlaw": "Chadlaw", "top_notch": "Top Notch", "floor_tonic": "Floor Tonic",
    "em_workwear": "EM Workwear", "fairway": "Fairway", "cch": "CCH",
    "mna_cladding": "MNA Cladding", "mna_support_service": "MNA Support",
}

INK, SURFACE = (11, 11, 11), (255, 255, 255)
REDACT = [
    (0.00, 0.00, 0.32, 0.13),  # score/clock when carried at top-left
    (0.78, 0.00, 1.00, 0.13),  # broadcaster mark / score at top-right
    (0.00, 0.82, 0.24, 1.00),  # score/clock when carried at bottom-left
]
FEATHER = 12


def font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def brand_of(cls_name):
    return cls_name.rsplit("_", 1)[0] if cls_name.endswith(("_home", "_away")) else cls_name


def redact(im):
    blurred = im.filter(ImageFilter.GaussianBlur(20))
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    W, H = im.size
    for fx0, fy0, fx1, fy1 in REDACT:
        md.rectangle([int(W * fx0), int(H * fy0), int(W * fx1), int(H * fy1)], fill=255)
    im.paste(blurred, (0, 0), mask.filter(ImageFilter.GaussianBlur(FEATHER)))
    return im


def halo_text(d, xy, text, f, fill):
    """Text with a white halo, so it reads over grass or a dark kit alike."""
    x, y = xy
    for dx in (-2, 0, 2):
        for dy in (-2, 0, 2):
            if dx or dy:
                d.text((x + dx, y + dy), text, font=f, fill=SURFACE)
    d.text((x, y), text, font=f, fill=fill)


def render(src, boxes, out):
    """boxes: (x1, y1, x2, y2, brand, conf)."""
    im = redact(Image.open(src).convert("RGB"))
    W, H = im.size
    d = ImageDraw.Draw(im)
    f_conf = font(34)

    # A plain coloured box per detection, with its own confidence beside it.
    # The brand is carried by the colour and decoded in the legend beneath;
    # writing the brand on the box as well makes the chips overlap and cover
    # the very boxes they describe once a frame holds nine marks.
    for x1, y1, x2, y2, brand, conf in sorted(boxes, key=lambda b: b[1]):
        col = BRAND_COLOUR.get(brand, FALLBACK)
        pad = 5
        d.rectangle([x1 - pad, y1 - pad, x2 + pad, y2 + pad], outline=col, width=6)

        txt = f"{conf:.2f}"
        tb = d.textbbox((0, 0), txt, font=f_conf)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        # Above the box by preference, below it when that would leave the frame.
        tx = min(max(x1 - pad, 4), W - tw - 6)
        ty = y1 - pad - th - 12
        if ty < 4:
            ty = y2 + pad + 6
        halo_text(d, (tx, ty), txt, f_conf, col)

    # Legend: colour to brand only. Per-detection confidence is on the frame.
    per = defaultdict(list)
    for *_, brand, conf in boxes:
        per[brand].append(conf)
    order = sorted(per, key=lambda b: (-len(per[b]), -max(per[b])))

    f_leg = font(44)
    cols = 2
    rows = (len(order) + cols - 1) // cols
    pad, line = 30, 68
    sheet = Image.new("RGB", (W, H + rows * line + 2 * pad), SURFACE)
    sheet.paste(im, (0, 0))
    dl = ImageDraw.Draw(sheet)
    colw = W // cols
    for i, brand in enumerate(order):
        cx = pad + (i % cols) * colw
        cy = H + pad + (i // cols) * line
        # The swatch is the whole key now, so it matches the box weight.
        dl.rounded_rectangle([cx, cy + 4, cx + 52, cy + 44], radius=7,
                             fill=BRAND_COLOUR.get(brand, FALLBACK),
                             outline=(120, 120, 120), width=2)
        dl.text((cx + 70, cy + 4), DISPLAY.get(brand, brand), font=f_leg, fill=INK)

    sheet.save(out, quality=93)
    print(f"  wrote {out.name}  ({sheet.width}x{sheet.height}, "
          f"{len(boxes)} detections, {len(order)} brands)")


def find(stem):
    for split in ("train", "valid", "test"):
        hits = glob.glob(str(DATA / split / (stem + "*")))
        if hits:
            return hits[0]
    raise SystemExit(f"frame not found: {stem}")


def detection_figures():
    from ultralytics import YOLO
    model = YOLO(str(WEIGHTS))
    for stem, outname in FRAMES.items():
        src = find(stem)
        r = model.predict(src, imgsz=IMGSZ, conf=CONF, device="cpu", verbose=False)[0]
        boxes = [(*(float(v) for v in b.xyxy[0]),
                  brand_of(model.names[int(b.cls)]), float(b.conf)) for b in r.boxes]
        render(src, boxes, FIG / outname)


def team_figure(second=9.6, out="fig_team_attribution.png"):
    """A frame from the pipeline's own team-detection overlay.

    The overlay is rendered at 960x540, so the frame is shown whole for context
    with a magnified crop of the contested area beneath, where the per-player
    TARGET / OTHER decisions are legible.
    """
    cap = cv2.VideoCapture(str(TEAMDET))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(second * fps))
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("could not read the team-detection overlay")

    im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    W, H = im.size

    full = im.resize((1600, int(H * 1600 / W)), Image.LANCZOS)
    dfull = ImageDraw.Draw(full, "RGBA")
    # The overlay's own key sits top-left and renders illegibly once scaled, so
    # it is covered by an opaque card and redrawn at figure resolution.
    dfull.rectangle([0, 0, 430, 150], fill=(255, 255, 255, 235))
    f_key = font(30)
    for i, (col, text) in enumerate([((247, 181, 41), "TARGET team"),
                                     ((216, 216, 216), "Other / officials"),
                                     ((77, 208, 225), "Undecided")]):
        y = 18 + i * 42
        dfull.rounded_rectangle([20, y, 54, y + 30], radius=5, fill=col,
                                outline=(70, 70, 70), width=2)
        dfull.text((66, y - 2), text, font=f_key, fill=(20, 20, 20))

    # Magnify the defensive line, where the TARGET / OTHER decisions sit side
    # by side. The crop starts right of the legend so it is not shown twice.
    crop = im.crop((int(W * 0.28), int(H * 0.36), int(W * 0.78), int(H * 0.86)))
    zoom = crop.resize((1600, int(crop.height * 1600 / crop.width)), Image.LANCZOS)

    gap = 18
    sheet = Image.new("RGB", (1600, full.height + gap + zoom.height), SURFACE)
    sheet.paste(full, (0, 0))
    sheet.paste(zoom, (0, full.height + gap))
    d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, 1599, full.height - 1], outline=(200, 200, 195), width=2)
    d.rectangle([0, full.height + gap, 1599, sheet.height - 1],
                outline=(200, 200, 195), width=2)
    sheet.save(FIG / out, quality=93)
    print(f"  wrote {out}  ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    detection_figures()
    team_figure()
