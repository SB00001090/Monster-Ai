# Monster AI Call Guard — 測試與上架 Checklist

**Developed by Suckbob | Monster AI Call Guard** · v1.2.0

## 本機後端

- [ ] `python main.py` → `/health` OK
- [ ] `run-tunnel.bat` → 取得 `https://*.trycloudflare.com`
- [ ] `scripts/callguard/show-connection.ps1` → Tunnel reachable
- [ ] `/api/callguard/status` → `enabled: true`
- [ ] `/api/callguard/connection` → `no_tailscale: true`

## Android APK

- [ ] `scripts/callguard/build-release-apk.ps1` 成功
- [ ] `scripts/callguard/publish-github-release.ps1` 上傳 GitHub Releases
- [ ] SHA256 記錄於 `dist/*.sha256`
- [ ] **無 QR Code**（Web UI、build 腳本、App 均無）
- [ ] App 僅顯示 **Cloudflare Tunnel URL** 欄位（無 IP）
- [ ] `grep -ri tailscale` 僅剩拒絕邏輯／文件說明「已移除」
- [ ] 測試連線成功
- [ ] 來電篩選角色已授予
- [ ] 背景保護啟動後通知極少（僅狀態變更）
- [ ] 離線時仍可用快取 threat-db

## 功能驗證

- [ ] 高風險號碼 → 自動拒接
- [ ] 匿名回報僅上傳 hash + 分類
- [ ] ≥3 票共識後更新 `hash_blocklist`
- [ ] **無公開留言板** UI/API
- [ ] `trust_score` 於 analyze 回應中返回
- [ ] 7 日試用 / 一次性付費流程

## 整合

- [ ] Dify workflow `deploy/dify/workflow_callguard_trust.json` 已匯入
- [ ] Make 情境 B/C 可收到部署通知
- [ ] Sentry DSN 已設定（Web + 後端）
- [ ] Cloudflare Pages `VITE_MONSTER_API_URL` = Tunnel URL
- [ ] `web.cors_origins` 含 pages.dev

## 隱私與合規

- [ ] `PRIVACY_POLICY.md` 已更新（Tunnel only）
- [ ] `PRIVACY_DISCLAIMER.md` 免責聲明可見
- [ ] Google Play 資料安全表單已填
- [ ] 防盜背景位置有獨立開關與告知

## 上架

- [ ] 側載：`install-callguard.bat` 一鍵流程
- [ ] Play Console：內部測試軌道
- [ ] Ahrefs / Wix Landing Page（可選，2026 Q3）