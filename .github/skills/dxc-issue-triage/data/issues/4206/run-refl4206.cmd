@echo off
rem #4206 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-refl4206.cmd`, the
rem documented route for a defect dxc.exe cannot reach (SKILL.md, "When the
rem symptom is in a pass dxc.exe cannot run, register the harness as a
rem compiler").  `run`, --shader, --args, --expect, `audit` and `reindex` then
rem all apply unchanged.
rem
rem The real work is in refl4206.py; batch is a poor argument parser and the
rem harness has to forward an arbitrary dxc command line verbatim.
rem
rem Two environment knobs, both defaulting to this repo's Debug build:
rem   DXC_EXE     dxc.exe that COMPILES the container (the subject under test)
rem   DXC_READER  dxa.exe that READS it back (the instrument; hold this fixed)
rem
rem No absolute path is baked in: everything derives from this script's own
rem location, so the repro runs from a fresh clone.

setlocal
python "%~dp0refl4206.py" %*
exit /b %ERRORLEVEL%
