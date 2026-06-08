@echo off
REM Train the yolo26 logo detector. Activate the env first:
REM     conda activate bradford_bulls
REM     train.bat                       (yolo26m @ 1280, defaults)
REM     train.bat --model yolo26s.pt --epochs 200
cd /d "%~dp0"
python train.py %*
