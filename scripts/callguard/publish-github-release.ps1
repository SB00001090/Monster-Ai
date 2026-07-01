# 上傳 MonsterCallGuard APK 至 GitHub Releases（無 QR Code）
param(
    [string]$Version = "1.2.0",
    [string]$Repo = "Suckbob/monster-ai",
    [string]$ProjectRoot = "",
    [switch]$Draft
)

$ErrorActionPreference = "Stop"
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
$apkName = "MonsterCallGuard-v$($tag.TrimStart('v'))-signed.apk"
$apkPath = Join-Path $ProjectRoot "dist\$apkName"
$hashPath = "$apkPath.sha256"

if (-not (Test-Path $apkPath)) {
    Write-Error "APK not found: $apkPath — run build-release-apk.ps1 first"
}

$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    Write-Host "安裝 GitHub CLI: winget install GitHub.cli" -ForegroundColor Yellow
    Write-Host "手動上傳: $apkPath" -ForegroundColor Yellow
    Write-Host "Tag: $tag" -ForegroundColor Yellow
    Write-Host "URL: https://github.com/$Repo/releases/new?tag=$tag" -ForegroundColor Cyan
    exit 1
}

$notes = @"
Monster AI Call Guard $tag

- Cloudflare Tunnel HTTPS 連線（唔使 IP）
- 已移除 Tailscale 同所有 QR Code
- 信任分數 + 匿名 hash 回報（無公開留言板）
- Developed by Suckbob | Monster AI Call Guard
"@

$args = @(
    "release", "create", $tag,
    "--repo", $Repo,
    "--title", "Monster Call Guard $tag",
    "--notes", $notes,
    $apkPath
)
if ($hashPath -and (Test-Path $hashPath)) { $args += $hashPath }
if ($Draft) { $args += "--draft" }

& gh @args
Write-Host "`n[OK] https://github.com/$Repo/releases/tag/$tag" -ForegroundColor Green
Write-Host "APK URL: https://github.com/$Repo/releases/download/$tag/$apkName" -ForegroundColor Cyan