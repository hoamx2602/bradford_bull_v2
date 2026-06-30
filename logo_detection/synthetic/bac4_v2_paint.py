"""bac4_v2_paint.py — Bước 1: sinh texture PNG (chạy với conda bradford_bulls).

Mỗi sample: đọc kit_layout.yaml → paste tất cả sponsor logos ở đúng vị trí UV → ghi manifest.

Usage:
    conda run -n bradford_bulls python logo_detection/synthetic/bac4_v2_paint.py \\
        --n 50 --kit home --out logo_detection/synthetic/data_bac4_v3
"""

import argparse, json, random, yaml
from pathlib import Path
from PIL import Image, ImageEnhance

ap = argparse.ArgumentParser()
ap.add_argument("--n",          type=int,   default=50)
ap.add_argument("--kit",        default="home", choices=["home", "away", "both"])
ap.add_argument("--logo-dir",   default="Sponsor Logo")
ap.add_argument("--layout",     default="logo_detection/synthetic/kit_layout.yaml")
ap.add_argument("--out",        default="logo_detection/synthetic/data_bac4_v3")
ap.add_argument("--seed",       type=int,   default=0)
ap.add_argument("--debug-uv",   action="store_true")
args = ap.parse_args()

TEX_SIZE = 4096
ROOT     = Path(__file__).resolve().parent.parent.parent
LOGO_DIR = ROOT / args.logo_dir
OUT_DIR  = ROOT / args.out
TEX_DIR  = OUT_DIR / "textures"
TEX_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "images").mkdir(exist_ok=True)
(OUT_DIR / "labels").mkdir(exist_ok=True)

layout = yaml.safe_load((ROOT / args.layout).read_text())


def _loadable(p):
    try:
        Image.open(p).verify()
        return True
    except Exception:
        return False


def _load_logo(logo_file):
    p = LOGO_DIR / logo_file
    if not p.exists() or not _loadable(p):
        raise FileNotFoundError(f"Logo not found / corrupt: {p}")
    return Image.open(p).convert("RGBA")


def _paste_logo(base, logo_raw, uv_cx, uv_cy, uv_w, debug=False):
    """Paste logo onto base texture at UV position. Returns (uv_cx, uv_cy, uv_w, uv_h)."""
    logo_ar = logo_raw.width / max(logo_raw.height, 1)
    uv_h    = uv_w / max(logo_ar, 0.05)

    logo_pw = max(int(uv_w * TEX_SIZE), 32)
    logo_ph = max(int(uv_h * TEX_SIZE), 32)
    logo_r  = logo_raw.resize((logo_pw, logo_ph), Image.LANCZOS)
    # Front panel UV V is inverted (high V = jersey bottom): flip logo vertically
    logo_r  = logo_r.transpose(Image.FLIP_TOP_BOTTOM)

    cx_px = int(uv_cx * TEX_SIZE)
    cy_px = int((1 - uv_cy) * TEX_SIZE)
    x0 = cx_px - logo_pw // 2
    y0 = cy_px - logo_ph // 2

    base.paste(logo_r, (x0, y0), logo_r.split()[3])

    if debug:
        from PIL import ImageDraw
        d = ImageDraw.Draw(base)
        d.rectangle([x0, y0, x0 + logo_pw, y0 + logo_ph], outline=(255, 0, 0), width=12)
        d.line([cx_px - 80, cy_px, cx_px + 80, cy_px], fill=(0, 0, 255), width=8)
        d.line([cx_px, cy_px - 80, cx_px, cy_px + 80], fill=(0, 0, 255), width=8)

    return uv_cx, uv_cy, uv_w, uv_h


def make_sample(idx, kit_name, kit_cfg, rng_s):
    slots    = kit_cfg["slots"]
    base_rgb = kit_cfg["jersey_color"]

    # Jersey base with slight color jitter
    base_c = tuple(min(255, max(0, c + rng_s.randint(-10, 10))) for c in base_rgb)
    base   = Image.new("RGB", (TEX_SIZE, TEX_SIZE), base_c)

    logos_meta = []
    for slot in slots:
        try:
            logo_raw = _load_logo(slot["logo_file"])
        except FileNotFoundError as e:
            print(f"  [warn] {e} — skipping slot {slot['brand']}")
            continue

        uv_w  = slot["uv_w"]
        uv_cx = slot["uv_cx"]
        uv_cy = slot["uv_cy"]

        if slot.get("jitter", False):
            uv_w  *= rng_s.uniform(0.85, 1.15)
            uv_cx += rng_s.uniform(-0.008, 0.008)
            uv_cy += rng_s.uniform(-0.008, 0.008)

        uv_cx_out, uv_cy_out, uv_w_out, uv_h_out = _paste_logo(
            base, logo_raw, uv_cx, uv_cy, uv_w, debug=args.debug_uv
        )
        logos_meta.append({
            "brand":  slot["brand"],
            "logo":   str(LOGO_DIR / slot["logo_file"]),
            "uv_cx":  uv_cx_out,
            "uv_cy":  uv_cy_out,
            "uv_w":   uv_w_out,
            "uv_h":   uv_h_out,
        })

    base = ImageEnhance.Brightness(base).enhance(rng_s.uniform(0.88, 1.12))

    tex_file = TEX_DIR / f"{idx:05d}.png"
    base.save(str(tex_file), optimize=False)
    return tex_file, logos_meta


# ── Build sample list ─────────────────────────────────────────────────────────
if args.kit == "both":
    kit_names = ["home", "away"]
else:
    kit_names = [args.kit]

manifest = []
for i in range(args.n):
    rng_s    = random.Random(args.seed + i * 1000)
    kit_name = kit_names[i % len(kit_names)]
    kit_cfg  = layout[kit_name]

    tex_file, logos_meta = make_sample(i, kit_name, kit_cfg, rng_s)

    manifest.append({
        "idx":      i,
        "tex":      str(tex_file),
        "kit":      kit_name,
        "logos":    logos_meta,
        "jpeg_q":   rng_s.randint(72, 95),
        "tilt_x":   rng_s.uniform(-5, 5),
        "tilt_y":   rng_s.uniform(-12, 12),
        "tilt_z":   rng_s.uniform(-8, 8),
        "cam_seed": args.seed + i * 1000 + 1,
    })

    if (i + 1) % 10 == 0 or i == args.n - 1:
        brands = [lg["brand"] for lg in logos_meta]
        print(f"  [{i+1}/{args.n}] {kit_name}: {', '.join(brands)}")

manifest_path = OUT_DIR / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2))
print(f"\n[paint] Done. Manifest: {manifest_path}")
print(f"[paint] Textures: {TEX_DIR} ({args.n} files)")
