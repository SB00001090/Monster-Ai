# Cloudflare Tunnel 設定 — Monster AI Call Guard

**Developed by Suckbob | Monster AI Call Guard**

## 架構

```
[Android App] ──HTTPS──► [*.trycloudflare.com] ──cloudflared──► [127.0.0.1:7860 main.py]
[Web UI]      ──HTTPS──► [monster-ai.pages.dev]  ──VITE_MONSTER_API_URL──► 同上 Tunnel
```

- **唔使輸入 IP**
- **完全唔用 Tailscale**
- 所有請求走 **HTTPS**（TLS 由 Cloudflare 終止）

## 電腦端步驟

### 1. 啟動 Monster AI 後端

```bat
cd C:\MonsterAI\monster-ai
python main.py
```

確認：`http://127.0.0.1:7860/health` → `{"status":"ok",...}`

### 2. 啟動 Quick Tunnel

```bat
run-tunnel.bat
```

或：

```bat
python scripts\deploy_cloudflare.py --tunnel
```

複製輸出中的 URL，例如：

```
https://requirements-controversy-length-pam.trycloudflare.com
```

### 3. 儲存 URL（可選）

```powershell
scripts\callguard\save-tunnel-url.ps1 -Url "https://xxx.trycloudflare.com"
```

### 4. 查詢連線狀態

```powershell
scripts\callguard\show-connection.ps1
```

## Android App 設定

1. 安裝 `dist/MonsterCallGuard-v1.2.0-signed.apk`
2. 開啟 App → **Cloudflare Tunnel URL** 欄位
3. 貼上完整 `https://xxx.trycloudflare.com`（**勿加 :7860**）
4. 按 **儲存 Tunnel URL** → **測試連線**
5. 設為來電過濾 App → 啟動背景保護

## 連線範例（Kotlin / Retrofit）

```kotlin
// TunnelConnection.normalizeUrl() 驗證 URL
val baseUrl = "https://xxx.trycloudflare.com/"

val client = OkHttpClient.Builder()
    .connectTimeout(8, TimeUnit.SECONDS)
    .readTimeout(12, TimeUnit.SECONDS)
    .addInterceptor(RetryInterceptor(maxRetries = 3))
    .build()

val api = Retrofit.Builder()
    .baseUrl(baseUrl)
    .client(client)
    .addConverterFactory(ScalarsConverterFactory.create())
    .build()
    .create(MonsterApiService::class.java)

// 健康檢查
val health = client.newCall(
    Request.Builder().url("${baseUrl}health").get().build()
).execute()

// 來電分析
val body = JSONObject()
    .put("number", "+85291234567")
    .put("display_name", "財務公司")
    .put("deep", true)
    .toString()
    .toRequestBody("application/json".toMediaType())

client.newCall(
    Request.Builder()
        .url("${baseUrl}api/callguard/analyze")
        .post(body)
        .build()
).execute()
```

## 自動重連與離線快取

| 機制 | 說明 |
|------|------|
| `RetryInterceptor` | 瞬斷重試 3 次，指數退避 |
| `ConnectionHealthWorker` | 每 30 分鐘背景探測 `/health` |
| `threat_db.json` 快取 | Tunnel 離線時仍可用本機規則庫 |
| 連線狀態 UI | CONNECTED / DEGRADED / OFFLINE |

## 注意事項

- Quick Tunnel **無 SLA**，重啟 cloudflared 後 URL 會變
- 生產環境建議使用 [Named Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- `config.yaml` → `web.cors_origins` 加入 `https://monster-ai.pages.dev`