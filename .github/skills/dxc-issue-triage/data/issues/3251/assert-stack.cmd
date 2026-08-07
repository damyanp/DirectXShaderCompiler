@echo off
rem Capture the assert message and stack for issue #3251.
rem
rem dxc routes DXASSERT text to OutputDebugString (include/dxc/Support/Global.h) and then
rem __debugbreak()s, so the message is NOT on stderr -- a plain run prints only
rem "Internal compiler error: Terminal Error 0x80000003" and exits 0x80000003. The file and
rem line, which are the whole point here, are only visible under a debugger.
rem
rem The first breakpoint is the loader's initial break; "g" runs on to the DXASSERT trap, and
rem "kn" then prints the stack at that second break.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; the shader paths are relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl -- the repro, with the arguments in cmd.txt
"%CDB%" -c "g;kn 12;q" "%DXC%" -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl

echo ### CASE 2: control-fieldwise-payload.hlsl -- same copy written field by field, must not trap
"%CDB%" -c "g;kn 12;q" "%DXC%" -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug control-fieldwise-payload.hlsl

echo ### CASE 3: variant-local-payload.hlsl -- payload filled from a local; traps ELSEWHERE
"%CDB%" -c "g;kn 12;q" "%DXC%" -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug variant-local-payload.hlsl
endlocal
