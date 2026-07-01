# Monster Guardian AI 上架 Checklist

Developed by Suckbob | Monster Guardian AI

## 核心功能

- [ ] `GET /api/guardian/training/status` → `encrypted: true`, `plaintext_forbidden: true`
- [ ] 好圖/爛圖存為 `.mgtrain`（`data/guardian/training_vault/`）— 無明文 PNG/JSON
- [ ] `POST /api/guardian/training/migrate` 將舊 `quality/good|bad` 轉為加密
- [ ] 訓練金鑰綁定 MonsterLock 指紋或 Android Keystore
- [ ] 雲端 sync `training_vault` bundle 為端到端密文
- [ ] `GET /api/guardian/status` → `no_tailscale: true`, `no_qr_code: true`
- [ ] `GET /api/guardian/disclaimer` 含「可能性無法退款」
- [ ] Google / GitHub OAuth 登入後可 `sync/upload` + `sync/download`
- [ ] 錯誤觸發 `errors/report` 回傳 `fix_suggestion` + `code_snippet`
- [ ] `learning/supervise` 回傳 Grok `priorities`
- [ ] `quality/gate` score < 0.70 → `fail`
- [ ] `oc/protect` 產生 `MGA-` 浮水印

## 連接與部署

- [ ] `python scripts/deploy_cloudflare.py --tunnel` 取得 HTTPS URL
- [ ] `MONSTER_TUNNEL_URL` 寫入 `data/callguard/tunnel_url.txt`
- [ ] Android `TunnelConnection.kt` 拒絕 Tailscale / IP
- [ ] USB：`scripts/callguard/install-apk-adb.ps1` 安裝最新 APK
- [ ] **無 QR Code**（`grep -ri qrserver` 為空）

## 整合

- [ ] Dify：匯入 `deploy/dify/workflow_guardian.json`
- [ ] Sentry：`SENTRY_DSN` + `VITE_SENTRY_DSN`
- [ ] Make：deploy 成功 → Slack 通知
- [ ] HF Space：`deploy/huggingface/`
- [ ] Wix Landing + Ahrefs SEO

## 商業

- [ ] 7 日試用 `POST /api/commercial/trial/start`
- [ ] 區域定價 HKD 388 / TWD 999 / USD 29–49

## 測試

```bash
python -m pytest tests/test_guardian_platform.py tests/test_guardian_training_vault.py tests/test_callguard_connection.py -q
```

## 法律

- [ ] 18+ Age Verification（React）
- [ ] Guardian 免責聲明不可被 config 關閉
- [ ] PRIVACY_POLICY.md 更新 Cloudflare Tunnel 說明