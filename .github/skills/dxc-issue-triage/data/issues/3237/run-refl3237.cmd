@echo off
rem #3237 harness-as-compiler wrapper.
rem
rem Registered with `triage.py compiler --exe <abs path>\run-refl3237.cmd`, which
rem is the documented way to triage a defect dxc.exe cannot reach (SKILL.md,
rem "When the symptom is in a pass dxc.exe cannot run, register the harness as a
rem compiler"). `run`, --shader, --args, --expect and `reindex` then all apply.
rem
rem The reflection implementation under test comes from DXC_REFLECT_DLL, so the
rem same harness can be pointed at any release's dxcompiler.dll. It defaults to
rem the repo's Debug build. No absolute path is baked in: everything is derived
rem from this script's own location.
rem
rem See build-refl3237.cmd for why this file uses goto rather than `if (...)`.

setlocal

set "HERE=%~dp0"
for %%I in ("%HERE%..\..\..\..\..\..") do set "REPO=%%~fI"

if defined DXC_REFLECT_DLL goto :havedll
set "DXC_REFLECT_DLL=%REPO%\build\Debug\bin\dxcompiler.dll"
:havedll

if exist "%HERE%bin\refl3237.exe" goto :run
rem Build on demand so the repro runs from a fresh clone. Build chatter must not
rem land in the captured probe output, so it goes to a log beside the binary.
call "%HERE%build-refl3237.cmd" >"%HERE%bin-build.log" 2>&1
if not exist "%HERE%bin\refl3237.exe" goto :nobuild

:run
"%HERE%bin\refl3237.exe" %*
exit /b %ERRORLEVEL%

:nobuild
echo run-refl3237: refl3237.exe is missing and could not be built; 1>&2
echo               see bin-build.log 1>&2
exit /b 3
