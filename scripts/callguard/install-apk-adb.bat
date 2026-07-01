@echo off
REM USB ADB install - Monster Call Guard APK + adb reverse
REM Developed by Suckbob | Monster AI Call Guard
cd /d "%~dp0..\.."
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-apk-adb.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
if %EXITCODE% neq 0 (
    echo [FAILED] Run: scripts\callguard\diagnose-adb.bat
    echo Phone: Developer options - USB debugging ON, USB mode File Transfer
) else (
    echo [OK] APK installed. Test connection in app.
)
pause
exit /b %EXITCODE%