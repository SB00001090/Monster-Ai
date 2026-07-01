# MonsterGuard v2.1 — Discord 反詐騙 Bot

**Developed by Suckbob | Monster AI Ecosystem**

MonsterGuard 是 Monster AI 內建的 Discord 伺服器保護 Bot，24/7 掃描文字頻道訊息，自動偵測並攔截常見詐騙。v2.1 新增 **Monster AI 動態自我介紹**（`/intro`、`/monsterai`、新成員歡迎）。

---

## English — MonsterGuard v2.0

MonsterGuard v2.0 is the Discord bridge for the Monster AI ecosystem. It provides anti-scam scanning, local LLM chat, and Monster CallGuard alert forwarding with **anti-disconnect resilience**.

### Anti-Disconnect (10 retries → standby)

1. Exponential backoff reconnect (5s → max 300s)
2. Max **10** attempts, then **standby mode** (stops auto-reconnect)
3. Heartbeat checks Discord latency + optional Monster AI `/api/status` ping
4. Discord Webhook / alert channel notifications on disconnect
5. Manual recovery: `/guard restart` or `POST /api/guard/restart`

### Monster AI Self-Intro (v2.1)

- `/intro` — dynamic personalized intro with live status (connection, blocks, CallGuard)
- `/monsterai` — alias; defaults to cyberpunk style
- **Styles:** `guardian` (formal), `cyberpunk` (humorous neon), `privacy` (zero-trust)
- **Auto welcome:** new members receive intro in system/mod/alert channel
- Requires **Server Members Intent** in Discord Developer Portal for `on_member_join`
- Uses local LLM via Monster AI `repair.generate()` with template fallback

### Slash commands (v2.1)

| Command | Description |
|---------|-------------|
| `/intro` | Monster AI dynamic self-introduction |
| `/monsterai` | Same as `/intro` (cyberpunk default) |
| `/status` | Global health dashboard (neon embed) |
| `/about` | Version + developer credit |
| `/ai` | Local LLM chat or scam analyze |
| `/callguard status` | CallGuard engine status |
| `/防盜` | Chinese alias for CallGuard |
| `/guard restart` | Restart bot (Manage Server) |
| `/guard logs` | Recent structured logs |

### Deployment modes

- **Embedded** (default): `python scripts/launch_monsterguard.py` — runs with Monster AI `main.py`
- **Standalone**: `python -m monster_ai.modules.discord.standalone`
- **Docker**: `deploy/monsterguard/docker-compose.yml`
- **PM2**: `deploy/monsterguard/ecosystem.config.js`
- **systemd**: `deploy/monsterguard/monsterguard.service`

### Monster CallGuard integration

1. Enable `protection.callguard` in `config.yaml`
2. Set `modules.discord.guard.callguard_bridge_enabled: true`
3. Set `MONSTERGUARD_ALERT_CHANNEL_ID` or `notify_channel_id`
4. Optional: `MONSTER_AI_CONNECT_CONSENT=1` for local AI link

### Security

- Local-first: data stays on your machine
- User consent required before Monster AI HTTP link (`monster_ai_consent_required`)
- Never commit `discord.token.local` or webhook URLs

---

## 中文 — MonsterGuard v2.0

## 可攔截的內容

| 類型 | 說明 | 範例 |
|------|------|------|
| 假 Nitro / Giveaway | 免費 Nitro、假禮物連結 | `discord-gift`、`free nitro`、`steamcommunlty` |
| 假驗證 / 帳號安全 | 騙取帳號或身分 | `verify your account`、假管理員招募表單 |
| Crypto / 投資詐騙 | 虛擬貨幣與假贈送 | 加倍投資、空投、助記詞、MrBeast 假活動 |
| 被盜帳號 DM 模式 | 好友帳號被盜後的話術 | 「這是你嗎？」、「看看我找到的」 |
| 惡意下載 / 遊戲詐騙 | 惡意附件與假虛寶 | `.exe` / `.apk` 附件、免費 Robux / V-Bucks |
| 釣魚連結 | 仿冒與黑名單網域 | Discord 仿冒網址、同形異義字、可疑 TLD |
| Raid / 大量洗版 | 機器人或集體 spam | 重複訊息、短時間大量發文、新帳號洗版 |

**行為風險訊號：** 新帳號發連結、緊迫感 + 免費承諾話術等。

**攔截後動作：** 警告 → 刪除訊息 → 通知管理員頻道 → 可選 mute / 隔離。

**目前不掃描：** 私信 (DM)、語音頻道、Bot 自身訊息。

> 完整說明定義於 [`guard/capabilities.py`](guard/capabilities.py)，Bot 內使用 `/guard features` 查看。

## 邀請 Bot（給伺服器管理員）

若使用官方營運的 MonsterGuard，直接點擊邀請連結：

👉 **[邀請 MonsterGuard 加入伺服器](https://discord.com/oauth2/authorize?client_id=1519991508172804096&permissions=1099511723008&scope=bot%20applications.commands)**

完整用戶說明見專案根目錄 **[MONSTERGUARD_INVITE.md](../../../MONSTERGUARD_INVITE.md)**。

加入後在頻道執行 `/guard setup` 即可啟用保護。

---

## 快速開始（自行架設）

### 1. 建立 Discord Application

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 建立 Application → Bot → 複製 **Token**
3. 啟用 **Privileged Gateway Intents → MESSAGE CONTENT INTENT**
4. OAuth2 → URL Generator：勾選 `bot` + `applications.commands`，權限建議 `Manage Messages`、`Read Message History`

### 2. 設定 Token（勿上傳 GitHub）

```bat
copy discord.token.local.example discord.token.local
notepad discord.token.local
```

將 Bot Token 貼在第一行，儲存。`discord.token.local` 已在 `.gitignore` 中排除。

### 3. 啟用模組

`config.yaml`（或從 `config.example.yaml` 複製）：

```yaml
modules:
  discord:
    enabled: true
    token_env: "MONSTER_DISCORD_TOKEN"
    guard:
      enabled: true
      mode: embedded
      protection_level: standard
      chat_bridge_enabled: true
```

### 4. 啟動

```bat
scripts\start-monsterguard.bat
```

或：

```bat
python scripts\launch_monsterguard.py
```

### 5. 邀請 Bot 加入伺服器（自行架設時）

自行架設請用 Developer Portal → OAuth2 → URL Generator 產生邀請連結。  
官方 Bot 邀請連結見 [MONSTERGUARD_INVITE.md](../../../MONSTERGUARD_INVITE.md)。

#### 加入後必做

1. **確認 Bot 在線** — 成員列表中 MonsterGuard 顯示綠點（需先啟動 `start-monsterguard.bat`）
2. **調整角色順序** — 伺服器設定 → 角色 → 將 MonsterGuard 角色拖到**高於**一般成員，低於伺服主／管理員
3. **完成設定** — 在任意文字頻道輸入：

```
/guard setup
```

4. 可選：輸入 `/guard features` 查看攔截清單，`/guard status` 確認運作中

#### 常見問題

| 問題 | 解法 |
|------|------|
| 邀請連結無效 | 確認 Application ID 正確、SCOPES 含 `bot` |
| Bot 離線 | 啟動 Monster AI + 檢查 `discord.token.local` |
| 無法刪除訊息 | Bot 角色需高於發訊者；需 **Manage Messages** 權限 |
| `/guard` 指令看不到 | 等 1–2 分鐘讓 Slash 同步；重啟 Bot |
| 掃描不到訊息 | Developer Portal → Bot → 開啟 **MESSAGE CONTENT INTENT** |

## Slash 指令

| 指令 | 說明 |
|------|------|
| `/intro` | Monster AI 動態自我介紹（可選風格） |
| `/monsterai` | 自我介紹別名（預設 cyberpunk） |
| `/status` | v2.1 全域健康儀表板 |
| `/about` | 版本與開發者資訊 |
| `/ai` | 本地 LLM 對話或詐騙分析 |
| `/callguard` `/防盜` | Monster CallGuard 狀態與報告 |
| `/guard setup` | 設定精靈（需管理伺服器） |
| `/guard features` | 查看可攔截的詐騙類型 |
| `/guard status` | Bot、重連、心跳、24h 攔截統計 |
| `/guard restart` | 重啟 Bot（待機模式恢復） |
| `/guard logs` | 結構化日誌（最近 20 條） |
| `/guard config` | 查看目前伺服器設定 |
| `/guard education` | 發送防詐教育訊息 |
| `/chat` | 與本地 Monster AI 對話（Chat Bridge） |
| `/report-scam` | 回報可疑訊息 |

## 防斷線設定（config.yaml）

```yaml
modules:
  discord:
    guard:
      max_reconnect_attempts: 10
      heartbeat_interval_seconds: 30
      notify_webhook_url: ""          # 或 MONSTERGUARD_WEBHOOK_URL
      notify_channel_id: 0            # 或 MONSTERGUARD_ALERT_CHANNEL_ID
      callguard_bridge_enabled: true
      monster_ai_consent_required: true
      welcome_intro_enabled: true
      welcome_intro_style: cyberpunk
```

### 新成員歡迎設定

1. Developer Portal → Bot → 啟用 **Server Members Intent**
2. 設定 `mod_channel_id`（`/guard setup`）或 `notify_channel_id` 作為歡迎頻道
3. 新成員加入時自動發送 Monster AI 介紹 embed

## 保護強度

| 等級 | 攔截門檻 | 動作 |
|------|----------|------|
| 輕度 `light` | 90 | 僅警告 |
| 標準 `standard` | 80 | 刪除 + 警告（推薦） |
| 嚴格 `strict` | 70 | 刪除 + mute 10 分鐘 |

## 專案結構

```
monster_ai/modules/discord/
├── bot.py                 # DiscordService + 防斷線層
├── constants.py           # v2.0 版本與品牌
├── guard/
│   ├── bot.py             # MonsterGuard Bot
│   ├── resilience/        # 重連、心跳、通知
│   ├── integration/       # Monster AI + CallGuard 橋接
│   ├── ui/embeds.py       # Neon cyberpunk embeds
│   ├── capabilities.py
│   ├── pipeline.py
│   └── cogs/
└── standalone/__main__.py

deploy/monsterguard/       # Docker / PM2 / systemd
```

## 測試

```bat
pytest tests/test_discord_self_heal.py tests/test_discord_reconnect.py tests/test_discord_heartbeat.py tests/test_discord_callguard_bridge.py tests/test_discord_intro.py -q
```

## 授權

MIT — 與 Monster AI 主專案相同。