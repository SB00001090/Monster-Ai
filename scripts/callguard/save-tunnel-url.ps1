# 從 cloudflared 輸出擷取並儲存 Tunnel URL（手動貼上）
param([string]$Url = "")
$dir = Join-Path $PSScriptRoot "..\..\data\callguard"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$out = Join-Path $dir "tunnel_url.txt"
if (-not $Url) {
    Write-Host "用法: .\save-tunnel-url.ps1 -Url 'https://your-name.trycloudflare.com'"
    exit 1
}
$Url = $Url.Trim().TrimEnd('/')
Set-Content -Path $out -Value $Url -Encoding UTF8
Write-Host "[OK] 已儲存: $out"
Write-Host "Cloudflare Pages → VITE_MONSTER_API_URL / MONSTER_TUNNEL_URL:"
Write-Host "  $Url"