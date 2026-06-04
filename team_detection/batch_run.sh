#!/bin/bash
# Batch process multiple videos using ONE K-means model from warmup.
#
# Edit VIDEO_LIST and cluster assignments below, then:
#   conda activate <your_env>
#   bash batch_run.sh
#
# NOTE: All videos in the list use the SAME cluster assignments.
#       If a video has very different lighting, re-run warmup.sh separately.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
KMEANS_MODEL="output/kmeans_model.pkl"
OUTPUT_BASE="output"

TEAM_A_CLUSTER=0
TEAM_B_CLUSTER=1
REFEREE_CLUSTER=2

TEAM_A_LABEL="Bradford"
TEAM_B_LABEL="Opponent"
REF_LABEL="Referee"

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

echo "Batch processing ${#VIDEO_LIST[@]} video(s)..."
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
        --kmeans_model "$KMEANS_MODEL" \
        --team_a       "$TEAM_A_CLUSTER" \
        --team_b       "$TEAM_B_CLUSTER" \
        --referee      "$REFEREE_CLUSTER" \
        --team_a_label "$TEAM_A_LABEL" \
        --team_b_label "$TEAM_B_LABEL" \
        --ref_label    "$REF_LABEL" \
        --output_dir   "$OUT_DIR" \
        --conf         "$CONF" \
        --min_height   "$MIN_HEIGHT" \
        --smoothing    "$SMOOTHING"

    echo ""
done

echo "All done. Results in: $OUTPUT_BASE/"
