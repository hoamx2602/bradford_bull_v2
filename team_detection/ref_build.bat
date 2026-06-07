@echo off
REM Run ref_build with same arguments
pushd %~dp0
python ref_build.py %*
popd
