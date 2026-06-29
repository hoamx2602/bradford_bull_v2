"""bac4_v2_paint.py — Bước 1: sinh texture PNG (chạy với conda bradford_bulls).

Với mỗi sample: tạo jersey texture trắng + paste logo ngẫu nhiên tại vị trí chest UV.
Output: thư mục textures/ + manifest.json chứa metadata cho bước render Blender.

Usage:
    conda run -n bradford_bulls python logo_detection/synthetic/bac4_v2_paint.py \\
        --n 50 --logo-dir "Sponsor Logo" --out logo_detection/synthetic/data_bac4_v2
"""

import argparse, json, random, os
from pathlib import Path
from PIL import Image, ImageEnhance

# ── UV chest position (từ phân tích mesh, có thể fine-tune) ─────────────────
UV_CX_DEFAULT = 0.250   # U center của chest logo trong UV space (calibrated via dot test)
UV_CY_DEFAULT = 0.620   # V center (GLTF: V=0=bottom, calibrated via dot test)
UV_W_DEFAULT  = 0.145   # logo width trong UV space (height tỉ lệ AR)
TEX_SIZE = 4096

ap = argparse.ArgumentParser()
ap.add_argument("--n",        type=int,   default=50)
ap.add_argument("--logo-dir", default="Sponsor Logo")
ap.add_argument("--out",      default="logo_detection/synthetic/data_bac4_v2")
ap.add_argument("--seed",     type=int,   default=0)
ap.add_argument("--uv-u",  type=float, default=UV_CX_DEFAULT)
ap.add_argument("--uv-v",  type=float, default=UV_CY_DEFAULT)
ap.add_argument("--uv-w",  type=float, default=UV_W_DEFAULT)
ap.add_argument("--debug-uv", action="store_true", help="vẽ hộp đỏ quanh logo trên texture")
args = ap.parse_args()

ROOT     = Path(__file__).resolve().parent.parent.parent
LOGO_DIR = ROOT / args.logo_dir
OUT_DIR  = ROOT / args.out
TEX_DIR  = OUT_DIR / "textures"
TEX_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "images").mkdir(exist_ok=True)
(OUT_DIR / "labels").mkdir(exist_ok=True)

def _loadable(p):
    try:
        Image.open(p).verify()
        return True
    except Exception:
        return False

LOGO_FILES = [p for p in LOGO_DIR.iterdir()
              if p.suffix.lower() in {".png", ".jpg", ".jpeg"} and _loadable(p)]
if not LOGO_FILES:
    raise RuntimeError(f"Không tìm thấy logo nào trong {LOGO_DIR}")
print(f"[paint] {len(LOGO_FILES)} logos → {args.n} textures")

rng = random.Random(args.seed)
manifest = []

for i in range(args.n):
    s = random.Random(args.seed + i * 1000)

    logo_path = s.choice(LOGO_FILES)
    logo_raw  = Image.open(logo_path).convert("RGBA")
    logo_ar   = logo_raw.width / max(logo_raw.height, 1)
    brand     = logo_path.stem

    uv_w  = args.uv_w * s.uniform(0.75, 1.25)
    uv_cx = args.uv_u + s.uniform(-0.012, 0.012)
    uv_cy = args.uv_v + s.uniform(-0.012, 0.012)
    uv_h  = uv_w / max(logo_ar, 0.05)

    # Jersey base color: trắng với variation nhỏ
    base_c = s.randint(225, 252)
    base   = Image.new("RGB", (TEX_SIZE, TEX_SIZE), (base_c, base_c, base_c))

    # Logo size trên texture (pixel)
    logo_pw = max(int(uv_w * TEX_SIZE), 32)
    logo_ph = max(int(uv_h * TEX_SIZE), 32)
    logo_r  = logo_raw.resize((logo_pw, logo_ph), Image.LANCZOS)
    # Front panel UV V is inverted (high V = jersey bottom): flip logo vertically to compensate
    logo_r  = logo_r.transpose(Image.FLIP_TOP_BOTTOM)

    # UV → PIL pixel: py = (1-V)*TEX_SIZE
    cx_px = int(uv_cx * TEX_SIZE)
    cy_px = int((1 - uv_cy) * TEX_SIZE)
    x0 = cx_px - logo_pw // 2
    y0 = cy_px - logo_ph // 2

    # Paste logo
    base.paste(logo_r, (x0, y0), logo_r.split()[3])

    if args.debug_uv:
        from PIL import ImageDraw
        d = ImageDraw.Draw(base)
        d.rectangle([x0, y0, x0 + logo_pw, y0 + logo_ph], outline=(255, 0, 0), width=12)
        d.line([cx_px - 80, cy_px, cx_px + 80, cy_px], fill=(0, 0, 255), width=8)
        d.line([cx_px, cy_px - 80, cx_px, cy_px + 80], fill=(0, 0, 255), width=8)

    # Mild brightness jitter
    base = ImageEnhance.Brightness(base).enhance(s.uniform(0.88, 1.12))

    tex_file = TEX_DIR / f"{i:05d}.png"
    base.save(str(tex_file), optimize=False)

    manifest.append({
        "idx":       i,
        "tex":       str(tex_file),
        "logo":      str(logo_path),
        "brand":     brand,
        "logo_ar":   logo_ar,
        "uv_cx":     uv_cx,
        "uv_cy":     uv_cy,
        "uv_w":      uv_w,
        "uv_h":      uv_h,
        "jpeg_q":    s.randint(72, 95),
        "tilt_x":    s.uniform(-5, 5),
        "tilt_y":    s.uniform(-12, 12),
        "tilt_z":    s.uniform(-8, 8),
        "cam_seed":  args.seed + i * 1000 + 1,
    })

    if (i + 1) % 10 == 0 or i == args.n - 1:
        print(f"  [{i+1}/{args.n}] {brand}")

manifest_path = OUT_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2))
print(f"\n[paint] Done. Manifest: {manifest_path}")
print(f"[paint] Textures: {TEX_DIR} ({args.n} files)")
