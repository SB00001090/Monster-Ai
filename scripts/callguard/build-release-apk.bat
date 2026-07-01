@echo off
REM Monster Call Guard - Release APK build (double-click safe)
REM Developed by Suckbob | Monster AI Call Guard
cd /d "%~dp0..\.."
echo.
echo === Monster Call Guard APK Build ===
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell not found
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-release-apk.ps1" -Pause
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% neq 0 (
    echo [FAILED] Exit code: %EXITCODE%
    echo Log: dist\build-apk-log.txt
) else (
    echo [OK] Output: dist\MonsterCallGuard-v*.apk
)
echo.
pause
exit /b %EXITCODE%