# GitHub Releases APK 分發

**Developed by Suckbob | Monster AI Call Guard**

## 為何用 GitHub Releases（唔用 QR Code）

| 方案 | 安全性 |
|------|--------|
| QR Code | 可能洩露 APK/Tunnel URL，公共場所易被掃描 |
| GitHub Releases | 固定域名、SHA256 校驗、版本追溯 |

## 一鍵流程

```powershell
# 1. 建置
scripts\callguard\build-release-apk.ps1

# 2. 驗證
Get-FileHash dist\MonsterCallGuard-v1.2.0-signed.apk -Algorithm SHA256

# 3. 發布（需 gh CLI）
scripts\callguard\publish-github-release.ps1 -Version 1.2.0
```

## 下載連結

- **Releases 頁：** https://github.com/SB00001090/Monster-Ai/releases/latest
- **直接下載：**  
  `https://github.com/SB00001090/Monster-Ai/releases/download/v1.2.0/MonsterCallGuard-v1.2.0-signed.apk`

## config.yaml

```yaml
protection:
  callguard:
    github_releases_page: https://github.com/SB00001090/Monster-Ai/releases/latest
    # 留空則自動從 github_releases_page 推導 apk_download_url
    apk_download_url: ""
```

## App 連線（建置後）

1. 從 GitHub Releases 下載 APK
2. 電腦 `run-tunnel.bat` 取得 Tunnel URL
3. App 手動貼上 `https://xxx.trycloudflare.com`
4. 測試連線 → 啟動保護