@echo off
cd /d "%~dp0..\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnose-adb.ps1" -WaitSeconds 30
pause