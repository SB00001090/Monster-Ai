# Android ↔ Guardian 雲端同步

Developed by Suckbob | Monster Guardian AI

## 功能

Android App（Monster Call Guard v1.3.1+）與 Web `/guardian-sync` 使用**相同 Guardian API** 與 bundle 格式：

| Bundle | Android | Web |
|--------|---------|-----|
| `preferences` | Tunnel URL、保護開關 | 主題、Tunnel URL |
| `oc_cards` | 佔位（Web 為主） | 完整角色卡 |
| `chat_sessions` | 佔位 | 完整對話 |
| `training_vault` | 密文轉發 | 密文上傳 |

## 使用流程

1. 電腦 `run.bat` + `run-tunnel.bat`
2. App 設定 Tunnel URL 或 USB `adb reverse`
3. App → **Monster Guardian 雲端同步**
4. 輸入與 Web 相同的 `provider` / `provider_sub` / passphrase
5. **加密上傳** 或 **下載並還原 Preferences**

## 背景同步

`GuardianSyncWorker` 每 12 小時上傳 `preferences`（需勾選「記住 passphrase」）。

## 金鑰

- `GuardianCredentials` — EncryptedSharedPreferences（Android Keystore）
- `TrainingVaultKeyManager` — 訓練 vault 指紋

## Dev 測試

Web dev-login：

- Google → `dev_google_user`
- GitHub → `dev_github_user`

Android 使用相同 `provider_sub` + passphrase 即可互通。