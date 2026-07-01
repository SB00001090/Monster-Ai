# Monster Call Guard — pre-delivery verification
# Developed by Suckbob | Monster AI Call Guard
param(
    [string]$ProjectRoot = "",
    [string]$TunnelUrl = "",
    [switch]$CopyToPhone
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$tunnelFile = Join-Path $ProjectRoot "data\callguard\tunnel_url.txt"
if (-not $TunnelUrl -and (Test-Path $tunnelFile)) {
    $TunnelUrl = (Get-Content $tunnelFile -Raw).Trim()
}

Write-Host "=== Call Guard Delivery Test ===" -ForegroundColor Cyan
$fail = 0

function Assert-Ok($name, $cond, $detail = "") {
    if ($cond) {
        Write-Host "[OK] $name" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $name $detail" -ForegroundColor Red
        $script:fail++
    }
}

# 1) APK artifact
$apk = Get-ChildItem (Join-Path $ProjectRoot "dist") -Filter "MonsterCallGuard-v*-signed.apk" |
    Sort-Object Name -Descending | Select-Object -First 1
Assert-Ok "APK built" ($null -ne $apk) $apk.FullName
if ($apk) { Write-Host "     $($apk.Name)" -ForegroundColor DarkGray }

# 2) Android unit tests
Write-Host "`n[Android tests]" -ForegroundColor Yellow
$androidDir = Join-Path $ProjectRoot "apps\monstercallguard-android"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
Push-Location $androidDir
& .\gradlew.bat test --no-daemon -q
$gradleOk = $LASTEXITCODE -eq 0
Pop-Location
Assert-Ok "Gradle unit tests" $gradleOk

# 3) Python tests
Write-Host "`n[Python tests]" -ForegroundColor Yellow
Push-Location $ProjectRoot
python -m pytest tests/test_callguard_connection.py tests/test_callguard_consensus.py -q
$pyOk = $LASTEXITCODE -eq 0
Pop-Location
Assert-Ok "CallGuard API tests" $pyOk

# 4) Local backend
Write-Host "`n[Backend smoke]" -ForegroundColor Yellow
$base = "http://127.0.0.1:7860"
try {
    $health = Invoke-RestMethod "$base/health" -TimeoutSec 4
    Assert-Ok "Backend /health" ($health.status -eq "ok")
} catch {
    Assert-Ok "Backend /health" $false $_.Exception.Message
}

try {
    $conn = Invoke-RestMethod "$base/api/callguard/connection" -TimeoutSec 4
    Assert-Ok "Backend /connection JSON" ($conn.mode -eq "cloudflare_tunnel")
    Assert-Ok "no_tailscale" ($conn.no_tailscale -eq $true)
    Assert-Ok "no_qr_code" ($conn.no_qr_code -eq $true)
} catch {
    Assert-Ok "Backend /connection JSON" $false "Restart start-callguard.bat — stale server returns HTML"
}

try {
    $body = @{ number = "+85290001111"; display_name = "test"; deep = $false } | ConvertTo-Json
    $analyze = Invoke-RestMethod "$base/api/callguard/analyze" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
    Assert-Ok "analyze trust_score" ($null -ne $analyze.trust_score)
} catch {
    Assert-Ok "analyze trust_score" $false $_.Exception.Message
}

# 5) Tunnel remote
if ($TunnelUrl) {
    Write-Host "`n[Tunnel smoke] $TunnelUrl" -ForegroundColor Yellow
    try {
        $th = Invoke-RestMethod "$TunnelUrl/health" -TimeoutSec 10
        Assert-Ok "Tunnel /health" ($th.status -eq "ok")
    } catch {
        Assert-Ok "Tunnel /health" $false $_.Exception.Message
    }
    try {
        $body = @{ number = "+85290001111"; display_name = "test"; deep = $false } | ConvertTo-Json
        $ta = Invoke-RestMethod "$TunnelUrl/api/callguard/analyze" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10
        Assert-Ok "Tunnel analyze" ($ta.score -ge 0)
    } catch {
        Assert-Ok "Tunnel analyze" $false $_.Exception.Message
    }
}

# 6) Optional MTP copy
if ($CopyToPhone -and $apk) {
    Write-Host "`n[Copy to phone]" -ForegroundColor Yellow
    $shell = New-Object -ComObject Shell.Application
    $pc = $shell.NameSpace(17)
    $phone = ($pc.Items() | Where-Object { $_.Name -match 'V Max' } | Select-Object -First 1)
    if ($phone) {
        $storage = ($phone.GetFolder().Items() | Select-Object -First 1).GetFolder()
        $download = ($storage.Items() | Where-Object { $_.Name -match 'Download' } | Select-Object -First 1).GetFolder()
        $src = $shell.NameSpace($apk.DirectoryName)
        $download.CopyHere($src.ParseName($apk.Name), 0x14)
        Start-Sleep -Seconds 5
        Assert-Ok "MTP copy to Download" $true
    } else {
        Assert-Ok "MTP copy to Download" $false "V Max Pro not visible"
    }
}

Write-Host ""
if ($fail -eq 0) {
    Write-Host "=== DELIVERY READY ===" -ForegroundColor Green
    Write-Host "APK: dist\$($apk.Name)"
    if ($TunnelUrl) { Write-Host "Tunnel: $TunnelUrl" }
    exit 0
}
Write-Host "=== $fail CHECK(S) FAILED — fix before delivery ===" -ForegroundColor Red
exit 1