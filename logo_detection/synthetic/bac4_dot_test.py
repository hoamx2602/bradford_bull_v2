"""bac4_dot_test.py — Calibration: paint a 3×3 colored-square grid on the jersey UV
and write a 1-item manifest so the render step can produce a diagnostic image.

The 9 squares cover candidate positions for the front-panel sponsor slots.
Inspect the rendered image to read off which UV → which visual location.

Usage (conda env):
    conda run -n bradford_bulls python logo_detection/synthetic/bac4_dot_test.py \
        --out logo_detection/synthetic/data_bac4_dottest
"""

import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="logo_detection/synthetic/data_bac4_dottest")
ap.add_argument("--cam-seed", type=int, default=42, help="fixed camera seed for reproducibility")
args = ap.parse_args()

ROOT    = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / args.out
TEX_DIR = OUT_DIR / "textures"
TEX_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "images").mkdir(exist_ok=True)
(OUT_DIR / "labels").mkdir(exist_ok=True)

TEX_SIZE = 4096

# ── 3×3 grid of candidate UV positions ──────────────────────────────────────
# U direction: normal (low=left, high=right)
# V direction: INVERTED in render (high V = bottom of jersey)
# cy_px in PIL = (1 - V) * TEX_SIZE

GRID = [
    # (U,   V,     color_RGB,       label)
    (0.200, 0.535, (255,  20,  20), "A: U.200 V.535"),
    (0.250, 0.535, ( 20, 200,  20), "B: U.250 V.535"),
    (0.295, 0.535, ( 20,  20, 255), "C: U.295 V.535"),
    (0.200, 0.620, (255, 165,   0), "D: U.200 V.620"),
    (0.250, 0.620, (255,   0, 255), "E: U.250 V.620"),  # known calibrated chest
    (0.295, 0.620, (  0, 220, 220), "F: U.295 V.620"),
    (0.200, 0.710, (255, 255,   0), "G: U.200 V.710"),
    (0.250, 0.710, (160,  32, 240), "H: U.250 V.710"),
    (0.295, 0.710, (128, 200,   0), "I: U.295 V.710"),
]

SQ = 220  # square side in px

base = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (230, 230, 230))
draw = ImageDraw.Draw(base)

for (u, v, color, label) in GRID:
    cx = int(u * TEX_SIZE)
    cy = int((1 - v) * TEX_SIZE)
    x0, y0 = cx - SQ // 2, cy - SQ // 2
    x1, y1 = cx + SQ // 2, cy + SQ // 2
    draw.rectangle([x0, y0, x1, y1], fill=color)
    # white border so squares are findable even on similar background
    draw.rectangle([x0, y0, x1, y1], outline=(255, 255, 255), width=10)
    # label text inside the square
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", 60)
    except Exception:
        font = ImageFont.load_default()
    draw.text((x0 + 15, y0 + 15), label[0], fill=(255, 255, 255), font=font)

tex_file = TEX_DIR / "dottest.png"
base.save(str(tex_file))
print(f"[dot_test] Texture → {tex_file}")

# Write manifest for a single fixed-angle render
manifest = [{
    "idx":      0,
    "tex":      str(tex_file),
    "logo":     "diagnostic",
    "brand":    "dottest",
    "logo_ar":  1.0,
    "uv_cx":    0.250,
    "uv_cy":    0.620,
    "uv_w":     0.0,
    "uv_h":     0.0,
    "jpeg_q":   95,
    "tilt_x":   0,
    "tilt_y":   0,
    "tilt_z":   0,
    "cam_seed": args.cam_seed,
}]

mpath = OUT_DIR / "manifest.json"
mpath.write_text(json.dumps(manifest, indent=2))
print(f"[dot_test] Manifest → {mpath}")
print("[dot_test] Run Blender next, then inspect images/00000.jpg")
print("\nColor legend:")
for u, v, color, label in GRID:
    print(f"  {label}  RGB={color}")
