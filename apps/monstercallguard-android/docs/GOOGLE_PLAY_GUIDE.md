# Google Play 上架指南 — Monster Call Guard

**Developed by Suckbob | Monster AI Ecosystem**

## 1. 生成 AAB

```bash
cd apps/monstercallguard-android
gradlew.bat bundleRelease
```

產物：`app/build/outputs/bundle/release/app-release.aab`

## 2. Play Console 設定

### App 內容
- [ ] 隱私政策 URL（上傳 `PRIVACY_POLICY.md` 至 GitHub Pages 或網站）
- [ ] 資料安全表單：聲明收集位置（防盜）、電話（來電篩選）
- [ ] 背景位置聲明影片/說明（必填）

### 一次性產品
- Product ID: `monster_callguard_lifetime`
- 類型：In-app product (one-time)
- **區域定價建議：**
  - 香港 HKD 88
  - 台灣 TWD 299
  - 美國 USD 12.99
  - 印度 INR 低價 tier
  - 使用 Console **Price templates** + per-country override

### 試用說明
試用由 App 內 `TrialManager` 實現（7 日），**非** Play 訂閱試用。

## 3. Policy Checklist

| 項目 | 狀態 |
|------|------|
| Call screening 權限說明 | 必填於商店描述 |
| POST_NOTIFICATIONS | Android 13+ |
| ACCESS_BACKGROUND_LOCATION | 防盜功能 + 影片 |
| Billing permission | `com.android.vending.BILLING` |
| 無誤導性一次性付費描述 | 強調無訂閱 |
| targetSdk 34 | ✅ |
| 64-bit ABI | ✅ (bundle splits) |

## 4. 商店描述要點（中英）

**EN:** One-time purchase. 7-day free trial. Local AI call guard. Anti-theft with WiFi/GPS (no SIM required). Connects to your Monster AI at home.

**ZH:** 一次付費永久使用，無訂閱。7 日免費試用。本地 AI 來電守衛。防盜追蹤（拔出 SIM 仍可用 WiFi/GPS）。

## 5. 截圖 Placeholder

1. Home — neon dashboard + trial countdown
2. Paywall — regional price + lifetime unlock
3. Privacy — transparency dashboard
4. Anti-theft — SIM status + location toggle
5. Call block — rejected scam call notification

## 6. 內部測試軌道

1. Upload AAB to Internal testing
2. Add license testers
3. Verify billing with test card
4. Promote to Production