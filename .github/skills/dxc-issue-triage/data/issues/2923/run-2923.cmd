@echo off
setlocal enabledelayedexpansion
rem ---------------------------------------------------------------------------
rem Repro driver for microsoft/DirectXShaderCompiler#2923.
rem
rem The symptom lives in the PIX "numbering" pass
rem (-dxil-annotate-with-virtual-regs), which never runs during an ordinary dxc
rem compile, so a plain `dxc` command line cannot show it. This reproduces the
rem exact pipeline PixTest.cpp's RunAnnotationPasses uses:
rem
rem   dxc   -Zi -Qembed_debug ...            -> container with a debug DXIL part
rem   dxa   -extractpart=dbgmodule           -> the ILDB module
rem   dxopt -opt-mod-passes
rem            -dxil-dbg-value-to-dbg-declare
rem            -dxil-annotate-with-virtual-regs
rem   opt   -S                               -> readable annotated IR
rem   check-2923.py                          -> the report scored by match.json
rem
rem Usage:  run-2923.cmd <shader.hlsl> [-Od|-O1]
rem         run-2923.cmd --version
rem
rem Environment overrides (used by history-2923.cmd to probe old releases):
rem   DXC_BIN   directory holding dxa.exe / dxopt.exe / opt.exe  (this build)
rem   PIX_DXC   dxc.exe used to compile the shader
rem   PIX_DLL   dxcompiler.dll whose PIX passes are run (via dxopt -external)
rem ---------------------------------------------------------------------------
if "%DXC_BIN%"=="" set "DXC_BIN=%~dp0..\..\..\..\..\..\build\Debug\bin"
if "%PIX_DXC%"=="" set "PIX_DXC=%DXC_BIN%\dxc.exe"
set "EXTERNAL="
if not "%PIX_DLL%"=="" set "EXTERNAL=-external %PIX_DLL% -external-fn DxcCreateInstance"

if "%~1"=="--version" (
  echo # compiler used to compile the shader:
  "%PIX_DXC%" --version
  echo # dxcompiler.dll providing the PIX passes:
  if "%PIX_DLL%"=="" ("%DXC_BIN%\dxc.exe" --version) else (echo %PIX_DLL%)
  exit /b 0
)

if "%~1"=="" echo usage: run-2923.cmd ^<shader.hlsl^> [-Od^|-O1] & exit /b 2
set "SRC=%~1"
set "OPT=%~2"
if "%OPT%"=="" set "OPT=-Od"
set "STEM=%~n1%OPT%"

echo # shader: %SRC%    optimization: %OPT%
echo # (PixTest.cpp compiles with /Zi /Qembed_debug -HV 2018 -enable-16bit-types)
echo.

echo $ dxc -T as_6_5 -E main %OPT% -HV 2018 -enable-16bit-types -Zi -Qembed_debug %SRC% -Fo%STEM%.dxo
"%PIX_DXC%" -T as_6_5 -E main %OPT% -HV 2018 -enable-16bit-types -Zi -Qembed_debug "%SRC%" -Fo%STEM%.dxo
if errorlevel 1 (echo ## dxc failed with %errorlevel% & exit /b 1)

echo $ dxa -extractpart=dbgmodule -o=%STEM%.ildb.bc %STEM%.dxo
"%DXC_BIN%\dxa.exe" "-extractpart=dbgmodule" "-o=%STEM%.ildb.bc" %STEM%.dxo
if errorlevel 1 (echo ## dxa failed with %errorlevel% & exit /b 1)

echo $ dxopt %EXTERNAL% -o=%STEM%.annotated.bc %STEM%.ildb.bc -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
"%DXC_BIN%\dxopt.exe" %EXTERNAL% "-o=%STEM%.annotated.bc" %STEM%.ildb.bc -opt-mod-passes -dxil-dbg-value-to-dbg-declare -dxil-annotate-with-virtual-regs
if errorlevel 1 (echo ## dxopt failed with %errorlevel% & exit /b 1)

echo $ opt -S -o=%STEM%.annotated.ll %STEM%.annotated.bc
"%DXC_BIN%\opt.exe" -S "-o=%STEM%.annotated.ll" %STEM%.annotated.bc
if errorlevel 1 (echo ## opt failed with %errorlevel% & exit /b 1)

echo $ python check-2923.py %STEM%.annotated.ll %OPT%
echo.
python "%~dp0check-2923.py" %STEM%.annotated.ll %OPT%
set "RC=%errorlevel%"
del /q %STEM%.dxo %STEM%.ildb.bc %STEM%.annotated.bc 2>nul
exit /b %RC%
