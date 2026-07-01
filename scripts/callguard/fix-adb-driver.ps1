# Download + install Google USB driver for DOOGEE V Max Pro ADB
# Developed by Suckbob | Monster AI Call Guard
$ErrorActionPreference = "Continue"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$dest = Join-Path $root "data\callguard\usb_driver"
$inf = Join-Path $dest "usb_driver\android_winusb.inf"

if (-not (Test-Path $inf)) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $zip = Join-Path $dest "usb_driver.zip"
    Write-Host "Downloading Google USB driver..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://dl.google.com/android/repository/usb_driver_r13-windows.zip" -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $dest -Force
}

Write-Host "=== DOOGEE V Max Pro ADB Driver Fix ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Phone authorized OK. Windows needs ADB driver for VID_0E8D PID_2004." -ForegroundColor Yellow
Write-Host ""
Write-Host "Option A - Device Manager (recommended):" -ForegroundColor Green
Write-Host "  1. Win+X -> Device Manager"
Write-Host "  2. Find 'USB Composite Device' or unknown under Other devices (MediaTek)"
Write-Host "  3. Right-click -> Update driver -> Browse my computer"
Write-Host "  4. Let me pick -> Have Disk -> Browse to:"
Write-Host "     $inf"
Write-Host "  5. Select 'Android ADB Interface' -> Next -> Install"
Write-Host ""
Write-Host "Option B - Admin pnputil:" -ForegroundColor Green
Write-Host "  Right-click fix-adb-driver.bat -> Run as administrator"
Write-Host ""
Write-Host "Option C - Wireless debugging (no USB driver):" -ForegroundColor Green
Write-Host "  Phone: Developer options -> Wireless debugging -> ON"
Write-Host "  Tap 'Pair device with pairing code', then run:"
Write-Host "  adb pair <ip>:<port>  <6-digit-code>"
Write-Host "  adb connect <ip>:<port>"
Write-Host ""
Write-Host "After driver fix: diagnose-adb.bat -> install-apk-adb.bat" -ForegroundColor Cyan

Start-Process "devmgmt.msc"