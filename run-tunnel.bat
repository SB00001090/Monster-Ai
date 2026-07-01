@echo off
REM Monster AI - Cloudflare Quick Tunnel (Call Guard)
REM Developed by Suckbob | Monster AI Call Guard
cd /d "%~dp0"
echo.
echo === Cloudflare Quick Tunnel ===
echo Project: %CD%
echo Ensure python main.py is running on http://127.0.0.1:7860
echo URL saves to data\callguard\tunnel_url.txt
echo.

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe scripts\deploy_cloudflare.py --tunnel
) else (
    python scripts\deploy_cloudflare.py --tunnel
)

if errorlevel 1 (
    echo.
    echo [ERROR] Tunnel failed. Install: winget install Cloudflare.cloudflared
    echo Or run cloudflared manually from WinGet folder.
    pause
    exit /b 1
)
pause