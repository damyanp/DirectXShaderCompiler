@echo off
rem Build isense5172.exe -- the #5172 ParseTranslationUnit/IDxcIncludeHandler
rem comparison harness.
rem
rem No absolute paths: everything is derived from this script's own
rem location, so the repro runs from a fresh clone (SKILL.md, "A committed
rem repro must be runnable from the repo alone" -- measured on #2427).
rem
rem   build-isense5172.cmd            build into .\bin\
rem
rem The output directory is created here rather than assumed, because git
rem does not store empty directories and a missing one fails with the same
rem exit status as a real error.
rem
rem This file avoids `for (...)` and `if (...)` blocks entirely. The Visual
rem Studio paths contain "Program Files (x86)", and an expanded close paren
rem terminates a parenthesised block early -- which half-runs the block and
rem still reports success.

setlocal

set "HERE=%~dp0"
rem data\issues\5172\ -> repo root is six levels up.
for %%I in ("%HERE%..\..\..\..\..\..") do set "REPO=%%~fI"

if not exist "%HERE%bin" mkdir "%HERE%bin"

where cl.exe >nul 2>&1
if not errorlevel 1 goto :compile

set "VCV="
call :try "%ProgramFiles%\Microsoft Visual Studio\18\Enterprise"
call :try "%ProgramFiles%\Microsoft Visual Studio\18\Professional"
call :try "%ProgramFiles%\Microsoft Visual Studio\18\Community"
call :try "%ProgramFiles%\Microsoft Visual Studio\18\BuildTools"
call :try "%ProgramFiles%\Microsoft Visual Studio\2022\Enterprise"
call :try "%ProgramFiles%\Microsoft Visual Studio\2022\Professional"
call :try "%ProgramFiles%\Microsoft Visual Studio\2022\Community"
call :try "%ProgramFiles%\Microsoft Visual Studio\2022\BuildTools"
if not defined VCV goto :notoolset
call "%VCV%"
where cl.exe >nul 2>&1
if errorlevel 1 goto :notoolset

:compile
cl /nologo /EHsc /std:c++17 /W3 /MD /D_CRT_SECURE_NO_WARNINGS ^
   /I "%REPO%\include" ^
   "%HERE%isense5172.cpp" ^
   /Fo:"%HERE%bin\\" /Fe:"%HERE%bin\isense5172.exe" ^
   /link ole32.lib oleaut32.lib
exit /b %ERRORLEVEL%

:try
if defined VCV exit /b 0
if exist "%~1\VC\Auxiliary\Build\vcvars64.bat" set "VCV=%~1\VC\Auxiliary\Build\vcvars64.bat"
exit /b 0

:notoolset
echo build-isense5172: no Visual Studio C++ toolset found; run this from a 1>&2
echo                   Developer Command Prompt, or install the MSVC toolset. 1>&2
exit /b 1
