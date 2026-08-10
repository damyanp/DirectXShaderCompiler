@echo off
rem #4415 harness entry point. Registered with
rem   triage.py compiler --id main-debug-dxv4415 --exe <this file>
rem so the harness looks like a compiler to the whole tool (SKILL.md, "When the
rem symptom is in a pass dxc.exe cannot run, register the harness as a
rem compiler"). The DXC build directory is taken from DXC_BIN when set, so the
rem same harness can be pointed at another build.
python "%~dp0validate.py" %*
