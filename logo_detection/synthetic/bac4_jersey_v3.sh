#!/usr/bin/env bash
# bac4_jersey_v3.sh — Kit-aware pipeline: paint (conda) → render (Blender)
# Paints ALL front-panel sponsor logos at authentic UV positions from kit_layout.yaml.
#
# Quick test (1 image, home kit):
#   bash logo_detection/synthetic/bac4_jersey_v3.sh --n 1 --kit home --debug-uv
#
# Full batch (200 images, alternating home/away):
#   bash logo_detection/synthetic/bac4_jersey_v3.sh --n 200 --kit both

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
N=50
KIT="home"
OUT="logo_detection/synthetic/data_bac4_v3"
DEBUG_UV=""
HDRI=""
SIZE=640
SEED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --n)        N="$2";       shift 2 ;;
    --kit)      KIT="$2";    shift 2 ;;
    --out)      OUT="$2";    shift 2 ;;
    --debug-uv) DEBUG_UV="--debug-uv"; shift ;;
    --hdri)     HDRI="$2";   shift 2 ;;
    --size)     SIZE="$2";   shift 2 ;;
    --seed)     SEED="$2";   shift 2 ;;
    *) echo "Unknown arg: $1"; shift ;;
  esac
done

MANIFEST="$ROOT/$OUT/manifest.json"

echo "══════════════════════════════════════"
echo " bac4_jersey_v3  n=$N  kit=$KIT  out=$OUT"
echo "══════════════════════════════════════"
echo ""

# ── Step 1: Paint textures (conda) ───────────────────────────────────────────
echo "[1/2] Sinh textures (conda bradford_bulls)..."
conda run -n bradford_bulls python "$PAINT_SCRIPT" \
  --n "$N" \
  --kit "$KIT" \
  --out "$OUT" \
  --seed "$SEED" \
  $DEBUG_UV

echo ""

# ── Step 2: Render (Blender) ─────────────────────────────────────────────────
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
