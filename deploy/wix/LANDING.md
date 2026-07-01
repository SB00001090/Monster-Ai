# Monster AI — Wix Landing Page Guide

Developed by Suckbob | Monster AI

## Structure

1. **Hero** — Neon preview GIF + headline「本機 AI 創作平台」
   - CTA: `https://monster-ai.pages.dev?ref=wix`

2. **Features** — RP / 圖 / 影片 / 音訊 / Likeness / 98% 品質追蹤
   - Links: `/mini-studio`, `/ecosystem`, `/chat`

3. **How it works**
   - 一鍵安裝 → Tunnel → 開始創作
   - CTA: `https://monster-ai.pages.dev/ecosystem`

4. **Pricing** — 7 日免費試用 + 一次性永久解鎖
   - 香港 HKD 388 · 台灣 TWD 999 · 東南亞 USD 29 · 美國 USD 49 · 歐盟 EUR 45
   - API: `GET /api/commercial/pricing?region=HK`
   - CTA: `https://monster-ai.pages.dev/ecosystem?ref=wix`

5. **Demo** — Embed HF Space iframe

6. **Trust** — 18+ disclaimer, privacy, Suckbob credit

7. **SEO (Ahrefs)** — 見 `deploy/ahrefs/SEO_PLAN.md`
   - 目標詞：local AI generator、ComfyUI web UI、IP-Adapter likeness
   - UTM：`?ref=wix&utm_source=ahrefs`

## Wix Custom Code (Head)

```html
<script>
  window.MONSTER_APP_URL = "https://monster-ai.pages.dev";
</script>
```

## All CTAs

Use `https://monster-ai.pages.dev` — never host the main app on Wix.