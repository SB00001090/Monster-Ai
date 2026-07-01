# Install Monster Call Guard APK via USB ADB + adb reverse bridge
# Developed by Suckbob | Monster AI Call Guard
param(
    [string]$ProjectRoot = "",
    [string]$Version = "",
    [int]$WaitSeconds = 45
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

function Find-Adb {
    if (Get-Command adb -ErrorAction SilentlyContinue) { return (Get-Command adb).Source }
    $sdk = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
    if (Test-Path $sdk) { return $sdk }
    $studio = "C:\Program Files\Android\Android Studio\sdk\platform-tools\adb.exe"
    if (Test-Path $studio) { return $studio }
    return $null
}

function Test-AdbDevice {
    param([string]$AdbPath)
    $raw = & $AdbPath devices 2>&1
    $lines = @($raw | Where-Object { $_ -match "\t" })
    return @{
        Raw = $raw
        Ready = @($lines | Where-Object { $_ -match "\tdevice(\s|$)" })
        Unauthorized = @($lines | Where-Object { $_ -match "\tunauthorized" })
        Offline = @($lines | Where-Object { $_ -match "\toffline" })
    }
}

Write-Host "=== Monster Call Guard ADB Install ===" -ForegroundColor Cyan
Write-Host "Developed by Suckbob | Monster AI Call Guard"

$adb = Find-Adb
if (-not $adb) {
    Write-Host "[ERROR] adb not found." -ForegroundColor Red
    Write-Host "  winget install Google.PlatformTools" -ForegroundColor Yellow
    exit 1
}

if (-not $Version) {
    $gradle = Join-Path $ProjectRoot "apps\monstercallguard-android\app\build.gradle.kts"
    $Version = "1.3.0"
    if (Test-Path $gradle) {
        $m = Select-String -Path $gradle -Pattern 'versionName\s*=\s*"([^"]+)"' | Select-Object -First 1
        if ($m) { $Version = $m.Matches.Groups[1].Value }
    }
}

$apkName = "MonsterCallGuard-v$Version-signed.apk"
$apkPath = Join-Path $ProjectRoot "dist\$apkName"
if (-not (Test-Path $apkPath)) {
    $fallback = Get-ChildItem (Join-Path $ProjectRoot "dist") -Filter "MonsterCallGuard-v*-signed.apk" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($fallback) {
        $apkPath = $fallback.FullName
        $apkName = $fallback.Name
        Write-Host "[INFO] Using $apkName" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] Building APK ..." -ForegroundColor Yellow
        & (Join-Path $PSScriptRoot "build-release-apk.ps1") -ProjectRoot $ProjectRoot
        if (-not (Test-Path $apkPath)) {
            Write-Host "[ERROR] APK missing: $apkPath" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host "[1/5] Restart ADB server ..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $adb kill-server 2>$null
$ErrorActionPreference = $prevEap
Start-Sleep -Seconds 1
& $adb start-server | Out-Null

Write-Host "[2/5] Detect USB device (wait ${WaitSeconds}s max) ..."
Write-Host "  >> Unlock phone. If popup appears, tap Allow USB debugging <<" -ForegroundColor Yellow
$deadline = (Get-Date).AddSeconds($WaitSeconds)
$status = Test-AdbDevice -AdbPath $adb
while (-not $status.Ready.Count -and (Get-Date) -lt $deadline) {
    if ($status.Unauthorized.Count) {
        Write-Host "  ... waiting for you to tap Allow on phone ..." -ForegroundColor DarkYellow
    } else {
        Write-Host "  ... plug USB, enable USB debugging, set USB to File Transfer ..." -ForegroundColor DarkYellow
    }
    Start-Sleep -Seconds 3
    $status = Test-AdbDevice -AdbPath $adb
}

Write-Host $status.Raw
if (-not $status.Ready.Count) {
    Write-Host "[ERROR] No authorized device." -ForegroundColor Red
    & (Join-Path $PSScriptRoot "diagnose-adb.ps1")
    exit 1
}

Write-Host "[3/5] Installing $apkName ..."
& $adb install -r $apkPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] adb install failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

Write-Host "[4/5] USB bridge: adb reverse tcp:7860 tcp:7860 ..."
& $adb reverse tcp:7860 tcp:7860
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] adb reverse failed - is main.py running on :7860?" -ForegroundColor Yellow
}

Write-Host "[5/5] Verify PC backend ..."
try {
    Invoke-RestMethod "http://127.0.0.1:7860/health" -TimeoutSec 3 | Out-Null
    Write-Host "  [OK] http://127.0.0.1:7860" -ForegroundColor Green
} catch {
    Write-Host "  [!] Run start-callguard.bat first" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[OK] Installed. Open app -> Test Connection -> USB mode" -ForegroundColor Green
Write-Host "  Remote (no USB): run-tunnel.bat + paste Tunnel URL" -ForegroundColor Cyan