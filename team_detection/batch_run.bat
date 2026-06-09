@echo off
REM Batch process multiple videos using ONE reference model.
pushd %~dp0

REM Configuration (edit or create videos.txt)
set REFS_PATH=output/refs/team_refs.pkl
set OUTPUT_BASE=output
set TEAM_A_LABEL=Bradford
set TEAM_B_LABEL=Opponent
set OTHER_LABEL=Other
set CONF=0.50
set MIN_HEIGHT=0.07
set SMOOTHING=20

if not exist videos.txt (
    echo Create a file named videos.txt in this folder with one video path per line.
    echo Example: C:\path\to\clip_001.mp4
    popd
    exit /b 1
)

for /f "usebackq delims=" %%V in ("videos.txt") do (
    if exist "%%~V" (
        call :process "%%~V"
    ) else (
        echo SKIP (not found): %%~V
    )
)

echo All done. Results in: %OUTPUT_BASE%\
popd
exit /b 0

:process
set "VIDEO=%~1"
for %%F in ("%VIDEO%") do set "STEM=%%~nF"
set "OUT_DIR=%OUTPUT_BASE%\%STEM%"
echo Processing: %STEM%
python process_video.py --video "%VIDEO%" --refs "%REFS_PATH%" --team_a_label "%TEAM_A_LABEL%" --team_b_label "%TEAM_B_LABEL%" --other_label "%OTHER_LABEL%" --output_dir "%OUT_DIR%" --conf %CONF% --min_height %MIN_HEIGHT% --smoothing %SMOOTHING%
echo.
goto :eof
