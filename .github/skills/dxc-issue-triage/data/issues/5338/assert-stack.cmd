@echo off
rem Capture the assert message and stack for issue #5338.
rem
rem This assert arrives as a trapped DXASSERT (SKILL.md: "an assert firing
rem with no debugger attached" -> exit 0x80000003, a breakpoint trap), not as
rem a thrown C++ exception, so the launch is "g;kn 40;q" -- just run to the
rem trap and dump the stack -- not the "sxe -c ... e0000001;g;q" form used for
rem the exception-style asserts on other issues.
rem
rem Usage:  assert-stack.cmd <path-to-Debug-dxc.exe> [path-to-cdb.exe]
rem Run from this directory; both inputs are relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl (-T vs_6_0) -- the issue as filed
"%CDB%" -c "g;kn 40;q" "%DXC%" -T vs_6_0 repro.hlsl
endlocal
