@echo off
rem #4723 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-dep4723.cmd`, the
rem documented route for a symptom a bare dxc invocation cannot put into a
rem scored capture (SKILL.md, "When the symptom is in a pass dxc.exe cannot
rem run, register the harness as a compiler"). `run`, --shader, --args,
rem --expect, `audit` and `reindex` then all apply unchanged.
rem
rem The work is in dep4723.py: batch cannot forward an arbitrary dxc command
rem line reliably, and -- more importantly -- it cannot report an exit status.
rem %ERRORLEVEL% inside a single cmd line is expanded when the line is parsed,
rem so a batch harness prints the PREVIOUS status; the Python that launched
rem the process is the only thing that sees the real one.
rem
rem One environment knob, defaulting to this repo's Debug build:
rem   DXC_EXE   the dxc.exe under test
rem
rem No absolute path is baked in: everything derives from this script's own
rem location, so the repro runs from a fresh clone.

setlocal
python "%~dp0dep4723.py" %*
exit /b %ERRORLEVEL%
