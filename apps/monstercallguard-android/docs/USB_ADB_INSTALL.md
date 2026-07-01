# USB ADB 直接安裝 + 本機連線

**Developed by Suckbob | Monster AI Call Guard** · v1.3.0

## 原理

```
[Phone App] --http://127.0.0.1:7860--> [adb reverse] --> [PC main.py :7860]
```

- **唔使輸入 IP** — 手機用 localhost，由 `adb reverse` 轉發
- **唔用 Tailscale / QR Code**

## 一鍵安裝

```bat
install-apk-adb.bat
```

或：

```powershell
scripts\callguard\install-apk-adb.ps1
```

### 手機準備

1. 設定 → 開發人員選項 → **USB 偵錯** 開啟
2. USB 連接電腦 → 允許偵錯授權

### 電腦準備

1. `python main.py` 或 `start-callguard.bat`
2. 執行 `install-apk-adb.bat`

腳本會自動：
- 建置 APK（若 dist 無檔案）
- `adb install -r`
- `adb reverse tcp:7860 tcp:7860`

## App 雙模式

| 模式 | 條件 | 後端 URL |
|------|------|----------|
| USB 本機 | adb reverse 有效 | `http://127.0.0.1:7860` |
| Tunnel 遠端 | 已儲存 Tunnel URL | `https://xxx.trycloudflare.com` |

App 會**優先 USB**，拔掉 USB 或無 reverse 時自動用 Tunnel。

## 手動 ADB 指令

```bat
adb devices
adb install -r dist\MonsterCallGuard-v1.3.0-signed.apk
adb reverse tcp:7860 tcp:7860
```