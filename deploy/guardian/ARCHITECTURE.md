# Guardian Ai — 系統架構

Developed by Suckbob | Guardian Ai

## 總覽

```
┌─────────────────────────────────────────────────────────────────────┐
│  Client (React / Guardian Ai Android / Discord Guard)              │
│  Google · GitHub OAuth │ AES vault key │ Ephemeral chat              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTPS (Cloudflare Tunnel)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Monster AI FastAPI (:7860)                                          │
│  /api/guardian/*  sync · vault · oc · errors · quality · supervise   │
│  /api/roleplay/*  OC + chat                                          │
│  /api/learning/*  curriculum + feedback                              │
│  /api/heal/*      self-heal orchestrator                             │
└───────────────┬─────────────────────────────┬───────────────────────┘
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────────────┐
│  Local encrypted stores    │   │  Integrations                      │
│  data/guardian/cloud/      │   │  Dify · Sentry · Make · HF · Jam   │
│  chat_vault · oc_fp        │   │  Ahrefs · Wix · GitHub Releases    │
└───────────────────────────┘   └───────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Grok Supervisor (persona/grok.py + /learning/supervise)             │
│  優先級排序 · 偏差警告 · 策略建議                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 0. 訓練檔案加密（核心）

| 資產類型 | 儲存格式 | 加密 |
|----------|----------|------|
| 好圖 / 爛圖 | `.mgtrain` | AES-256-GCM |
| prompt 範例 | `.mgtrain` | AES-256-GCM |
| 訓練模板 | `.mgtrain` | AES-256-GCM |
| LoRA 訓練資料 | `.mgtrain` | AES-256-GCM |
| 品質日誌 | 加密 vault index | 無明文 `quality_log.jsonl` |

**金鑰推導：**
```
HKDF-SHA256(
  salt = random per device,
  material = hw:MonsterLock指纹 + optional pw:用户passphrase,
  info = "monster-guardian-training-v1"
)
```

- **桌面端**：MonsterLock 硬體指紋自動綁定（`bind_hardware_key: true`）
- **Android**：`TrainingVaultKeyManager.kt` — Android Keystore + EncryptedSharedPreferences
- **禁止明文**：`QualityStore` 在 `encrypt_quality_assets: true` 時只寫 `.mgtrain`
- **root / 複製防護**：磁碟上僅密文；解密僅在記憶體進行（`decrypt_asset_to_memory`）

路徑：`data/guardian/training_vault/{good,bad,template,prompt,lora}/`

## 1. 雲端同步 + 跨平台

| 層級 | 實作 |
|------|------|
| 身份 | Google / GitHub OAuth（Node `server/_core/oauth.ts`） |
| 加密 | 用戶 passphrase + OAuth sub → HKDF → AES-256-GCM |
| 儲存 | `data/guardian/cloud/{provider}/{user_hash}/*.json` 僅密文 |
| Bundle | `oc_cards` · `chat_sessions` · `preferences` · `training_vault` |

訓練檔案雲端同步流程：
1. `GET /api/guardian/training/export` → 取得已加密 bundle（仍為密文）
2. 再用 OAuth + passphrase 做第二層 E2E：`sync/upload` bundle_type=`training_vault`
3. 還原：`sync/download` → `POST /api/guardian/training/import`

換機流程：登入同一 OAuth → 輸入相同 passphrase → `POST /api/guardian/sync/download`

## 2. 自動錯誤回報

```
App Error → Sentry (optional) + tRPC errors.reportClientError
         → POST /api/guardian/errors/report
         → fix_suggestion + code_snippet
         → learning evolution log
         → Grok supervise (recurring patterns)
```

## 3. 學習系統

- `FailureAnalyzer` — 品質 < 70% 失敗模式
- `ErrorLearningStore` — 運行時錯誤案例
- `GrokSupervisor` — 規則 + LLM 策略指導
- Curriculum mode `cybersec` — 安全主題訓練

## 4. 聊天區安全

- AES-256-GCM vault（`chat_vault.py`）— SQLCipher 等效本地加密
- Ephemeral Chat 預設 — 記憶體會話，關閉即 wipe
- CrimeGuard 網絡鎖 — VPN/暗網偵測時阻斷外連學習

## 5. OC 反抄襲

- `generate_fingerprint` — 內容 hash + owner salt
- 浮水印 `MGA-XXXXXXXX` 寫入 `extensions.monster_guardian`
- `network_learning_allowed: false` 預設

## 6. 連接策略

- **僅** Cloudflare Tunnel HTTPS
- **已移除** Tailscale · QR Code · LAN IP 輸入
- USB `adb reverse` + `install-apk-adb.bat` 直裝 APK

## API 速查

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/guardian/status` | 平台狀態 |
| GET | `/api/guardian/disclaimer` | 硬編碼免責 |
| POST | `/api/guardian/sync/upload` | E2E 上傳 |
| POST | `/api/guardian/sync/download` | E2E 下載 |
| POST | `/api/guardian/errors/report` | 錯誤學習 |
| POST | `/api/guardian/learning/supervise` | Grok 監督 |
| POST | `/api/guardian/oc/protect` | OC 指紋 |
| POST | `/api/guardian/quality/gate` | 70% 門檻 |
| GET | `/api/guardian/connection` | Tunnel + USB 資訊 |