# 電池優化與通知減少方案

**Monster AI Call Guard v1.2.0** · Developed by Suckbob

## 設計原則

| 項目 | 策略 |
|------|------|
| 來電分析 | 僅在 `CallScreeningService` 觸發時運算 |
| 遠端分析 | 僅當本機 score ≥ 60 且未拒接時才呼叫 Tunnel |
| 背景服務 | `START_STICKY` + 低優先級通知 channel |
| 網路同步 | WorkManager 6h 威脅庫 + 30min 健康探測（需網路） |
| Tunnel 離線 | 使用本機 `threat_db.json` 快取，不輪詢 |

## 通知策略

- **常駐通知**：僅「背景保護已啟動」一則（Android 前景服務要求）
- **攔截通知**：可選，預設關閉高頻 toast
- **連線狀態**：僅 UI 內顯示，不推播（除非從 OFFLINE→CONNECTED）

## 電池設定建議

1. App 首次啟動會請求「忽略電池最佳化」（可選）
2. 勿使用持續 GPS（防盜模式才啟用位置）
3. `ConnectionHealthWorker` 使用 `NetworkType.CONNECTED` 約束，無網路不喚醒

## 與 Whocall 差異

- 無雲端號碼查詢 API — 僅連**您自己的** Monster AI
- 無公開留言板 — 減少背景上傳
- 信任分數 + 共識 ≥3 票才採納封鎖