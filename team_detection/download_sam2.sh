#!/bin/bash
# Download SAM2.1 checkpoints.
# Run once after installing SAM2:
#   pip install git+https://github.com/facebookresearch/sam2.git
#   bash download_sam2.sh          # downloads all sizes
#   bash download_sam2.sh large    # downloads only 'large'

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p checkpoints

SIZE="${1:-all}"
BASE="https://dl.fbaipublicfiles.com/segment_anything_2/092824"

download() {
    local name="$1"
    local url="$BASE/$name"
    if [ -f "checkpoints/$name" ]; then
        echo "Already exists: checkpoints/$name"
    else
        echo "Downloading $name ..."
        wget -q --show-progress -O "checkpoints/$name" "$url"
    fi
}

case "$SIZE" in
    large)  download "sam2.1_hiera_large.pt" ;;
    base+)  download "sam2.1_hiera_base_plus.pt" ;;
    small)  download "sam2.1_hiera_small.pt" ;;
    tiny)   download "sam2.1_hiera_tiny.pt" ;;
    all)
        download "sam2.1_hiera_large.pt"
        download "sam2.1_hiera_base_plus.pt"
        download "sam2.1_hiera_small.pt"
        download "sam2.1_hiera_tiny.pt"
        ;;
    *)
        echo "Usage: bash download_sam2.sh [large|base+|small|tiny|all]"
        exit 1 ;;
esac

echo ""
echo "Done. Checkpoints in: $(ls checkpoints/*.pt 2>/dev/null | tr '\n' ' ')"
