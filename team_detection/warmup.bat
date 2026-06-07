@echo off
REM Run warmup with same arguments
pushd %~dp0
python warmup.py %*
popd
