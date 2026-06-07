@echo off
REM Run process_video with same arguments
pushd %~dp0
python process_video.py %*
popd
