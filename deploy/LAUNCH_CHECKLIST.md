# Monster AI 上架 Checklist

Developed by Suckbob | Monster AI

## 5 分鐘快速公開

- [ ] `python main.py` 運行中（:7860）
- [ ] `pnpm dev` 或已 build `dist/public`
- [ ] `python scripts/deploy_cloudflare.py --tunnel` 取得 Tunnel URL
- [ ] Cloudflare Pages 設 `VITE_MONSTER_API_URL=<tunnel>`
- [ ] 驗證 `https://monster-ai.pages.dev/api/health` → ok
- [ ] 驗證 `/mini-studio` 生成 + 品質環顯示
- [ ] 驗證 `/ecosystem` 一鍵安裝
- [ ] 驗證 `/integrations` 狀態綠燈

## 整合工具（可選）

- [ ] Dify：匯入 `deploy/dify/workflow_image_quality.json`，設 `DIFY_API_KEY`
- [ ] HF Space：部署 `deploy/huggingface/`，設 Tunnel secret
- [ ] Make：`deploy/make/SCENARIO.md` 三情境
- [ ] Sentry：`SENTRY_DSN` + `VITE_SENTRY_DSN`
- [ ] Jam：`VITE_JAM_TEAM_ID`
- [ ] Wix：`deploy/wix/LANDING.md` 結構
- [ ] Ahrefs：`deploy/ahrefs/SEO_PLAN.md` 關鍵字追蹤

## 測試

```bash
python -m pytest tests/test_mini_monster_ai.py tests/test_dify_bridge.py tests/test_integrations_api.py tests/test_commercial.py -q
```

## 商業

- [ ] `POST /api/commercial/trial/start` 啟動 7 日試用
- [ ] 區域定價 `GET /api/commercial/pricing?region=HK`
- [ ] Wix 付費 CTA 連結含 `?ref=wix`

## 法律

- [ ] 用戶確認 18+ Age Verification
- [ ] Mini / Ecosystem 免責聲明已閱
- [ ] Likeness 僅用授權參考圖