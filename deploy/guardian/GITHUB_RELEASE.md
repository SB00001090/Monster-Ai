# Guardian Ai — GitHub Release 描述模板

**Developed by Suckbob | Guardian Ai**

複製以下內容至 [GitHub Releases](https://github.com/SB00001090/Guardian-Ai/releases) 建立新版本。

---

## Release title

```
Guardian Ai v{VERSION}
```

## Release body

```markdown
## Guardian Ai v{VERSION}

**Developed by Suckbob | Guardian Ai**

### 新功能

- 幼兒教育式學習系統 — 由淺入深、正面鼓勵、溫和糾正
- Grok 監督整個學習週期（`/api/guardian/learning/supervise`）
- 自主網絡學習 + 藝術品質分診（好圖 / 爛圖 / 真藝術）
- OC 反抄襲指紋 + `GDA-` 不可見浮水印
- 訓練檔案全面 AES-256-GCM 加密（`.mgtrain`，禁止明文）
- E2E 雲端同步（Google / GitHub OAuth + passphrase）
- 硬編碼免責聲明（含幼兒學習提醒、無法退款條款）

### 已移除

- **Call Guard 全部功能**（來電篩選、反盜、威脅資料庫）
- Tailscale 連線
- QR Code 配對

### 安裝

| 平台 | 方式 |
|------|------|
| 桌面 | `run.bat` → http://127.0.0.1:7860 |
| 遠端 | Cloudflare Tunnel — `scripts\callguard\run-tunnel.bat`，手動貼上 HTTPS URL |
| Android | GitHub Releases APK + USB `scripts\callguard\install-apk-adb.ps1` |

### 商業模式

- 7 日免費試用：`POST /api/commercial/trial/start`
- 一次性付費解鎖（區域定價：HKD 388 / TWD 999 / USD 29–49）

### 文件

- [ARCHITECTURE.md](deploy/guardian/ARCHITECTURE.md)
- [MASTER_SPEC_20260901.md](deploy/guardian/MASTER_SPEC_20260901.md)
- [LAUNCH_CHECKLIST.md](deploy/guardian/LAUNCH_CHECKLIST.md)

### 免責聲明

`GET /api/guardian/disclaimer?locale=zh-TW` — 不可被 config 關閉。
```

## Repo description（GitHub About 欄）

```
Guardian Ai — local-first AI platform with toddler-style learning, OC anti-plagiarism, encrypted training vault, E2E sync. Developed by Suckbob | Guardian Ai. Call Guard removed.
```

## Topics（建議）

```
guardian-ai, local-ai, privacy, encryption, oc-character, multimodal-ai, cloudflare-tunnel, dify, self-healing
```