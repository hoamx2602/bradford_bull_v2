@echo off
REM Synthetic copy-paste generator for the class-agnostic logo Localizer.
REM Activate the env first:
REM     conda activate bradford_bulls
REM     gen_synthetic.bat                       (4000 imgs, real frames as bg)
REM     gen_synthetic.bat --n 8000 --max-logos 5
REM     gen_synthetic.bat --no-bg-labels        (clean-background mode)
cd /d "%~dp0"
python gen_synthetic.py %*
