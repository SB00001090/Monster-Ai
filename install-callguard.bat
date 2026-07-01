@echo off
REM Monster Call Guard — 一鍵安裝（後端 + APK 建置）
REM Developed by Suckbob | Monster AI
cd /d "%~dp0"
echo.
echo === Monster Call Guard 安裝 ===
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請先安裝 Python 3.11+
    pause
    exit /b 1
)

echo [1/4] 檢查 Monster AI 後端...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:7860/api/callguard/status' -UseBasicParsing -TimeoutSec 3; Write-Host '[OK] CallGuard API:' $r.Content } catch { Write-Host '[!] 後端未運行 — 請先執行 run.bat 或 run-vmax-pro.bat' -ForegroundColor Yellow }"

echo.
echo [2/4] 建置 Android APK（首次約 3-10 分鐘）...
call "%~dp0scripts\callguard\build-release-apk.bat"
if errorlevel 1 (
    echo [錯誤] APK 建置失敗。請安裝 Android Studio 並 Sync Gradle。
    pause
    exit /b 1
)

echo.
echo [3/4] APK 輸出位置:
if exist "dist\MonsterCallGuard-v1.2.0-signed.apk" (
    echo   dist\MonsterCallGuard-v1.2.0-signed.apk
    dir "dist\MonsterCallGuard-v1.2.0-signed.apk"
    echo   發布: scripts\callguard\publish-github-release.ps1 -Version 1.2.0
) else (
    echo   [未找到] 請檢查 apps\monstercallguard-android\app\build\outputs\apk\release\
)

echo.
echo [4/4] 手機安裝步驟:
echo   1. 將 APK 傳到手機並安裝（允許未知來源）
echo   2. 電腦: run-tunnel.bat
echo   3. App 填 Cloudflare Tunnel URL ^(例 https://xxx.trycloudflare.com^)
echo   4. 啟用「來電篩選」+「背景保護」
echo.
echo 詳細教學: scripts\callguard\INSTALL_SIDELoad.md
echo.
pause