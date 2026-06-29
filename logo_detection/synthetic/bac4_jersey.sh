#!/usr/bin/env bash
# Bac 4 (P1.5) — jersey + domain randomization.  Chạy trên WSL/Linux.
#
# Basic (procedural sky):
#     bash bac4_jersey.sh --n 8 --out data_bac4_jersey
#
# Full DR (HDRI dir + motion blur):
#     bash bac4_jersey.sh --n 64 --hdri /mnt/c/HDRIs/stadiums \
#         --motion-blur --body-tilt 15 --jpeg-min 65 --out data_bac4_p15
#
# Tải stadium HDRIs miễn phí: https://hdri-haven.com (filter: outdoor/stadium)

BLENDER="${BLENDER:-/mnt/c/Program Files/Blender Foundation/Blender 5.1/blender.exe}"
SCRIPT_LINUX="$(cd "$(dirname "$0")" && pwd)/bac4_jersey.py"
SCRIPT="$(wslpath -w "$SCRIPT_LINUX")"

if [ ! -f "$BLENDER" ]; then
  echo "[error] blender.exe không tìm thấy tại: $BLENDER"
  echo "  Đặt biến env BLENDER trước khi chạy:"
  echo "  BLENDER=/path/to/blender.exe bash bac4_jersey.sh ..."
  exit 1
fi

"$BLENDER" --background --python "$SCRIPT" -- "$@"
