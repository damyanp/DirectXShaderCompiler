@echo off
rem Capture the assert message, file and line, plus the stack, for issue #3377.
rem
rem dxc routes DXASSERT text to OutputDebugString (include/dxc/Support/Global.h:300) and then
rem __debugbreak()s, so the message is NOT on stderr -- a plain run prints only
rem "Internal compiler error: Terminal Error 0x80000003" and exits 0x80000003. The file and
rem line are only visible under a debugger, and they are what identifies the defect.
rem
rem The first break is the loader's; "g" runs on to the DXASSERT trap; "kn" prints the stack.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; the shader paths are relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl -- the repro, with the arguments in cmd.txt
"%CDB%" -c "g;kn 12;q" "%DXC%" -T ps_6_0 -E main_fragment repro.hlsl

echo ### CASE 2: variant-minimal.hlsl -- no matrix, no SamplerState, no second entry point
"%CDB%" -c "g;kn 8;q" "%DXC%" -T ps_6_0 -E main_fragment variant-minimal.hlsl

echo ### CASE 3: control-no-semantic.hlsl -- repro minus the semantic; must NOT trap
"%CDB%" -c "g;kn 8;q" "%DXC%" -T ps_6_0 -E main_fragment control-no-semantic.hlsl

echo ### CASE 4: variant-no-uniform.hlsl -- same as CASE 2 with the `uniform` keyword dropped
"%CDB%" -c "g;kn 8;q" "%DXC%" -T ps_6_0 -E main_fragment variant-no-uniform.hlsl
endlocal
