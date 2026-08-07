@echo off
rem #3251 -- what a Release build would do, without building one.
rem
rem DXASSERT expands to `do { } while (0)` under NDEBUG (include/dxc/Support/Global.h:356), and
rem LLVM's own `assert(use_empty() && "Uses remain when a value is destroyed!")`
rem (lib/IR/Value.cpp:83) is compiled out too. Continuing past an assert in the debugger runs
rem the code a release build would have run, so this shows what the missing HLOpcodeGroup::NotHL
rem case costs once the assert is gone (SKILL.md step 3).
rem
rem   g      run to the first trap: DXASSERT(0, "not implemented yet"), HLOperationLower.cpp:8801
rem   gh     "go handled" -- resume past it, i.e. behave as if the assert were compiled out
rem   sxe -c "gh" e0000001  do the same for the C++-exception form of an assert, which is how
rem                         LLVM's assert() arrives (dxcompiler!llvm_assert -> RaiseException)
rem
rem Usage:  ndebug-emulate.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### STEP 1: continue past the DXASSERT only -- where does the unhandled memcpy lead?
"%CDB%" -c "g;gh;.lastevent;kn 14;q" "%DXC%" -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl

echo ### STEP 2: continue past every assert -- the full NDEBUG emulation
"%CDB%" -c "sxe -c \"gh\" e0000001;g;gh;.lastevent;kn 14;q" "%DXC%" -T as_6_5 -E main -Zi -enable-16bit-types -Qembed_debug repro.hlsl
endlocal
