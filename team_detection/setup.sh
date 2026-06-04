#!/bin/bash
# Install requirements into your existing conda environment.
#
# Usage (activate your env first):
#   conda activate <your_env>
#   bash setup.sh
#
# Or specify the env name directly:
#   bash setup.sh myenv

set -e

ENV="${1:-}"

if [ -n "$ENV" ]; then
    echo "Installing into conda env: $ENV"
    conda run -n "$ENV" pip install -r requirements.txt
else
    echo "Installing into active environment: $CONDA_DEFAULT_ENV"
    pip install -r requirements.txt
fi

echo ""
echo "Done. Verify PyTorch + CUDA:"
python -c "import torch; print(f'PyTorch {torch.__version__}  CUDA: {torch.cuda.is_available()}')"
