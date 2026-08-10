@echo off
rem #4256 harness entry point. Registered with
rem   triage.py compiler --id main-debug-dxv --exe <this file>
rem so the harness looks like a compiler to the whole tool (SKILL.md).
rem The DXC build directory is taken from DXC_BIN when set, so the same harness
rem can be pointed at another build.
python "%~dp0validate.py" %*
