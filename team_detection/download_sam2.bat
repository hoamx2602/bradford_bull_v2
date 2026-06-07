@echo off
REM Download SAM2 checkpoints (powershell required)
pushd %~dp0

set SIZE=%1
if "%SIZE%"=="" set SIZE=all

if not exist checkpoints mkdir checkpoints

set BASE=https://dl.fbaipublicfiles.com/segment_anything_2/092824

:dispatch
if "%SIZE%"=="large" goto large
if "%SIZE%"=="base+" goto baseplus
if "%SIZE%"=="small" goto small
if "%SIZE%"=="tiny" goto tiny
if "%SIZE%"=="all" goto all

echo Usage: download_sam2.bat [large|base+|small|tiny|all]
popd
goto :eof

:download
set NAME=%1
if exist checkpoints\%NAME% (
    echo Already exists: checkpoints\%NAME%
) else (
    echo Downloading %NAME% ...
    powershell -Command "Invoke-WebRequest -Uri '%BASE%/%NAME%' -OutFile 'checkpoints\\%NAME%' -UseBasicParsing"
)
goto :eof

:large
call :download sam2.1_hiera_large.pt
popd
goto :eof

:baseplus
call :download sam2.1_hiera_base_plus.pt
popd
goto :eof

:small
call :download sam2.1_hiera_small.pt
popd
goto :eof

:tiny
call :download sam2.1_hiera_tiny.pt
popd
goto :eof

:all
call :download sam2.1_hiera_large.pt
call :download sam2.1_hiera_base_plus.pt
call :download sam2.1_hiera_small.pt
call :download sam2.1_hiera_tiny.pt
echo.
echo Done. Checkpoints in:
dir /b checkpoints\*.pt
popd
goto :eof
