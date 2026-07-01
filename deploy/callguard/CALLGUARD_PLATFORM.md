# Monster AI Call Guard — 完整平台指南

**Developed by Suckbob | Monster AI Call Guard** · v1.2.0

> 嚴格禁止：Tailscale · QR Code · 手動輸入 IP  
> 必須使用：Cloudflare Tunnel 公開 HTTPS URL

---

## 1. Android 專案結構（已移除 Tailscale + QR Code）

```
apps/monstercallguard-android/
├── app/src/main/java/ai/monster/callguard/
│   ├── network/
│   │   ├── ConnectionManager.kt      # 重連、離線快取、狀態
│   │   ├── TunnelConnection.kt       # URL 驗證（僅 HTTPS）
│   │   ├── HomeMonsterClient.kt      # OkHttp API
│   │   ├── MonsterApiService.kt      # Retrofit 介面
│   │   └── RetryInterceptor.kt       # 超時重試
│   ├── engine/                       # 本機 + 遠端分析、信任分數
│   ├── report/AnonymousReportBuilder.kt
│   ├── sync/
│   │   ├── ThreatDbSyncWorker.kt     # 6h 同步
│   │   └── ConnectionHealthWorker.kt # 30min 探測
│   ├── service/CallScreeningServiceImpl.kt
│   └── ui/screens/HomeScreen.kt      # 僅 Tunnel URL 欄位
├── docs/TUNNEL_SETUP.md
├── docs/API_INTEGRATION.md
└── PRIVACY_POLICY.md
```

**已刪除：** `LanDiscovery.kt`、Tailscale 設定欄位、LAN IP 輸入、所有 QR 相關程式

---

## 2. Cloudflare Tunnel 設定 + Android 連接範例

### 電腦端

```bat
python main.py
run-tunnel.bat
```

複製 `https://xxx.trycloudflare.com` → App 貼上 → 測試連線。

### Kotlin 範例

```kotlin
val baseUrl = "https://xxx.trycloudflare.com/"

val client = OkHttpClient.Builder()
    .connectTimeout(8, TimeUnit.SECONDS)
    .readTimeout(12, TimeUnit.SECONDS)
    .addInterceptor(RetryInterceptor(maxRetries = 3))
    .build()

// 健康檢查
client.newCall(Request.Builder().url("${baseUrl}health").get().build())
    .execute().use { /* status ok */ }

// 來電分析（含 trust_score）
val body = JSONObject()
    .put("number", "+85291234567")
    .put("display_name", "財務公司")
    .put("deep", true)
    .toString()
    .toRequestBody("application/json".toMediaType())

client.newCall(
    Request.Builder().url("${baseUrl}api/callguard/analyze").post(body).build()
).execute()
```

詳見 `apps/monstercallguard-android/docs/TUNNEL_SETUP.md`

---

## 3. APK 分發方案（GitHub Releases）

### 建置

```powershell
scripts\callguard\build-release-apk.ps1
```

輸出：
- `dist/MonsterCallGuard-v1.2.0-signed.apk`
- `dist/MonsterCallGuard-v1.2.0-signed.apk.sha256`
- `dist/callguard-release.json`

### 發布

```powershell
scripts\callguard\publish-github-release.ps1 -Version 1.2.0
```

需安裝 [GitHub CLI](https://cli.github.com/) 並 `gh auth login`。

### 下載連結格式

```
https://github.com/Suckbob/monster-ai/releases/download/v1.2.0/MonsterCallGuard-v1.2.0-signed.apk
```

**唔使用 QR Code** — 用戶從 Releases 頁面手動下載，避免 URL 洩露。

---

## 4. Dify Workflow

檔案：`deploy/dify/workflow_callguard_trust.json`

| 節點 | 功能 |
|------|------|
| `hf_classify` | Hugging Face 輕量 spam 分類 |
| `trust_calc` | `trust_score = 100 - risk_score` |
| `quality_gate` | score ≥ 70 才進入回報 |
| `submit_report` | POST hash + 分類至 Tunnel |
| `consensus_poll` | ≥3 票共識，無留言板 |

變數：`MONSTER_TUNNEL_URL=https://xxx.trycloudflare.com`

---

## 5. Make 自動化

檔案：`deploy/make/SCENARIO.md`

| 情境 | 觸發 | 動作 |
|------|------|------|
| A | Git push | Cloudflare Pages 部署 |
| B | 部署失敗 | Discord + Sentry 通知 |
| D | 每 15min | Tunnel `/health` 監控 |
| E | APK 建置完成 | 更新 Release 通知 |

---

## 6. 電池優化與通知

檔案：`deploy/callguard/BATTERY_AND_NOTIFICATIONS.md`

- 來電時才分析；遠端僅 score ≥ 60
- WorkManager 背景同步（非持續輪詢）
- 單一低優先級前景服務通知
- Tunnel 離線 → 本機 threat-db 快取

---

## 7. Monster AI 後端整合

檔案：`deploy/callguard/MONSTER_AI_INTEGRATION.md`

| API | 路徑 |
|-----|------|
| 健康 | `GET /health` |
| 分析 | `POST /api/callguard/analyze` |
| 回報 | `POST /api/callguard/report` |
| 共識 | `GET /api/callguard/consensus` |
| 連線 | `GET /api/callguard/connection` |
| Manifest | `GET /api/callguard/app-manifest` |

`config.yaml`:

```yaml
protection:
  callguard:
    connection_mode: cloudflare_tunnel
    tunnel_url_file: ./data/callguard/tunnel_url.txt
    github_releases_page: https://github.com/Suckbob/monster-ai/releases/latest
```

---

## 8. 隱私政策 + 免責聲明

檔案：`apps/monstercallguard-android/PRIVACY_POLICY.md`

- 本地優先、hash 匿名回報
- 無公開留言板、無 QR 傳輸 URL
- Cloudflare Tunnel HTTPS 至您自己的 PC
- 輔助工具，不取代 ADCC 18222

---

## 9. 測試與上架 Checklist

檔案：`deploy/callguard/LAUNCH_CHECKLIST.md`

重點：
- [ ] 無 Tailscale 殘留（`grep -ri tailscale`）
- [ ] 無 QR Code（`grep -ri qrserver`）
- [ ] Tunnel 連線 + 離線快取
- [ ] GitHub Release 上傳 + SHA256 驗證
- [ ] Dify / Make / Sentry 整合測試