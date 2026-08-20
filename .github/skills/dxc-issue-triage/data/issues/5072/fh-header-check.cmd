@echo off
rem #5072 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\fh-header-check.cmd`,
rem the documented way to bring a file-only output mode into the scored
rem capture (SKILL.md step 3: "-Fh writes only to a file ... a file-producing
rem mode needs a command chain or harness that brings that artifact into the
rem scored capture"). `run`, --shader, --args, --expect and `reindex` all then
rem apply to fh-header-check.py's stdout, the same as a plain dxc capture.
rem
rem No absolute path is baked in: everything fh-header-check.py needs is
rem derived from its own location or DXC_FH_REAL_EXE.

setlocal
python "%~dp0fh-header-check.py" %*
exit /b %ERRORLEVEL%
