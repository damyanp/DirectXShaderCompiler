@echo off
echo === A: reported failing form: -Fd "dbgdir\" ===
"C:\prj\DirectXShaderCompiler\build\Debug\bin\dxc.exe" -T ps_6_0 /Zi -Fd "dbgdir\" mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
echo.
echo === B: pow2clk workaround: -Fd "dbgdir"\ ===
"C:\prj\DirectXShaderCompiler\build\Debug\bin\dxc.exe" -T ps_6_0 /Zi -Fd "dbgdir"\ mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
echo.
echo === C: unquoted trailing backslash ===
"C:\prj\DirectXShaderCompiler\build\Debug\bin\dxc.exe" -T ps_6_0 /Zi -Fd dbgdir\ mySimplePS.hlsl
echo [exit] %ERRORLEVEL%
