# Guardian Ai — 主規格（2026/09/01）

**Developed by Suckbob | Guardian Ai**

前身：Monster Guardian AI（**Call Guard 已完全移除**；遠端連線僅 Cloudflare Tunnel HTTPS 或 USB adb reverse）

---

## 1. 系統架構總覽

見 [`ARCHITECTURE.md`](ARCHITECTURE.md)。核心層：

| 層 | 元件 | 路徑 |
|----|------|------|
| 客戶端 | React Web UI · Android · Discord Guard | `client/` · `apps/` |
| API | FastAPI :7860 + Node tRPC :3000 | `monster_ai/` · `server/` |
| Guardian | 加密 · 同步 · OC · 學習 · Backstory | `monster_ai/modules/guardian/` |
| 整合 | Dify · Sentry · Make · HF · Jam | `deploy/dify/` · `monster_ai/api/integrations.py` |
| 連線 | Cloudflare Tunnel（無 Tailscale/QR） | `run-tunnel.bat` |

---

## 2. 增強版角色背景故事生成器

**超越 Easy-Peasy.AI：** 本地 LLM + 結構化 JSON + OC 指紋閘道 + 多模態提示。

**API：** `POST /api/guardian/backstory/generate`

```json
{
  "card": { "name", "personality", "worldview", "description" },
  "owner_id": "oauth-sub",
  "theme": "成熟、敏感或虛構主題",
  "ephemeral": true,
  "multimodal": true
}
```

**流程：**
1. 正規化 OC 欄位 → `content_hash`
2. `find_similar` 比對既有指紋 → 碰撞則 `blocked: true`
3. `repair.generate` 產出六段結構（失敗則模板 fallback）
4. `embed_watermark` + 儲存指紋
5. 回傳 `image_prompt_suggested` / `voice_tone_suggested`
6. `ephemeral: true` 時不持久化原始 prompt

**模組：** `monster_ai/modules/guardian/backstory.py`

---

## 3. 訓練檔案加密

- 格式：`.mgtrain`（AES-256-GCM）
- 路徑：`data/guardian/training_vault/{good,bad,template,prompt,lora}/`
- 金鑰：HKDF(MonsterLock 指紋 + 可選 passphrase)
- 禁止明文：`encrypt_quality_assets: true`
- 訓練：`decrypt_asset_to_memory()` → 用完即清
- 雲端：`training/export` → `sync/upload` bundle=`training_vault`

---

## 4. OC 反抄襲

- 文字：canonical JSON → SHA-256 `content_hash` + owner salt
- 圖片（規劃 G4）：pHash + embedding 比對
- 浮水印：`MGA-XXXXXXXX` in `extensions.monster_guardian`
- `network_learning_allowed: false` 預設
- API：`POST /api/guardian/oc/protect`

---

## 5. 聊天區安全

- `ChatVault`：AES-256-GCM（`.mgvault`）≈ SQLCipher
- Ephemeral：記憶體 session，關閉 wipe
- 反監聽（Android 規劃）：`RECORD_AUDIO` 前景服務偵測
- 防截圖：敏感模式浮水印 overlay
- API：`POST /api/guardian/vault/message`

---

## 6. 固定免責聲明

硬編碼：`monster_ai/modules/guardian/disclaimer.py` — **不可被 config 覆寫**

要點：模糊主題描述 · **可能性無法退款** · 完整原始實作僅開發者持有

API：`GET /api/guardian/disclaimer?locale=zh-TW`

---

## 7. 雲端同步

1. Google/GitHub OAuth（`server/_core/oauth.ts`）
2. 用戶 passphrase（≥8 字）→ HKDF → AES-256-GCM
3. Bundle：`oc_cards` · `chat_sessions` · `preferences` · `training_vault`
4. 儲存：`data/guardian/cloud/{provider}/{user_hash}/` 僅密文
5. 換機：`sync/download` + 相同 passphrase

---

## 8. 錯誤回報 + Grok 監督

```
Error → client autoErrorReporter / Sentry
     → POST /api/guardian/errors/report
     → fix_suggestion + code_snippet
     → ErrorLearningStore
     → POST /api/guardian/learning/supervise
     → GrokSupervisor priorities + bias_warnings
```

---

## 9. Dify Workflows

| 檔案 | 用途 |
|------|------|
| `workflow_guardian.json` | 全棧：免責→OC→訓練vault→品質→vault→chat→錯誤→監督 |
| `workflow_callguard_trust.json` | 信任分數（CallGuard 已取消 UI，API 保留） |
| `workflow_image_quality.json` | 圖片品質 <70% 重試 |
| `workflow_multimodal.json` | RP + 圖 + 音訊編排 |

---

## 10. Cloudflare Tunnel + USB APK

- `run-tunnel.bat` → `deploy_cloudflare.py --tunnel`
- URL → `data/callguard/tunnel_url.txt` + `MONSTER_TUNNEL_URL` 啟動載入
- **無** Tailscale · **無** QR Code
- USB：`install-apk-adb.bat` + `adb reverse tcp:7860`

---

## 11. GitHub Repo 要點

Repo：`SB00001090/Guardian-Ai`

README 需含：Guardian API 表 · 加密訓練說明 · Tunnel 部署 · 免責聲明連結 · 開發者標示

---

## 12. 路線圖 2026/09/01

見 [`ROADMAP_20260901.md`](ROADMAP_20260901.md)

| 階段 | 日期 | 交付 |
|------|------|------|
| G1 | 2026/07 | Guardian API · 加密 vault · Backstory · Dify |
| G2 | 2026/08 | 全平台 sync UI · OAuth 按鈕 |
| G3 | 2026/08 | Sentry→Dify→patch 自動化 |
| G4 | 2026/09/01 | 98%+ 品質 · pHash likeness |

---

## 13. 測試與上架

**測試：**
```bash
pytest tests/test_guardian_platform.py tests/test_guardian_training_vault.py tests/test_guardian_backstory.py -q
```

**Checklist：** [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md)

- [ ] `training_encryption: true` · `plaintext_forbidden: true`
- [ ] `grep -ri tailscale` 為空（連線路徑）
- [ ] `grep -ri qrserver` 為空
- [ ] Tunnel health 200
- [ ] 免責聲明 API 不可關閉
- [ ] 7 日試用 + 一次性 IAP（`modules/commercial/trial.py`）