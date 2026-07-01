# MonsterCallGuard 側載安裝教學

**Developed by Suckbob | Monster AI Call Guard** · v1.2.0

純 APK 模式 · 無 Google Play · 無廣告 · **Cloudflare Tunnel 連線（唔使 IP）**

## 1. 下載 APK

- `dist/MonsterCallGuard-v1.2.0-signed.apk`
- 家中 Monster AI Dashboard 下載連結

## 2. 驗證 SHA256

```powershell
Get-FileHash dist\MonsterCallGuard-v1.2.0-signed.apk -Algorithm SHA256
```

## 3. 側載安裝

1. 傳 APK 到手機
2. **設定 → 安全性 → 安裝未知應用程式**
3. 安裝並開啟 App

## 4. 電腦端（必須）

```bat
python main.py
run-tunnel.bat
```

複製 `https://xxx.trycloudflare.com`

## 5. App 設定

| 步驟 | 操作 |
|------|------|
| 1 | 授予電話、通話紀錄、通知權限 |
| 2 | 貼上 **Cloudflare Tunnel URL**（完整 https://） |
| 3 | 儲存 → **測試連線** |
| 4 | 設為來電篩選 App |
| 5 | 啟動背景保護 |

**唔使輸入 IP · 唔用 Tailscale**

## 6. 疑難排解

| 問題 | 解法 |
|------|------|
| DNS 找不到 | URL 須為真實 `*.trycloudflare.com`，非 `xxx` 範例 |
| 連線失敗 | 確認 `main.py` + `cloudflared` 運行；重啟 tunnel 後更新 URL |
| 離線仍可用 | App 使用本機 threat-db 快取 |
| Tunnel 過期 | 執行 `run-tunnel.bat` 取得新 URL |

## 7. 建置 APK

```powershell
scripts\callguard\generate-keystore.ps1
scripts\callguard\build-release-apk.ps1
```