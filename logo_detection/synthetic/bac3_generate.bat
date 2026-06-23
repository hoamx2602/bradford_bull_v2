@echo off
REM Bac 3 (Bien the C) diffusion harmonization generator. Activate the env first:
REM     conda activate bradford_bulls
REM     bac3_generate.bat --n 8           (smoke test; 1st run downloads ~10GB models)
REM     bac3_generate.bat --n 2000 --steps 30
REM     bac3_generate.bat --no-ip-adapter
cd /d "%~dp0"
python bac3_generate.py %*
