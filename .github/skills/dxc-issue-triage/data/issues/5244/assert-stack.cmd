@echo off
rem Capture the assert stack for issue #5244 (SPIR-V codegen for RWTexture2DMS).
rem
rem A plain (non-debugger) run of the repro already exits 0xE0000001 ("Internal compiler
rem error: LLVM Assert") because these are ordinary C++ assert()s that dxc's llvm_assert
rem handler turns into a C++ exception rather than a __debugbreak() trap -- but the message,
rem file and line are only visible under a debugger. `gh` ("go handled") continues past each
rem assert, which is what shows the underlying codegen defect is not just the assert: the
rem SPIR-V module DXC then tries to emit is invalid, and its own embedded validator rejects it.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; the shader path is relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### repro.hlsl -- the repro, with the arguments in cmd.txt; continue past both chained asserts
"%CDB%" -c "sxe -c \"kb 8; gh\" e0000001; g; q" "%DXC%" -spirv -Zi -fspv-reflect -E PS -T ps_6_7 repro.hlsl
endlocal
