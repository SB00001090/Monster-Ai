# Monster Call Guard — Privacy Policy / 隱私政策

**Developed by Suckbob | Monster AI Call Guard**  
**Last updated:** 2026-06-30

---

## English

### Who we are
Monster Call Guard is published by Suckbob as part of the Monster AI ecosystem.

### Data we process
- **Call metadata** (hashed numbers, risk/trust scores) for local screening
- **Optional location** when anti-theft mode is enabled by you
- **SIM status** for theft detection
- **Cloudflare Tunnel URL** (stored locally on device)

### Where data lives
- **Local-first:** encrypted on your device (EncryptedSharedPreferences, Room DB)
- **Optional sync:** only to **your** Monster AI PC via **Cloudflare Tunnel HTTPS** — never to a central cloud
- **No public comment board:** reports upload hash + category only

### Who can see your data
- **You** — full access on device and Monster AI dashboard
- **Your Monster AI instance** — full access on your hardware
- **Developer (Suckbob)** — only anonymized or **consent-based** data for model tuning — **never sold**

### Third-party services
- **Google Play Billing** — purchase verification only
- **Cloudflare** — TLS tunnel transport (no call content stored by Cloudflare)
- **Sentry** (optional) — crash metadata if you enable Monster AI telemetry

### Background location
Used **only** when you enable anti-theft mode, disclosed in-app before activation.

---

## 繁體中文

### 資料處理
本 App 採**本地優先**架構。來電分析預設僅存於手機加密空間。匿名回報只上傳**號碼雜湊 + 分類**，**不設公開留言板**。

### 連線方式
僅透過您自架的 **Cloudflare Tunnel 公開 HTTPS URL** 連接家中 Monster AI。**不使用 Tailscale，不需輸入 IP。**

### 誰能查看
- **您本人**與您自架的 **Monster AI** 可查看完整資料
- **開發者 Suckbob** 僅在您明確同意後處理匿名化資料以改善模型，**不販售給第三方**

### 一次付費
透過 Google Play 一次性購買驗證，無訂閱、無自動續費。

---

## Disclaimer / 免責聲明

Monster Call Guard 為輔助工具，**不能取代警方或 ADCC 18222 官方渠道**。攔截結果僅供參考；請自行判斷並遵守香港法律。開發者不對誤攔或漏攔承擔法律責任。