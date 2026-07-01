# Publish Traditional Chinese README to Monster-Ai-ZH-TW (zh-tw remote)
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$zhReadme = Join-Path $root "Monster-ai Zh-Tw\README.md"
$enReadme = Join-Path $root "README.md"
$enBackup = Join-Path $env:TEMP "monster-ai-readme-en-backup.md"

if (-not (Test-Path $zhReadme)) {
    throw "Missing $zhReadme"
}

& (Join-Path $PSScriptRoot "sync_monster_ai_zh_tw_folder.ps1")

Copy-Item -Force $enReadme $enBackup
try {
    Copy-Item -Force $zhReadme $enReadme

    Push-Location $root
    git add README.md .gitignore "Monster-ai Zh-Tw/" `
        scripts/sync_monster_ai_zh_tw_folder.ps1 scripts/publish_zh_tw_github.ps1
    $status = git status --porcelain
    if (-not $status) {
        Write-Host "No changes to commit."
    } else {
        git commit -m "docs(zh-TW): Monster-ai Zh-Tw folder and publish scripts"
        git push zh-tw main
        Write-Host "Pushed to zh-tw main with Traditional Chinese README."
        git reset --hard HEAD~1
        Write-Host "Local main reset — English README unchanged for origin."
    }
} finally {
    if (Test-Path $enBackup) {
        Copy-Item -Force $enBackup $enReadme
        Remove-Item -Force $enBackup -ErrorAction SilentlyContinue
    }
    Pop-Location
}

Write-Host "English README restored at repo root."