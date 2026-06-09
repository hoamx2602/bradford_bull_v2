#!/bin/bash
# Install all dependencies into your existing conda environment.
#
# Usage:
#   conda activate bradford_bulls
#   bash setup.sh
#
# Or specify env name:
#   bash setup.sh bradford_bulls

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV="${1:-}"
RUN=""
if [ -n "$ENV" ]; then
    echo "Installing into conda env: $ENV"
    RUN="conda run -n $ENV"
else
    echo "Installing into active environment: $CONDA_DEFAULT_ENV"
fi

# ── Core requirements ──────────────────────────────────────────────────────
$RUN pip install -r requirements.txt

# ── SAM2 ──────────────────────────────────────────────────────────────────
echo ""
echo "Installing SAM2 real-time fork ..."
$RUN pip install git+https://github.com/Gy920/segment-anything-2-real-time.git --no-build-isolation

# ── Download SAM2 checkpoints ─────────────────────────────────────────────
echo ""
echo "Downloading SAM2 large checkpoint (~900 MB) ..."
bash download_sam2.sh large

echo ""
echo "=== Setup complete ==="
echo ""
$RUN python -c "
import torch
print(f'PyTorch  : {torch.__version__}')
print(f'CUDA     : {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU      : {torch.cuda.get_device_name(0)}')
    print(f'VRAM     : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')

import transformers; print(f'Transformers: {transformers.__version__}')
import umap;         print(f'UMAP     : {umap.__version__}')
try:
    from sam2.build_sam import build_sam2_camera_predictor
    print('SAM2     : OK (camera predictor)')
except ImportError as e:
    print(f'SAM2     : NOT FOUND ({e})')
"
