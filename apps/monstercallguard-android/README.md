# Monster AI Call Guard (Android)

**Developed by Suckbob | Monster AI Call Guard**

Whocall 式來電辨識 + 自動封鎖 · 本地優先 · **Cloudflare Tunnel HTTPS** 連線家中 Monster AI。

## 專案結構（v1.2.0 — 已移除 Tailscale）

```
apps/monstercallguard-android/
├── app/src/main/java/ai/monster/callguard/
│   ├── CallGuardApp.kt              # Application 入口
│   ├── ProtectionState.kt           # 攔截計數 / 鎖網狀態
│   ├── network/
│   │   ├── ConnectionManager.kt     # Tunnel 連線、重試、離線快取
│   │   ├── TunnelConnection.kt        # URL 驗證（僅 HTTPS trycloudflare）
│   │   ├── HomeMonsterClient.kt     # OkHttp API 客戶端
│   │   ├── MonsterApiService.kt     # Retrofit 介面
│   │   ├── RetryInterceptor.kt        # 指數退避重試
│   │   └── ThreatFeedClient.kt      # 威脅庫 CDN 備援
│   ├── engine/
│   │   ├── LocalThreatEngine.kt     # 本機規則評分
│   │   └── RemoteAnalyzer.kt        # Tunnel 深度分析
│   ├── report/
│   │   └── AnonymousReportBuilder.kt # 匿名 hash 回報
│   ├── guardian/          # E2E 雲端同步（與 Web /guardian-sync 互通）
│   ├── sync/
│   │   ├── SyncScheduler.kt         # WorkManager 排程
│   │   ├── ThreatDbSyncWorker.kt    # 威脅庫同步
│   │   └── ConnectionHealthWorker.kt # 30min 健康探測
│   ├── service/
│   │   ├── CallGuardForegroundService.kt
│   │   └── CallScreeningServiceImpl.kt
│   ├── ui/screens/HomeScreen.kt     # Tunnel URL + 連線狀態
│   └── billing/                     # 7 日試用 + 一次性付費
├── docs/TUNNEL_SETUP.md
├── PRIVACY_POLICY.md
└── build.gradle.kts
```

## 快速開始

### 電腦

```bat
python main.py
run-tunnel.bat
```

### 手機

1. 安裝 APK：`dist/MonsterCallGuard-v1.2.0-signed.apk`
2. 貼上 `https://xxx.trycloudflare.com`
3. 測試連線 → 設為來電過濾 → 啟動保護

詳見 [docs/TUNNEL_SETUP.md](docs/TUNNEL_SETUP.md)

## 連線原則

| 允許 | 禁止 |
|------|------|
| `https://*.trycloudflare.com` | Tailscale / `100.x.x.x` |
| Named Tunnel 自訂網域 | 手動輸入 LAN IP |
| 離線 threat-db 快取 | 公開留言板 |

## 建置 APK

```bat
scripts\callguard\build-release-apk.bat
```

（雙擊 `.bat` 唔會閃退；日誌：`dist\build-apk-log.txt`）