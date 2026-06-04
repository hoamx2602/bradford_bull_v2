#!/bin/bash
# Process a video with team detection and generate output video + timeline.
#
# Usage (after running warmup.sh and noting cluster numbers):
#   conda activate <your_env>
#   bash run.sh --video /path/to/video.mp4 --team_a 0 --team_b 1
#   bash run.sh --video /path/to/video.mp4 --team_a 1 --team_b 0 --referee 2 \
#               --team_a_label Bradford --team_b_label HFC \
#               --output_dir output/M02
#
# Options:
#   --video           Path to input video  (required)
#   --team_a          Cluster number for Team A  (required)
#   --team_b          Cluster number for Team B  (required)
#   --referee         Cluster number for Referee  (optional)
#   --team_a_label    Display label for Team A  (default: Bradford)
#   --team_b_label    Display label for Team B  (default: Opponent)
#   --ref_label       Display label for Referee  (default: Referee)
#   --kmeans_model    Path to saved K-means model  (default: output/kmeans_model.pkl)
#   --output_dir      Output directory  (default: output)
#   --conf            YOLO confidence threshold  (default: 0.50)
#   --min_height      Min player height / frame height  (default: 0.07)
#   --smoothing       Majority-vote window in frames  (default: 20)

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python process_video.py "$@"
