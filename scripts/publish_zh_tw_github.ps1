# Publish Guardian Ai full tree + Traditional Chinese README to Monster-Ai-ZH-TW
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$zhReadme = Join-Path $root "Monster-ai Zh-Tw\README.md"
$enReadme = Join-Path $root "README.md"
$enBackup = Join-Path $env:TEMP "guardian-ai-readme-en-backup.md"

if (-not (Test-Path $zhReadme)) {
    throw "Missing $zhReadme"
}

& (Join-Path $PSScriptRoot "sync_monster_ai_zh_tw_folder.ps1")

Copy-Item -Force $enReadme $enBackup
try {
    Copy-Item -Force $zhReadme $enReadme

    Push-Location $root
    git add README.md "Monster-ai Zh-Tw/" `
        scripts/sync_monster_ai_zh_tw_folder.ps1 scripts/publish_zh_tw_github.ps1
    $status = git status --porcelain
    if ($status) {
        git commit -m "docs(zh-TW): Guardian Ai Traditional Chinese README sync"
    }
    git push zh-tw HEAD:main --force-with-lease
    Write-Host "Pushed to https://github.com/SB00001090/Monster-Ai-ZH-TW"
    if ($status) {
        git reset --hard HEAD~1
    }
} finally {
    if (Test-Path $enBackup) {
        Copy-Item -Force $enBackup $enReadme
        Remove-Item -Force $enBackup -ErrorAction SilentlyContinue
    }
    Pop-Location
}

Write-Host "English README restored. Clone: git clone https://github.com/SB00001090/Monster-Ai-ZH-TW.git"
