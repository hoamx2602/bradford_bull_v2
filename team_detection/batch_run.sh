#!/bin/bash
# Batch process multiple videos using ONE reference model from ref_build.sh.
#
# Edit VIDEO_LIST and configuration below, then:
#   conda activate <your_env>
#   bash batch_run.sh
#
# NOTE: All videos use the SAME refs file.
#       If a video has very different lighting, re-run ref_build.sh separately.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
REFS_PATH="output/refs/team_refs.pkl"
OUTPUT_BASE="output"

TEAM_A_LABEL="Bradford"
TEAM_B_LABEL="Opponent"
OTHER_LABEL="Other"

CONF=0.50
MIN_HEIGHT=0.07
SMOOTHING=20

# >>> ADD YOUR VIDEO PATHS HERE <<<
VIDEO_LIST=(
    "/path/to/clip_001.mp4"
    "/path/to/clip_002.mp4"
    "/path/to/clip_003.mp4"
)
# ── END CONFIGURATION ─────────────────────────────────────────────────────────

echo "Batch processing ${#VIDEO_LIST[@]} video(s) using refs: $REFS_PATH"
echo ""

for VIDEO in "${VIDEO_LIST[@]}"; do
    if [ ! -f "$VIDEO" ]; then
        echo "SKIP (not found): $VIDEO"
        continue
    fi

    STEM=$(basename "$VIDEO" | sed 's/\.[^.]*$//')
    OUT_DIR="$OUTPUT_BASE/$STEM"
    echo "── Processing: $STEM ──────────────────────────"

    python process_video.py \
        --video        "$VIDEO" \
        --refs         "$REFS_PATH" \
        --team_a_label "$TEAM_A_LABEL" \
        --team_b_label "$TEAM_B_LABEL" \
        --other_label  "$OTHER_LABEL" \
        --output_dir   "$OUT_DIR" \
        --conf         "$CONF" \
        --min_height   "$MIN_HEIGHT" \
        --smoothing    "$SMOOTHING"

    echo ""
done

echo "All done. Results in: $OUTPUT_BASE/"
