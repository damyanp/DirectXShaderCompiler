@echo off
rem #4168 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-link4168.cmd`, the
rem documented way to triage a defect dxc.exe alone cannot reach (SKILL.md,
rem "When the symptom is in a pass dxc.exe cannot run, register the harness as a
rem compiler"). The real work is in link4168.py beside this file; this wrapper
rem exists only because triage.py launches the compiler as an executable.
rem
rem No absolute path is baked in: link4168.py derives the repo from its own
rem location and takes the tool directory from DXC_LINK4168_BIN.

setlocal
python "%~dp0link4168.py" %*
exit /b %ERRORLEVEL%
