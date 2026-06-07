@echo off
REM Install dependencies into conda environment (Windows)
pushd %~dp0

set ENV=%1
if defined ENV (
    echo Installing into conda env: %ENV%
    set "RUN=conda run -n %ENV%"
) else (
    echo Installing into active environment
    set "RUN="
)

%RUN% pip install -r requirements.txt

echo.
echo Installing SAM2 ...
%RUN% pip install git+https://github.com/facebookresearch/sam2.git

echo.
echo Downloading SAM2 large checkpoint (~900 MB) ...
call download_sam2.bat large

echo.
echo === Setup complete ===
echo.
%RUN% python -c "import torch,transformers,umap; print('PyTorch  :', getattr(torch,'__version__',None)); print('CUDA     :', torch.cuda.is_available()); print('Transformers:', transformers.__version__); print('UMAP     :', umap.__version__)"

popd
exit /b 0
