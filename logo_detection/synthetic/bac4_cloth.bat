@echo off
REM Bac 4 (P0) 3D cloth-drape logo factory. No conda env needed (Blender has its own
REM Python). Edit BLENDER below if you installed it elsewhere.
REM     bac4_cloth.bat --n 8 --out data_bac4
REM     bac4_cloth.bat --n 500 --samples 96 --res 1024
set "BLENDER=C:\Users\xmai\blender_portable\blender-4.2.0-windows-x64\blender.exe"
cd /d "%~dp0"
if not exist "%BLENDER%" (
  echo [error] blender.exe not found at %BLENDER%
  echo Edit the BLENDER path at the top of this .bat
  exit /b 1
)
"%BLENDER%" --background --python bac4_cloth.py -- %*
