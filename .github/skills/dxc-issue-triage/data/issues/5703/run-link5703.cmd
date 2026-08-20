@echo off
rem #5703 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-link5703.cmd`,
rem the documented way to triage a defect no single dxc.exe invocation can
rem reach (SKILL.md, "When the symptom is in a pass dxc.exe cannot run,
rem register the harness as a compiler"). The real work is in link5703.py
rem beside this file; this wrapper exists only because triage.py launches
rem the compiler as an executable.
rem
rem No absolute path is baked in: link5703.py derives the repo from its own
rem location and takes the tool directory from DXC_LINK5703_BIN (defaults
rem to <repo>/build/Release/bin, since no stable release or the local Debug
rem build directory ships dxl.exe).

setlocal
python "%~dp0link5703.py" %*
exit /b %ERRORLEVEL%
