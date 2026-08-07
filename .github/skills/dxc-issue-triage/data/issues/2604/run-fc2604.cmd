@echo off
rem #2604 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-fc2604.cmd`, which
rem is the documented way to triage a defect dxc.exe cannot reach (SKILL.md,
rem "When the symptom is in a pass dxc.exe cannot run, register the harness as
rem a compiler"). `run`, --shader, --args, --expect and `reindex` then all
rem apply.
rem
rem The compile implementation under test comes from DXC_FC_DLL, so the same
rem harness can be pointed at any release's dxcompiler.dll. It defaults to the
rem repo's Debug build. No absolute path is baked in: everything is derived
rem from this script's own location.
rem
rem See build-fc2604.cmd for why this file uses goto rather than `if (...)`.

setlocal

set "HERE=%~dp0"
for %%I in ("%HERE%..\..\..\..\..\..") do set "REPO=%%~fI"

if defined DXC_FC_DLL goto :havedll
set "DXC_FC_DLL=%REPO%\build\Debug\bin\dxcompiler.dll"
:havedll

if exist "%HERE%bin\fc2604.exe" goto :run
rem Build on demand so the repro runs from a fresh clone. Build chatter must
rem not land in the captured probe output, so it goes to a log beside the
rem binary.
call "%HERE%build-fc2604.cmd" >"%HERE%bin-build.log" 2>&1
if not exist "%HERE%bin\fc2604.exe" goto :nobuild

:run
"%HERE%bin\fc2604.exe" %*
exit /b %ERRORLEVEL%

:nobuild
echo run-fc2604: fc2604.exe is missing and could not be built; 1>&2
echo             see bin-build.log 1>&2
exit /b 3
