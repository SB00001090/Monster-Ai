@echo off
REM Monster Call Guard - fix MonsterLock, start backend, show tunnel steps
REM Developed by Suckbob | Monster AI Call Guard
cd /d "%~dp0"
echo.
echo === Monster Call Guard Stack ===
echo.

if not exist .venv\Scripts\python.exe (
    echo [ERROR] Run run.bat once to create .venv
    pause
    exit /b 1
)

echo [1/3] Repair MonsterLock seal + manifest ...
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\callguard\fix-monsterlock.ps1
if errorlevel 1 (
    echo [WARN] MonsterLock repair had issues - trying main.py anyway
)

echo.
echo [2/3] Starting Monster AI backend ...
echo Keep this window OPEN. Open a NEW terminal for tunnel.
echo.
set MONSTER_AI_CONNECT_CONSENT=1
if exist discord.token.local (
    for /f "usebackq tokens=*" %%a in (`powershell -NoProfile -Command "(Get-Content discord.token.local -Encoding UTF8 | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') } | Select-Object -First 1).Trim()"`) do set MONSTER_DISCORD_TOKEN=%%a
)
call .venv\Scripts\activate.bat
python main.py
pause