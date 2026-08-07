@echo off
rem Capture the assert message and stack for issue #2191.
rem
rem dxc routes assert text to OutputDebugString (lib/Support/assert.cpp,
rem llvm_assert -> OutputDebugFormatA) and then RaiseException(0xE0000001), so
rem the message is NOT on stderr -- a plain run only prints
rem "Internal compiler error: LLVM Assert". A debugger is the only way to see it.
rem
rem Usage:  assert-stack.cmd <path-to-Debug-dxc.exe> [path-to-cdb.exe]
rem Run from this directory; both inputs are relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl (-T cs_6_0 -E main) -- the issue as filed
"%CDB%" -c "sxe -c \"kn 30;q\" e0000001;g;q" "%DXC%" -T cs_6_0 -E main repro.hlsl

echo ### CASE 2: variant-maxvertexcount.hlsl (-T gs_6_0 -E main) -- a different attribute
"%CDB%" -c "sxe -c \"kn 12;q\" e0000001;g;q" "%DXC%" -T gs_6_0 -E main variant-maxvertexcount.hlsl
endlocal
