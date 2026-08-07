@echo off
rem Point DXC at any dxc.exe; the QUOTING of the arguments below is what is
rem under test, so it must not be altered. Run from this directory, via cmd.exe
rem -- PowerShell re-quotes arguments and repairs the very bug being measured.
if "%DXC%"=="" set DXC=%~dp0..\..\..\..\..\..\build\Debug\bin\dxc.exe
rem The output directory must exist: -Fd does not create it, and a missing
rem dbgdir makes every case fail with "cannot find the path specified",
rem which masks the argv-splitting behaviour this repro is about. Git does
rem not track empty directories, so create it here rather than commit it.
if not exist "%~dp0dbgdir" mkdir "%~dp0dbgdir"
echo === A: reported failing form: -Fd "dbgdir\" ===
"%DXC%" -T ps_6_0 /Zi -Fd "dbgdir\" mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
echo.
echo === B: pow2clk workaround: -Fd "dbgdir"\ ===
"%DXC%" -T ps_6_0 /Zi -Fd "dbgdir"\ mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
echo.
echo === C: unquoted trailing backslash ===
"%DXC%" -T ps_6_0 /Zi -Fd dbgdir\ mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
