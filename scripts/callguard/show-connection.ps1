# Monster Call Guard connection info
$ErrorActionPreference = "SilentlyContinue"
Write-Host ""
Write-Host "=== Monster Call Guard Connection ===" -ForegroundColor Cyan

try {
    Invoke-RestMethod "http://127.0.0.1:7860/health" -TimeoutSec 3 | Out-Null
    Write-Host "[OK] Local backend: http://127.0.0.1:7860" -ForegroundColor Green
} catch {
    Write-Host "[!] Local backend offline - run run.bat first" -ForegroundColor Red
}

$urlFile = Join-Path $PSScriptRoot "..\..\data\callguard\tunnel_url.txt"
if (Test-Path $urlFile) {
    $saved = (Get-Content $urlFile -Raw).Trim()
    Write-Host ""
    Write-Host "Saved Tunnel URL:" -ForegroundColor Yellow
    Write-Host "  $saved"
    try {
        Invoke-RestMethod "$saved/health" -TimeoutSec 8 | Out-Null
        Write-Host "  [OK] Tunnel reachable" -ForegroundColor Green
    } catch {
        Write-Host "  [!] Tunnel dead - restart cloudflared" -ForegroundColor Red
    }
}

$lan = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.IPAddress -match '^192\.168\.' -and $_.PrefixOrigin -ne 'WellKnown'
} | Select-Object -First 1).IPAddress
if ($lan) {
    Write-Host ""
    Write-Host "Same Wi-Fi (run lan-bridge.py):" -ForegroundColor Yellow
    Write-Host "  http://${lan}:7860"
}

Write-Host ""
Write-Host "Call Guard App - paste FULL URL with https:// (no :7860)"
if (Test-Path $urlFile) {
    $saved = (Get-Content $urlFile -Raw).Trim()
    Write-Host "  Use: $saved"
} else {
    Write-Host "  No saved URL yet - run run-tunnel.bat first"
}
Write-Host "  WRONG: xxx.trycloudflare.com (placeholder only)"
Write-Host ""
Write-Host "Restart tunnel: run-tunnel.bat  (or python scripts/deploy_cloudflare.py --tunnel)"
Write-Host ""