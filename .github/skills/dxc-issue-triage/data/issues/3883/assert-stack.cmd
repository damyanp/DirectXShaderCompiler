@echo off
rem Capture the assert text, file/line and stack for issue #3883, and then emulate NDEBUG.
rem
rem A plain run of the Debug build prints only "Internal compiler error: LLVM Assert" and
rem exits 0xE0000001 -- the assert arrives as a C++ exception (llvm_assert -> RaiseException),
rem so the message, its file and its line are only visible under a debugger.
rem
rem `sxe -c "kb N; gh" e0000001` breaks on that exception, prints the stack and then goes
rem HANDLED, which is what emulates NDEBUG: continuing past the assert runs exactly the code
rem a Release build would have run, so this one Debug binary shows both the Debug symptom
rem and the Release symptom in a single transcript.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory, through cmd.exe (from PowerShell, cdb produces no output at all);
rem the shader paths are relative to it. Pipe through trim-cdb.py to get the committed form.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" for /f "delims=" %%I in ('where cdb.exe 2^>nul') do set CDB=%%I
if "%CDB%"=="" set CDB=%ProgramFiles(x86)%\Windows Kits\10\Debuggers\x64\cdb.exe

set CMD1=-c "sxe -c \"kb 9; gh\" e0000001; g; q" "%DXC%" -T ps_6_0 -E PSMain repro.hlsl
set CMD2=-c "sxe -c \"kb 4; gh\" e0000001; g; q" "%DXC%" -T ps_6_0 -E PSMain control-initialised.hlsl
set CMD3=-c "sxe -c \"gh\" e0000001; sxe -c \"kb 6\" e06d7363; g; q" "%DXC%" -T ps_6_0 -E PSMain repro.hlsl

echo ### CASE 1: repro.hlsl -- the repro, with the arguments in cmd.txt.
echo ### Two asserts fire in turn, then NDEBUG-emulated execution shows the Release symptom.
echo ### $ cdb %CMD1%
"%CDB%" %CMD1%

echo ### CASE 2: control-initialised.hlsl -- `uint index = 0;`. Must reach no assert at all.
echo ### The only break below is the loader's; no `Error: assert` line appears, and the
echo ### compile exits 0 (see variant-control-initialised-main-debug.txt).
echo ### $ cdb %CMD2%
"%CDB%" %CMD2%

echo ### CASE 3: where the RELEASE build actually dies. Both asserts are gone (`gh` past
echo ### them, which is what NDEBUG does), and the next break is the hlsl::Exception thrown
echo ### by the failing cast -- so this names the cast rather than inferring it from source.
echo ### $ cdb %CMD3%
"%CDB%" %CMD3%
endlocal
