#!/usr/bin/env bash
# bac4_jersey_v2.sh — Pipeline 2 bước: paint (conda) → render (Blender)
#
# Test nhanh (1 ảnh, debug UV box):
#   bash logo_detection/synthetic/bac4_jersey_v2.sh --n 1 --debug-uv
#
# Full batch 50 ảnh:
#   bash logo_detection/synthetic/bac4_jersey_v2.sh --n 50
#
# Với HDRI:
#   bash logo_detection/synthetic/bac4_jersey_v2.sh --n 50 --hdri /mnt/c/HDRIs

set -e

BLENDER="${BLENDER:-/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

PAINT_SCRIPT="$SCRIPT_DIR/bac4_v2_paint.py"
RENDER_SCRIPT="$SCRIPT_DIR/bac4_v2_render.py"
RENDER_SCRIPT_WIN="$(wslpath -w "$RENDER_SCRIPT")"

if [ ! -f "$BLENDER" ]; then
  echo "[error] blender.exe không tìm thấy: $BLENDER"
  exit 1
fi

# ── Parse args ────────────────────────────────────────────────────────────────
N=20
OUT="logo_detection/synthetic/data_bac4_v2"
DEBUG_UV=""
HDRI=""
LOGO_DIR="Sponsor Logo"
SIZE=640
SEED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n)       N="$2";        shift 2 ;;
    --out)     OUT="$2";      shift 2 ;;
    --debug-uv) DEBUG_UV="--debug-uv"; shift ;;
    --hdri)    HDRI="$2";     shift 2 ;;
    --logo-dir) LOGO_DIR="$2"; shift 2 ;;
    --size)    SIZE="$2";     shift 2 ;;
    --seed)    SEED="$2";     shift 2 ;;
    *) echo "Unknown arg: $1"; shift ;;
  esac
done

MANIFEST="$ROOT/$OUT/manifest.json"

echo "══════════════════════════════════════"
echo " bac4_jersey_v2  n=$N  out=$OUT"
echo "══════════════════════════════════════"
echo ""

# ── Bước 1: Paint textures (conda) ───────────────────────────────────────────
echo "[1/2] Sinh textures (conda bradford_bulls)..."
conda run -n bradford_bulls python "$PAINT_SCRIPT" \
  --n "$N" \
  --logo-dir "$LOGO_DIR" \
  --out "$OUT" \
  --seed "$SEED" \
  $DEBUG_UV

echo ""

# ── Bước 2: Render (Blender) ─────────────────────────────────────────────────
echo "[2/2] Render với Blender..."
MANIFEST_WIN="$(wslpath -w "$MANIFEST")"

HDRI_ARG=""
if [ -n "$HDRI" ]; then
  HDRI_ARG="--hdri $(wslpath -w "$HDRI")"
fi

"$BLENDER" --background --python "$RENDER_SCRIPT_WIN" -- \
  --manifest "$MANIFEST_WIN" \
  --size "$SIZE" \
  $HDRI_ARG

echo ""
echo "✓ Done. Output: $ROOT/$OUT"
