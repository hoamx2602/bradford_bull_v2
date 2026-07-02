#!/bin/bash
# Warm-up: sample frames → extract shirt colours → fit K-means → save model + cluster image.
#
# Usage:
#   conda activate <your_env>
#   bash warmup.sh --video /path/to/video.mp4
#   bash warmup.sh --video /path/to/video.mp4 --output_dir output/M02 --n_clusters 3
#
# Options:
#   --video           Path to input video  (required)
#   --output_dir      Where to save model + cluster image  (default: output)
#   --n_clusters      Number of K-means clusters  (default: 3)
#   --warmup_frames   Frames to sample  (default: 50)
#   --conf            YOLO confidence threshold  (default: 0.50)
#   --min_height      Min player height / frame height  (default: 0.07)
#
# After running, open output/shirt_clusters.png, then assign clusters with run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python warmup.py "$@"
