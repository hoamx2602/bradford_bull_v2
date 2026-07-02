#!/bin/bash
# Process a video with reference-based team detection.
#
# Usage:
#   conda activate <your_env>
#   bash run.sh --video /path/to/video.mp4 --refs output/refs/team_refs.pkl
#   bash run.sh --video /path/to/video.mp4 --refs output/refs/team_refs.pkl \
#               --team_a_label Bradford --team_b_label HFC \
#               --output_dir output/M02
#
# Build the refs file first:
#   bash ref_build.sh extract --video /path/to/clip.mp4
#   bash ref_build.sh assign  --team_a 3,7,12 --team_b 0,5,9
#
# Options:
#   --video           Path to input video  (required)
#   --refs            Path to team_refs.pkl from ref_build.sh  (required)
#   --team_a_label    Override display label for Team A  (optional)
#   --team_b_label    Override display label for Team B  (optional)
#   --other_label     Override display label for Other  (optional)
#   --output_dir      Output directory  (default: output)
#   --conf            YOLO confidence threshold  (default: 0.50)
#   --min_height      Min player height / frame height  (default: 0.07)
#   --smoothing       Majority-vote window in frames  (default: 20)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python process_video.py "$@"
