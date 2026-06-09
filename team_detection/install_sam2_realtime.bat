@echo off
REM Install the SAM2 real-time (camera predictor) fork for the team_detection
REM pipeline. Activate your conda env first, e.g.:
REM     conda activate bradford_bulls
REM     install_sam2_realtime.bat
REM Optional args are forwarded, e.g.:  install_sam2_realtime.bat --size base+
cd /d "%~dp0"
python install_sam2_realtime.py %*
