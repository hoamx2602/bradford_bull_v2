#!/bin/bash
# Interactive reference builder — extract crops from a clip, select teams in a GUI window.
#
# Usage:
#   conda activate <your_env>
#   bash ref_build.sh --video /path/to/clip.mp4
#   bash ref_build.sh --video /path/to/clip.mp4 --n_frames 30 --output_dir output/refs
#
# A window will open. Click crops to assign them to teams, then press S to save.
#
# Options:
#   --video          Short clip to extract crops from  (required)
#   --output_dir     Where to save team_refs.pkl  (default: output/refs)
#   --n_frames       Frames to sample  (default: 25)
#   --conf           YOLO confidence threshold  (default: 0.50)
#   --min_height     Min bbox height / frame height  (default: 0.07)
#   --max_iou        Max IoU to keep isolated crops  (default: 0.25)
#   --team_a_label   Display label for Team A  (default: Bradford)
#   --team_b_label   Display label for Team B  (default: Opponent)
#   --other_label    Display label for Other  (default: Other)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python ref_build.py "$@"
