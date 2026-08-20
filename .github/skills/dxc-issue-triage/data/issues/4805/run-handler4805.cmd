@echo off
rem #4805 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-handler4805.cmd`,
rem which is the documented way to triage a defect dxc.exe cannot reach
rem (SKILL.md, "When the symptom is in a pass dxc.exe cannot run, register the
rem harness as a compiler"). `run`, --shader, --args, --expect and `reindex`
rem then all apply.
rem
rem The compiler under test comes from DXC_INCLUDE_DLL, so the same harness can
rem be pointed at any release's dxcompiler.dll. It defaults to the repo's
rem Debug build. No absolute path is baked in: everything is derived from this
rem script's own location.
rem
rem See build-handler4805.cmd for why this file uses goto rather than `if (...)`.

setlocal

set "HERE=%~dp0"
for %%I in ("%HERE%..\..\..\..\..\..") do set "REPO=%%~fI"

if defined DXC_INCLUDE_DLL goto :havedll
set "DXC_INCLUDE_DLL=%REPO%\build\Debug\bin\dxcompiler.dll"
:havedll

if exist "%HERE%bin\handler4805.exe" goto :run
rem Build on demand so the repro runs from a fresh clone. Build chatter must not
rem land in the captured probe output, so it goes to a log beside the binary.
call "%HERE%build-handler4805.cmd" >"%HERE%bin-build.log" 2>&1
if not exist "%HERE%bin\handler4805.exe" goto :nobuild

:run
"%HERE%bin\handler4805.exe" %*
exit /b %ERRORLEVEL%

:nobuild
echo run-handler4805: handler4805.exe is missing and could not be built; 1>&2
echo                  see bin-build.log 1>&2
exit /b 3
