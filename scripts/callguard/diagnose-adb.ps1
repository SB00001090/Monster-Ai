# ADB USB diagnostics for Monster Call Guard install
# Developed by Suckbob | Monster AI Call Guard
param([int]$WaitSeconds = 0)

$ErrorActionPreference = "Continue"

function Find-Adb {
    if (Get-Command adb -ErrorAction SilentlyContinue) { return (Get-Command adb).Source }
    $paths = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "C:\Program Files\Android\Android Studio\sdk\platform-tools\adb.exe"
    )
    foreach ($p in $paths) { if (Test-Path $p) { return $p } }
    return $null
}

Write-Host "=== ADB USB Diagnostics ===" -ForegroundColor Cyan

$adb = Find-Adb
if (-not $adb) {
    Write-Host "[FAIL] adb.exe not found" -ForegroundColor Red
    Write-Host "Fix: Install Android Studio, or SDK Platform-Tools" -ForegroundColor Yellow
    Write-Host "  winget install Google.PlatformTools" -ForegroundColor Yellow
    exit 1
}
Write-Host "adb: $adb" -ForegroundColor DarkGray

& $adb kill-server 2>$null
Start-Sleep -Seconds 1
& $adb start-server
Write-Host ""

if ($WaitSeconds -gt 0) {
    Write-Host "Waiting up to ${WaitSeconds}s for device (unlock phone, tap Allow)..." -ForegroundColor Yellow
    & $adb wait-for-device -t $WaitSeconds 2>$null
}

$raw = & $adb devices -l 2>&1
Write-Host $raw

$lines = @($raw | Where-Object { $_ -match "\t" })
$device = $lines | Where-Object { $_ -match "\tdevice(\s|$)" }
$unauth = $lines | Where-Object { $_ -match "\tunauthorized" }
$offline = $lines | Where-Object { $_ -match "\toffline" }

Write-Host ""
if ($device) {
    Write-Host "[OK] Device ready for install" -ForegroundColor Green
    Write-Host "Next: install-apk-adb.bat" -ForegroundColor Cyan
    exit 0
}

if ($unauth) {
    Write-Host "[ACTION] Phone shows UNAUTHORIZED" -ForegroundColor Yellow
    Write-Host "  1. Unplug and replug USB cable" -ForegroundColor White
    Write-Host "  2. On phone: tap Allow USB debugging (check Always allow)" -ForegroundColor White
    Write-Host "  3. Run: diagnose-adb.ps1 -WaitSeconds 60" -ForegroundColor White
    exit 2
}

if ($offline) {
    Write-Host "[ACTION] Device OFFLINE" -ForegroundColor Yellow
    Write-Host "  1. Change USB mode to File Transfer / MTP (not Charge only)" -ForegroundColor White
    Write-Host "  2. Try another USB cable (data cable, not charge-only)" -ForegroundColor White
    Write-Host "  3. Run: adb kill-server then diagnose-adb.ps1 again" -ForegroundColor White
    exit 3
}

Write-Host "[FAIL] No device detected" -ForegroundColor Red
Write-Host ""
Write-Host "Phone checklist:" -ForegroundColor Yellow
Write-Host "  Settings -> About phone -> tap Build number 7x (Developer mode)"
Write-Host "  Settings -> Developer options -> USB debugging ON"
Write-Host "  Connect USB -> notification -> USB for File transfer / MTP"
Write-Host "  When popup: Allow USB debugging from this computer"
Write-Host ""
Write-Host "PC checklist:" -ForegroundColor Yellow
Write-Host "  Install OEM USB driver if Samsung/Xiaomi/Oppo (optional)"
Write-Host "  winget install Google.PlatformTools"
Write-Host "  Different USB port (USB 2.0 port often works better)"
Write-Host ""
Write-Host "No USB? Use Tunnel mode instead:" -ForegroundColor Cyan
Write-Host "  Copy APK to phone manually, install, paste Tunnel URL in app"
exit 1