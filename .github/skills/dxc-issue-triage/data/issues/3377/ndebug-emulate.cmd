@echo off
rem Emulate NDEBUG on the Debug build for issue #3377, to show that the Debug assert and the
rem reporter's Release access violation are the same defect.
rem
rem DXASSERT uses __debugbreak(), so "gh" ("go handled") steps over the trap and continues into
rem exactly the code a release build -- where DXASSERT expands to `do { } while (0)`
rem (include/dxc/Support/Global.h:356) -- would have run. Two asserts fire on this repro
rem (ScalarReplAggregatesHLSL.cpp:4791 then :4801), so more than one "gh" is needed; 30 is
rem simply more than enough. ".lastevent" then names the exception the run actually died on and
rem "kn" prints its stack.
rem
rem Usage:  ndebug-emulate.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; repro.hlsl is relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

set GH=gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;gh;

"%CDB%" -c "g;%GH%.lastevent;kn 16;q" "%DXC%" -T ps_6_0 -E main_fragment repro.hlsl
endlocal
