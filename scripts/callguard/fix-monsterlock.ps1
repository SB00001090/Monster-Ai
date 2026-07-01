# Re-seal config + rebuild integrity manifest after legitimate code/config changes
# Developed by Suckbob | Monster AI Call Guard
param([string]$ProjectRoot = "")

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
Set-Location $ProjectRoot

Write-Host "=== MonsterLock repair (Call Guard dev) ===" -ForegroundColor Cyan

if (Test-Path ".venv\Scripts\python.exe") {
    $py = ".venv\Scripts\python.exe"
} else {
    $py = "python"
}

Write-Host "[1/2] Rebuild integrity manifest ..."
& $py (Join-Path $ProjectRoot "scripts\monsterlock\build_manifest.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] build_manifest returned $LASTEXITCODE" -ForegroundColor Yellow
}

Write-Host "[2/2] Re-seal config.yaml ..."
& $py (Join-Path $ProjectRoot "scripts\callguard\reseal_config.py")

Write-Host ""
Write-Host "[OK] MonsterLock repair done. Now run: python main.py" -ForegroundColor Green
Write-Host "Or: start-callguard.bat" -ForegroundColor Cyan