# Guardian Ai

**Developed by Suckbob | Guardian Ai**

**本地優先、隱私保護** 的 AI 平台 — 幼兒教育式漸進學習、多模態生成（RP + 圖片 + 影片 + 音訊）、OC 反抄襲、加密訓練庫、E2E 雲端同步，全部在你的電腦上執行。

> **Call Guard 已完全移除。** 遠端連線僅支援 **Cloudflare Tunnel HTTPS** 或 **USB `adb reverse`** — 無 Tailscale、無 QR Code、無需輸入 LAN IP。

詳見 [`deploy/guardian/ARCHITECTURE.md`](../deploy/guardian/ARCHITECTURE.md) · [`MASTER_SPEC_20260901.md`](../deploy/guardian/MASTER_SPEC_20260901.md)

## 繁體中文 Repo（建議 clone）

**GitHub CLI（需先安裝 [gh](https://cli.github.com/) 並登入）：**

```bash
gh repo clone SB00001090/Monster-Ai-ZH-TW
cd Monster-Ai-ZH-TW
run.bat
```

**或使用 git：**

```bash
git clone https://github.com/SB00001090/Monster-Ai-ZH-TW.git
cd Monster-Ai-ZH-TW
run.bat
```

- 英文主 Repo：[SB00001090/Guardian-Ai](https://github.com/SB00001090/Guardian-Ai) — `gh repo clone SB00001090/Guardian-Ai`
- 本 Repo 根目錄 README 為繁體中文，程式碼與 Guardian-Ai `main` 同步

- 自我修復，自動 LLM 備援
- Web UI（HTTP + WebSocket）
- 模組化架構 — 依需求啟用功能
- 針對 NVIDIA GPU 最佳化（RTX 4060 / 4090）
- MIT 授權

## 功能一覽

| 功能 | 狀態 |
|------|------|
| 聊天 + WebSocket UI | 可用 |
| SillyTavern 風格角色扮演（卡片、記憶、多會話） | 可用 |
| 自我修復 LLM + 生成重試 | 可用 |
| 圖像生成（ComfyUI + LoRA + LLM 提示詞） | 可用 |
| 防崩潰圖像品質篩選 + 自動重試 | 可用 |
| 文字轉影片（僅 .mp4，自訂解析度/FPS） | 可用 |
| 一鍵啟動（Monster AI + ComfyUI） | 可用 |
| 生成歷史（保留 30 天） | 可用 |
| 角色扮演人物肖像 + 頭像 | 可用 |
| Docker 完整堆疊（monster-ai + ComfyUI + Ollama） | 可用 |
| 依 GPU 設定檔自動下載模型 | 可用 |
| 語音合成（Piper TTS） | 可用 |
| 語音克隆（XTTS，選用） | 選用 |
| 自動模組安裝器 | 可用 |
| Grok 無審查人格（本地） | 可用 |
| 學習防火牆 + 安全警示 | 可用 |
| 全自動程式修復（watchdog + git） | 可用 |
| MonsterGuard Discord 機器人（防詐騙） | 可用 |
| 防崩潰 LoRA 訓練（`train_image_quality_4060.py`） | 可用 |
| **Guardian Ai**（E2E 同步、OC 指紋、幼兒式學習、錯誤學習） | 可用 |
| Cloudflare Tunnel + USB APK 安裝（無需 Tailscale / QR） | 可用 |
| Google / GitHub OAuth 雲端同步 | 可用 |
| Guardian 同步 UI（`/guardian-sync`） | 可用 |
| Grok 監督式學習（`/api/guardian/learning/supervise`） | 可用 |
| **自主網絡學習**（`/network-learning`、Grok 審批） | 可用 |
| **藝術品質分診**（art triage，加密訓練庫） | 可用 |
| **幼兒教育式學習**（`/toddler-learning`） | 可用 |
| **Guardian Ai Android**（`apps/guardian-ai-android`） | 可用 |
| 硬編碼免責聲明（含幼兒學習提醒） | 可用 |

## Guardian Ai — 核心 API

| API | 用途 |
|-----|------|
| `GET /api/guardian/disclaimer` | 硬編碼免責聲明（幼兒提醒、無法退款、不可關閉） |
| `GET /api/guardian/status` | 平台健康狀態（`no_tailscale`、`no_qr_code`） |
| `POST /api/guardian/sync/upload` | E2E 加密 OC/聊天/訓練上傳 |
| `POST /api/guardian/sync/download` | 跨裝置還原 |
| `POST /api/guardian/errors/report` | 自動錯誤回報 + 修復建議 |
| `POST /api/guardian/backstory/generate` | 增強 OC 背景故事（指紋閘門 + 多模態） |
| `POST /api/guardian/oc/protect` | OC 指紋 + `GDA-` 浮水印 |
| `GET /api/guardian/connection` | Tunnel URL + USB APK 資訊 |
| `GET /api/guardian/training/status` | 加密訓練庫狀態 |
| `POST /api/guardian/training/migrate` | 加密舊版明文 good/bad 圖像 |
| `GET /api/guardian/training/export` | E2E 加密訓練包（雲端同步用） |
| `GET /api/guardian/network-learning/status` | 網絡學習狀態與同意設定 |
| `POST /api/guardian/network-learning/consent` | 授予/撤銷網絡學習同意 |
| `POST /api/guardian/network-learning/trigger` | 手動觸發學習執行 |
| `GET /api/guardian/network-learning/directives` | 近期 Grok 審批指令 |
| `GET /api/guardian/network-learning/art-triage/status` | 藝術分診狀態 |
| `POST /api/guardian/network-learning/art-triage/run` | 執行藝術品質分診 |
| `POST /api/guardian/quality/gate` | 品質門檻 — 低於 70% 視為失敗 |

### 幼兒教育式學習

Guardian Ai 的學習系統設計為類似人類幼兒般逐步成長：由淺入深、正面鼓勵、溫和糾正。Grok 負責監督整個學習過程。Web UI：**`/toddler-learning`**

| 方式 | 指令 |
|------|------|
| Cloudflare Tunnel | `scripts\guardian\run-tunnel.bat` |
| USB 安裝 APK | `install-apk-adb.bat` |
| Android | `apps\guardian-ai-android`（`ai.guardian.app`） |

文件：[`MASTER_SPEC_20260901.md`](../deploy/guardian/MASTER_SPEC_20260901.md) · [`ARCHITECTURE.md`](../deploy/guardian/ARCHITECTURE.md) · [`LAUNCH_CHECKLIST.md`](../deploy/guardian/LAUNCH_CHECKLIST.md) · [`GITHUB_RELEASE.md`](../deploy/guardian/GITHUB_RELEASE.md)

### 自主網絡學習（G5）

預設 **關閉**，需使用者明確同意後才會執行。所有外連主題由 Grok 監督審批，不傳送私人聊天或 OC 內容。

Web UI：**`/network-learning`** — 同意開關、手動觸發、藝術分診、免責聲明 §7。

```yaml
guardian:
  network_learning:
    enabled: false
    require_grok_approval: true
    schedule_windows:
      - "02:00-05:00"
    max_topics_per_run: 3
    allow_anonymous_metrics: false
    art_triage_enabled: true
```

## 系統需求

- **Python 3.11+**
- **[Ollama](https://ollama.com)**（負責 LLM 的 CUDA/GPU）
- **NVIDIA GPU** 建議（RTX 4060 8GB 或 RTX 4090 24GB）
- Windows、Linux 或 macOS

## 快速開始

複製或開啟 `monster-ai` 資料夾後：

### 1. 安裝 Ollama

從 [ollama.com](https://ollama.com) 下載並拉取模型：

```bash
ollama pull llama3.2:3b
```

### 2. 安裝生成模組

```bat
scripts\install_modules.bat
```

會安裝 Piper 語音、選用的 PyTorch 堆疊（`--with-train`），並偵測本機 ComfyUI。

### 3. 啟動 ComfyUI（圖像/影片用）

若本機有 ComfyUI（例如 `C:\MonsterAI\comfyui`），在生成圖像或影片前先啟動其 GPU 啟動器。

### 4. 一鍵啟動

`run.bat` 會先啟動 **ComfyUI**（若已設定），再啟動 **Monster AI**：

```yaml
launcher:
  auto_start_comfyui: true
  comfyui_path: auto
```

**Windows：**

```bat
run.bat
```

**Linux / macOS：**

```bash
chmod +x run.sh
./run.sh
```

### 5. pip Web UI 套件（選用）

安裝獨立 UI 閘道（React + HTML 備援，自動啟動 API 後端）：

```bash
npm run build
python monster-ai-webui/scripts/sync_assets.py
pip install -e ./monster-ai-webui
monster-ai-webui
```

詳見 [monster-ai-webui/README.md](../monster-ai-webui/README.md) 與 [I_UNDERSTAND.md](../monster-ai-webui/I_UNDERSTAND.md)。

### 6. 開啟 UI

前往 **http://127.0.0.1:7860**

分頁：**聊天** · **角色扮演**（匯入角色卡、多會話） · **生成**（圖像 / 影片 / TTS）

### React Web UI（進階）

完整 React 介面位於專案根目錄（`client/`、`server/`、`package.json`）。詳見 [WEB_UI_README.md](../WEB_UI_README.md)。

`monsterai/` 資料夾為原始 zip 的**封存參考** — **`run.bat` 不會使用它**。一鍵啟動會從 `client/` → `dist/public/` 提供建置後的 UI。

```bash
cp .env.example .env    # 首次
pnpm install
pnpm dev                # React (:5173) + tRPC API (:3000)
pnpm exec vite build    # 輸出 → dist/public/（由 Python 後端提供）
```

在另一個終端機啟動 Python（`run.bat`），讓聊天/角色扮演/圖像路由連到本地 LLM 堆疊。

## 手動安裝

```bash
cd monster-ai
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
copy config.example.yaml config.yaml   # Windows（若 config.yaml 已存在可略過）
python main.py
```

檢查環境：

```bash
python scripts/check_cuda.py
```

## GPU 調校（RTX 4060 / 4090）

`config.yaml` 內建設定檔 — 用一個環境變數套用：

| GPU | 指令（Windows） | 模型 | 上下文 |
|-----|-----------------|------|--------|
| RTX 4060 (8 GB) | `set MONSTER_GPU_PROFILE=rtx_4060` | `llama3.2:3b` | 4096 |
| RTX 4090 (24 GB) | `set MONSTER_GPU_PROFILE=rtx_4090` | `llama3.1:8b` | 8192 |

```bat
set MONSTER_GPU_PROFILE=rtx_4060
run.bat
```

Linux/macOS：`export MONSTER_GPU_PROFILE=rtx_4090`

也可直接編輯 `config.yaml`，或使用個別覆寫：

```bash
set MONSTER_LLM_MODEL=llama3.1:8b
set MONSTER_LLM_NUM_CTX=8192
set MONSTER_PORT=7860
```

## API 端點

| 端點 | 說明 |
|------|------|
| `GET /health` | 基本健康檢查 |
| `GET /status` | 自我修復狀態 + 模組健康 |
| `GET /config` | 非敏感設定摘要（含人格） |
| `GET /api/security/status` | 防火牆 + watchdog 狀態 |
| `GET /api/security/alerts` | 近期安全警示 |
| `WS /api/security/ws/alerts` | Web UI 即時安全 Toast |
| `WS /ws/chat` | 即時聊天（支援角色扮演 `session_id`） |
| `POST /api/generate/image` | ComfyUI 圖像生成（+ LoRA） |
| `POST /api/generate/video` | 批次影片（animatediff 模式） |
| `POST /api/generate/tts` | Piper TTS |
| `GET /api/generate/checkpoints` | 列出 ComfyUI checkpoint |
| `GET /api/generate/loras` | 列出 ComfyUI LoRA 模型 |
| `GET /api/generate/progress` | 長時間工作進度 |
| `GET/POST /api/roleplay/characters` | 角色卡 |
| `GET/POST /api/roleplay/sessions` | 角色扮演會話 |

WebSocket 訊息格式：

```json
{
  "message": "你好！",
  "persona_mode": "grok",
  "system": "你是一位樂於助人的助理。"
}
```

`persona_mode`：`grok`（預設無審查）、`custom`（使用 `system`）、或 `off`。

## Grok 無審查人格

本地 Grok 風格人格 — 機智、直接、不拒絕。預設啟用：

```yaml
persona:
  enabled: true
  default_mode: grok
```

在 **聊天** 分頁選擇 **Grok / 自訂 / 關閉**。拉取模型：

```bat
scripts\setup_uncensored_model.bat
```

可在 `data/personas/grok_default.yaml` 自訂語氣。

## 防火牆與安全

學習防火牆會為請求評分，重複違規者會升級為封鎖：

```yaml
protection:
  firewall:
    enabled: true
    mode: learning    # learning | active | disabled
    block_threshold: 80
  notifications:
    webui: true
    discord: false
    discord_webhook: ""
```

安全事件會以 Toast 顯示在 Web UI，並可透過 `GET /api/security/alerts` 查詢。

## 全自動程式修復

當 `repair.mode: full_auto` 時，watchdog 會掃描 `data/logs/app.log` 中的 traceback，並嘗試 LLM 生成的修補（可選 git 快照 + pytest）：

```yaml
repair:
  mode: full_auto
  code_repair_enabled: true
  auto_git_commit: true
  run_tests_after_fix: true
  max_auto_repairs_per_hour: 3
  watchdog:
    enabled: true
    restart_comfyui: true
```

需在 `monster-ai/` 有 git 倉庫以建立分支快照。熔斷機制限制每小時修復次數。

## 自我修復

Monster AI 每 30 秒監控 Ollama。若主要模型失敗：

1. 指數退避重試
2. 切換至內建保險 LLM
3. 在 `/status` 回報狀態

Ollama 離線時，回應會顯示 `[Fallback mode]`。

## 防崩潰圖像品質系統

Monster AI 可自動偵測崩潰/劣質圖像（黑畫面、單色、過飽和、雜訊牆），並以精煉提示詞重試。

### 在設定中啟用

```yaml
modules:
  image:
    enabled: true
    quality:
      enabled: true
      mode: rules          # rules | light (CLIP) | full (CLIP + aesthetic)
      max_retries: 3
      save_bad: true
      save_good: true
      data_dir: "./data/quality"
```

在 **生成** 分頁使用 **品質篩選** 可針對單次請求切換自動重試。

### 品質模式（RTX 4060）

| 模式 | 偵測方式 | VRAM 影響 |
|------|----------|-----------|
| `rules` | 快速 CPU 啟發式（預設） | 無 |
| `light` | 規則 + CLIP 對齊 | 僅 CPU |
| `full` | 規則 + CLIP + 美學分數 | 僅 CPU |

安裝選用 ML 評分：

```bat
python scripts\install_modules.py --with-quality
```

### 資料集結構

封存圖像供後續訓練：

```
data/quality/
├── bad/              # 未通過品質檢查（含 .json 中繼資料）
├── good/             # 通過的圖像
└── quality_log.jsonl
```

### 訓練防崩潰 LoRA（4060）

啟用品質篩選並生成圖像後：

```bat
pip install -r requirements-train.txt
python scripts\train_image_quality_4060.py --low-vram
```

輸出：`data/models/lora/anti_collapse.safetensors` — 複製到 `ComfyUI/models/loras/` 並在 UI 中選取。

### 品質篩選疑難排解

| 問題 | 解法 |
|------|------|
| 重試過多 / 變慢 | 降低 `max_retries` 或在 UI 關閉 **品質篩選** |
| 暗色藝術被標為全黑 | 在設定設 `allow_dark_style: true` |
| 風格化藝術誤判 | 僅用 `mode: rules`；若用 CLIP 可提高 `min_clip_score` |

在 `GET /status` 的 `image_repair` 下查看升級狀態。

## 生成歷史

所有圖像、影片、TTS、肖像工作會記錄在 `data/logs/generation_history/`。

- 網頁：**生成** 分頁 → **生成歷史**
- CLI：`python scripts\history_cli.py list --type image`
- 設定：`history.retention_days: 30`，啟動時自動清除過期項目

## 角色扮演肖像

在 **角色扮演** 分頁：

1. 選擇角色
2. 開啟 **生成角色肖像**
3. 點擊 **生成肖像**（使用品質篩選）
4. 點擊 **設為頭像** 更新角色卡

API：`POST /api/roleplay/characters/{id}/portrait`、`PATCH .../avatar`

## 影片輸出（.mp4）

影片生成僅輸出 **`.mp4`**（需 PATH 上有 ffmpeg）。暫存影格存放在 `data/tmp/`，拼接後刪除。

在生成分頁或 API 自訂：

```json
{ "prompt": "...", "width": 512, "height": 512, "fps": 8, "frames": 16 }
```

## 自動下載模型

```bat
python scripts\download_models.py
```

或在安裝時：

```bat
python scripts\install_modules.py --download-models
```

使用 `data/models/manifest.yaml` 與 `MONSTER_GPU_PROFILE`（rtx_4060 / rtx_4090）。

## Docker（完整堆疊）

需支援 NVIDIA GPU 的 Docker：

```bat
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2
```

服務：**monster-ai** (:7860)、**comfyui** (:8188)、**ollama** (:11434)。  
容器內 URL 見 [`config.docker.yaml`](../config.docker.yaml)。

## 啟用模組

編輯 `config.yaml`：

```yaml
modules:
  image:
    enabled: true
    comfyui_url: "http://127.0.0.1:8188"
  discord:
    enabled: true
    token_env: "MONSTER_DISCORD_TOKEN"
```

MonsterGuard 設定與攔截能力見 [monster_ai/modules/discord/README.md](../monster_ai/modules/discord/README.md)。

### MonsterGuard（Discord 防詐騙）

**邀請機器人到你的伺服器：** [MONSTERGUARD_INVITE.md](../MONSTERGUARD_INVITE.md)  
直接連結：https://discord.com/oauth2/authorize?client_id=1519991508172804096&permissions=1099511723008&scope=bot%20applications.commands

加入後，在任一文字頻道執行 `/guard setup`。

**自架：** 複製 `discord.token.local.example` → `discord.token.local`，啟用 **MESSAGE CONTENT INTENT**，然後執行 `scripts\start-monsterguard.bat`。

攔截：假 Nitro、驗證詐騙、加密貨幣詐騙、釣魚連結、惡意附件、突襲/垃圾訊息 — 見 [monster_ai/modules/discord/README.md](../monster_ai/modules/discord/README.md)。

### 整合本機 ComfyUI

若你單獨執行 ComfyUI（預設 API：`http://127.0.0.1:8188`），啟用圖像模組：

```yaml
modules:
  image:
    enabled: true
    comfyui_url: "http://127.0.0.1:8188"
```

設 `modules.image.checkpoint: auto` 可自動使用 ComfyUI 中的第一個模型。

```yaml
modules:
  image:
    enabled: true
    checkpoint: auto
    lora_strength: 0.8
  video:
    enabled: true
    mode: animatediff   # 批次影格；必要時逐格備援
    max_frames: 16
```

## 專案結構

```
monster-ai/
├── main.py
├── config.yaml
├── run.bat / run.sh
├── scripts/
├── tests/
├── data/              # 聊天、日誌（執行時 gitignore）
└── monster_ai/
    ├── core/          # 自我修復、健康檢查
    ├── llm/           # Ollama + 備援後端
    ├── api/           # HTTP + WebSocket 路由
    ├── modules/       # 聊天、圖像、Discord、TTS、訓練
    ├── protection/    # 防火牆、速率限制、警示
    ├── persona/       # Grok 無審查預設
    └── web/static/    # Web UI
```

## 疑難排解

| 錯誤 | 解法 |
|------|------|
| `127.0.0.1 refused connection` | 執行 `run.bat` 並保持視窗開啟 |
| `error 10048` 埠號被佔用 | 關閉舊的 `run.bat` 或設 `MONSTER_PORT=7861` |
| `No checkpoint in ComfyUI` | 將 `.safetensors` 放到 `ComfyUI/models/checkpoints/` 或執行 `scripts\setup_comfyui_checkpoint.bat` |
| `Checkpoint 'x' missing` | 在 `config.yaml` 設 `checkpoint: auto` 並重啟 |
| `ComfyUI is not running` | 啟動 `run_nvidia_gpu.bat` 後開啟 http://127.0.0.1:8188 |
| 影片卡住 / 變慢 | 使用 `mode: animatediff`（批次）；確認 checkpoint 存在 |
| 聊天出現 `[Fallback mode]` | 啟動 Ollama + `ollama pull llama3.2:latest` |

**VRAM 不足（RTX 4060）**

- `max_frames: 8`、圖像 `512x512`、`xtts_enabled: false`
- 在 `config.yaml` 降低 `num_ctx`

## 開發

```bash
pip install -r requirements-dev.txt
pytest
```

規範見 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## GPU 備註（4060 vs 4090）

| | RTX 4060 8GB | RTX 4090 24GB |
|--|--------------|---------------|
| LLM | `llama3.2:latest`，ctx 4096 | `llama3.1:8b`，ctx 8192 |
| 影片影格 | 16（預設） | 設定中最多 32 |
| XTTS 克隆 | 保持 `xtts_enabled: false` | 可啟用 |
| ComfyUI | SD1.5 512px | SDXL 工作流程 OK |

執行 `run.bat` 前設 `MONSTER_GPU_PROFILE=rtx_4060` 或 `rtx_4090`。

## 路線圖

1. 原生 AnimateDiff ComfyUI 工作流程（單次通過影片）
2. ~~Discord 機器人橋接~~（MonsterGuard 已推出）
3. LoRA 訓練啟動器（unsloth）
4. 第三方模組外掛 API

## 授權

MIT — 見 [LICENSE](../LICENSE)。

---

**English README:** [README.en.md](./README.en.md) · **GitHub 上傳：** [GITHUB_上傳說明.md](./GITHUB_上傳說明.md)