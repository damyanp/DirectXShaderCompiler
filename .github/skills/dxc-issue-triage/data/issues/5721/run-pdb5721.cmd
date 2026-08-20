@echo off
rem #5721 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-pdb5721.cmd`,
rem the documented way to triage a defect no single dxc.exe invocation can
rem reach (SKILL.md, "When the symptom is in a pass dxc.exe cannot run,
rem register the harness as a compiler"). The real work is in pdb5721.py
rem and pdb5721-harness.cpp beside this file; this wrapper exists only
rem because triage.py launches the compiler as an executable.
rem
rem No absolute path is baked in: pdb5721.py derives the repo from its own
rem location.

setlocal
python "%~dp0pdb5721.py" %*
exit /b %ERRORLEVEL%
