@echo off
REM Install dependencies into conda environment (Windows)
pushd %~dp0

set ENV=%1
if defined ENV (
    echo Installing into conda env: %ENV%
    call conda activate %ENV% || (
        echo Failed to activate conda environment %ENV%. Ensure conda is installed and initialized in this shell.
        popd
        exit /b 1
    )
) else (
    echo Installing into active environment: %CONDA_DEFAULT_ENV%
)

echo.
if exist "%ProgramFiles%\Git\cmd\git.exe" (
    echo Adding Git for Windows to PATH
    set "PATH=%ProgramFiles%\Git\cmd;%ProgramFiles%\Git\mingw64\bin;%PATH%"
) else (
    echo Git for Windows not found in %ProgramFiles%\Git\cmd. Make sure Git is installed and on PATH.
)

echo.
echo Checking Git availability from Python...
python -c "import shutil; print('python sees git:', shutil.which('git'))"

echo.
echo Installing core requirements (using active Python)...
python -m pip install -r requirements.txt

if exist sam2\setup.py (
    goto :install_local_sam2
) else (
    goto :install_git_sam2
)

:install_local_sam2
echo.
echo Found local sam2 clone; installing from local folder.
python -m pip install .\sam2
if errorlevel 1 (
    echo SAM2 local install failed.
    popd
    exit /b 1
)
goto :download_checkpoints

:install_git_sam2
echo.
echo Installing SAM2 real-time fork from GitHub (requires git)...
python -m pip install git+https://github.com/Gy920/segment-anything-2-real-time.git --no-build-isolation
if errorlevel 1 (
    echo SAM2 real-time fork install failed.
    popd
    exit /b 1
)
goto :download_checkpoints

:download_checkpoints
echo.
echo Downloading SAM2 large checkpoint (~900 MB) ...
call download_sam2.bat large
if errorlevel 1 (
    echo download_sam2.bat failed.
    popd
    exit /b 1
)

echo.
echo === Setup complete ===
echo.
python -c "exec('try:\n import torch\n print(\"PyTorch  :\", getattr(torch,\"__version__\",None))\n print(\"CUDA     :\", torch.cuda.is_available())\nexcept Exception as e:\n print(\"PyTorch not available:\", e)')"
python -c "exec('try:\n import transformers\n print(\"Transformers:\", transformers.__version__)\nexcept Exception as e:\n print(\"Transformers not available:\", e)')"
python -c "exec('try:\n import umap\n print(\"UMAP     :\", umap.__version__)\nexcept Exception as e:\n print(\"UMAP not available:\", e)')"
python -c "exec('try:\n from sam2.build_sam import build_sam2_camera_predictor\n print(\"SAM2     : OK (camera predictor)\")\nexcept Exception as e:\n print(\"SAM2     : NOT FOUND\", e)')"

popd
exit /b 0
