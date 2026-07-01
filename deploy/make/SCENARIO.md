# Make.com — Monster AI 自動化情境

## 情境 A：Git Push → Cloudflare Pages 部署

1. **Trigger**：GitHub — Watch commits on `main`
2. **Action**：HTTP — POST `https://api.cloudflare.com/client/v4/accounts/{account}/pages/projects/monster-ai/deployments`
3. **Filter**：僅 `client/` 或 `functions/` 變更時觸發

## 情境 B：部署失敗通知

1. **Trigger**：Webhook — Cloudflare Pages build failure
2. **Action**：Discord / Email 通知
3. **Action**：HTTP POST Monster AI

```http
POST https://{TUNNEL}/api/integrations/make/deploy-hook
X-Make-Secret: {MAKE_WEBHOOK_SECRET}
Content-Type: application/json

{"event": "deploy_failed", "detail": "{{build.log}}"}
```

## 情境 C：品質數據同步

1. **Schedule**：每 6 小時
2. **HTTP GET**：`https://{TUNNEL}/api/integrations/status`
3. **Store**：Google Sheets 或 Airtable — 記錄 `mini_success.success_rate`

## 情境 D：Call Guard Tunnel 健康監控

1. **Schedule**：每 15 分鐘
2. **HTTP GET**：`https://{TUNNEL}/api/callguard/connection`
3. **Router**：若 `tunnel_url` 為空 → Discord/Email 告警「請執行 run-tunnel.bat」
4. **HTTP GET**：`https://{TUNNEL}/health` — 失敗則觸發 Sentry webhook

## 情境 E：APK 建置完成通知

1. **Trigger**：GitHub Actions / 本機 webhook `apk_built`
2. **Action**：更新 Wix Landing Page 下載連結（可選）
3. **HTTP POST**：`https://{TUNNEL}/api/integrations/make/deploy-hook`

```json
{"event": "callguard_apk_ready", "version": "1.2.0", "sha256": "..."}
```

## 環境變數

| 變數 | 用途 |
|------|------|
| `MAKE_WEBHOOK_SECRET` | 驗證 `/api/integrations/make/deploy-hook` |
| `CLOUDFLARE_API_TOKEN` | Pages 部署 API |
| `TUNNEL_URL` | 本機 Monster AI 公開網址（Call Guard App 填入同一 URL） |
| `MONSTER_TUNNEL_URL` | Dify workflow 變數 |