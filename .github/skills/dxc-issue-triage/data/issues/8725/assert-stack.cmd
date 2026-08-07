@echo off
rem Capture assert messages, stacks and the invalid IR for issue #8725.
rem
rem dxc routes assert text to OutputDebugString (lib/Support/assert.cpp,
rem llvm_assert -> OutputDebugFormatA) and then RaiseException(0xE0000001), so
rem the message is NOT on stderr -- a plain run only prints
rem "Internal compiler error: LLVM Assert". A debugger is the only way to see it.
rem
rem "sxe -c \"kn N;q\" e0000001" breaks on the first assert, prints N frames and
rem quits. "gh" instead of "q" continues execution with the exception handled,
rem which resumes after RaiseException -- i.e. it emulates what an NDEBUG build
rem does when the assert is compiled out, and shows what the compiler goes on to
rem produce.
rem
rem Usage:  assert-stack.cmd [path-to-Debug-dxc.exe] [path-to-cdb.exe]
rem Run from this directory; all inputs are relative to it.

setlocal
set DXC=%~1
if "%DXC%"=="" set DXC=..\..\..\..\..\..\build\Debug\bin\dxc.exe
set CDB=%~2
if "%CDB%"=="" set CDB=C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe

echo ### CASE 1: repro.hlsl (-T lib_6_9) -- the issue as filed, FIRST assert only
"%CDB%" -c "sxe -c \"kn 30;q\" e0000001;g;q" "%DXC%" -T lib_6_9 repro.hlsl

echo.
echo ### CASE 2: repro.hlsl -- continue past every assert (gh) to see the whole
echo ### sequence and what a build with asserts compiled out would report.
"%CDB%" -c "sxe -c \"kn 8;gh\" e0000001;g;q" "%DXC%" -T lib_6_9 repro.hlsl

echo.
echo ### CASE 3: control-inout.hlsl -- the reporter's workaround, must NOT assert
"%CDB%" -c "sxe -c \"kn 30;q\" e0000001;g;q" "%DXC%" -T lib_6_9 control-inout.hlsl

echo.
echo ### CASE 4: variant-static-global.hlsl -- no by-value parameter, no user
echo ### function: a mutable static global payload passed straight to Invoke.
"%CDB%" -c "sxe -c \"kn 12;q\" e0000001;g;q" "%DXC%" -T lib_6_9 variant-static-global.hlsl

echo.
echo ### CASE 5: variant-hitobject-traceray-byval.hlsl -- dx::HitObject::TraceRay,
echo ### not Invoke, with the same by-value payload parameter.
"%CDB%" -c "sxe -c \"kn 12;q\" e0000001;g;q" "%DXC%" -T lib_6_9 variant-hitobject-traceray-byval.hlsl

echo.
echo ### CASE 6: variant-nopaq.hlsl -disable-payload-qualifiers -- no payload
echo ### access qualifiers anywhere.
"%CDB%" -c "sxe -c \"kn 12;q\" e0000001;g;q" "%DXC%" -T lib_6_9 -disable-payload-qualifiers variant-nopaq.hlsl

echo.
echo ### CASE 7: repro.hlsl -fcgl, continuing past the asserts -- the invalid IR
echo ### that CodeGen emits for the Invoke call.
"%CDB%" -c "sxe -c \"gh\" e0000001;g;q" "%DXC%" -T lib_6_9 -fcgl repro.hlsl

echo.
echo ### CASE 8: control-inout.hlsl -fcgl -- the same IR for the working case, for
echo ### comparison. No debugger needed; run through cdb anyway so the two
echo ### captures are produced identically.
"%CDB%" -c "sxe -c \"gh\" e0000001;g;q" "%DXC%" -T lib_6_9 -fcgl control-inout.hlsl
endlocal
