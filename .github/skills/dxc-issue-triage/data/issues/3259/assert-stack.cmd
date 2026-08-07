@echo off
rem Capture the assert message and stack for issue #3259.
rem
rem dxc routes DXASSERT text to OutputDebugString (include/dxc/Support/Global.h) and
rem then __debugbreak()s, so the message is NOT on stderr -- a plain run prints only
rem "Internal compiler error: Terminal Error 0x80000003" and exits 0x80000003.
rem A debugger is the only way to see it.
rem
rem The first breakpoint is the loader's initial break; "g" runs on to the DXASSERT
rem trap, and "kn" then prints the stack at that second break.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; the repro path is relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl -- the repro, with the arguments in cmd.txt
"%CDB%" -c "g;kn 40;q" "%DXC%" -T as_6_5 -E main repro.hlsl

echo ### CASE 2: control-scalar-payload.hlsl -- legal payload, must not trap
"%CDB%" -c "g;kn 40;q" "%DXC%" -T as_6_5 -E main control-scalar-payload.hlsl
endlocal
