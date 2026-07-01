# Monster AI

A **local-first, open-source AI platform** — chat, roleplay, image generation, and more, running entirely on your machine.

> **Monster Guardian AI** — privacy-first security shell with E2E cloud sync (Google/GitHub), OC anti-plagiarism, auto error learning, and Grok-supervised evolution. See [`deploy/guardian/ARCHITECTURE.md`](deploy/guardian/ARCHITECTURE.md). Developed by Suckbob | Monster Guardian AI.

- Self-healing with automatic LLM fallback
- Web UI (HTTP + WebSocket)
- Modular architecture — enable features as you need them
- Optimized for NVIDIA GPUs (RTX 4060 / 4090)
- MIT licensed

## Features

| Feature | Status |
|---------|--------|
| Chat + WebSocket UI | Working |
| SillyTavern-style roleplay (cards, memory, sessions) | Working |
| Self-repair LLM + generation retry | Working |
| Image generation (ComfyUI + LoRA + LLM prompts) | Working |
| Anti-collapse image quality filter + auto-retry | Working |
| Text-to-video (.mp4 only, custom resolution/FPS) | Working |
| One-click launcher (Monster AI + ComfyUI) | Working |
| Generation history (30-day retention) | Working |
| Roleplay character portrait + avatar | Working |
| Docker full stack (monster-ai + ComfyUI + Ollama) | Working |
| Auto model download by GPU profile | Working |
| Voice synthesis (Piper TTS) | Working |
| Voice cloning (XTTS, optional) | Optional |
| Auto module installer | Working |
| Grok uncensored persona (local) | Working |
| Learning firewall + security alerts | Working |
| Full-auto code repair (watchdog + git) | Working |
| MonsterGuard Discord bot (anti-scam) | Working |
| Anti-collapse LoRA training (`train_image_quality_4060.py`) | Working |
| **Monster Guardian AI** (E2E sync, OC fingerprint, error learning) | Working |
| Cloudflare Tunnel + USB APK install (no Tailscale / QR) | Working |
| Google / GitHub OAuth cloud sync | Working |
| Grok-supervised learning (`/api/guardian/learning/supervise`) | Working |

## Monster Guardian AI

| API | Purpose |
|-----|---------|
| `GET /api/guardian/status` | Platform health |
| `POST /api/guardian/sync/upload` | E2E encrypted OC/chat upload |
| `POST /api/guardian/sync/download` | Cross-device restore |
| `POST /api/guardian/errors/report` | Auto error + fix suggestions |
| `POST /api/guardian/oc/protect` | OC fingerprint + watermark |
| `GET /api/guardian/connection` | Tunnel URL + USB APK info |
| `GET /api/guardian/training/status` | Encrypted training vault status |
| `POST /api/guardian/training/migrate` | Encrypt legacy plaintext good/bad images |
| `GET /api/guardian/training/export` | E2E encrypted training bundle for cloud sync |

Docs: [`deploy/guardian/ARCHITECTURE.md`](deploy/guardian/ARCHITECTURE.md) · [`LAUNCH_CHECKLIST.md`](deploy/guardian/LAUNCH_CHECKLIST.md)

## Requirements

- **Python 3.11+**
- **[Ollama](https://ollama.com)** (handles CUDA/GPU for LLMs)
- **NVIDIA GPU** recommended (RTX 4060 8GB or RTX 4090 24GB)
- Windows, Linux, or macOS

## Quick start

Clone or open the `monster-ai` folder, then:

### 1. Install Ollama

Download from [ollama.com](https://ollama.com) and pull a model:

```bash
ollama pull llama3.2:3b
```

### 2. Install generation modules

```bat
scripts\install_modules.bat
```

Installs Piper voices, optional PyTorch stack (`--with-train`), and detects local ComfyUI.

### 3. Start ComfyUI (for image/video)

If you have ComfyUI locally (e.g. `C:\MonsterAI\comfyui`), start its GPU launcher before generating images or video.

### 4. One-click launch

`run.bat` starts **ComfyUI** (if configured) then **Monster AI**:

```yaml
launcher:
  auto_start_comfyui: true
  comfyui_path: auto
```

**Windows:**

```bat
run.bat
```

**Linux / macOS:**

```bash
chmod +x run.sh
./run.sh
```

### 5. pip Web UI package (optional)

Install the standalone UI gateway (React + HTML fallback, auto-starts API backends):

```bash
npm run build
python monster-ai-webui/scripts/sync_assets.py
pip install -e ./monster-ai-webui
monster-ai-webui
```

See [monster-ai-webui/README.md](monster-ai-webui/README.md) and [I_UNDERSTAND.md](monster-ai-webui/I_UNDERSTAND.md).

### 6. Open the UI

Go to **http://127.0.0.1:7860**

Tabs: **Chat** · **Roleplay** (import character cards, multi-session) · **Generate** (image / video / TTS)

### React Web UI (advanced)

A full React interface lives at the project root (`client/`, `server/`, `package.json`). See [WEB_UI_README.md](WEB_UI_README.md).

The `monsterai/` folder is an **archived reference** from the original zip — **`run.bat` does not use it**. One-click launch serves the built UI from `client/` → `dist/public/`.

```bash
cp .env.example .env    # first time
pnpm install
pnpm dev                # React (:5173) + tRPC API (:3000)
pnpm exec vite build    # output → dist/public/ (served by Python backend)
```

Start Python (`run.bat`) in another terminal so chat/roleplay/image routes hit the local LLM stack.

## Manual setup

```bash
cd monster-ai
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
copy config.example.yaml config.yaml   # Windows (skip if config.yaml exists)
python main.py
```

Check your environment:

```bash
python scripts/check_cuda.py
```

## GPU tuning (RTX 4060 / 4090)

Built-in profiles in `config.yaml` — apply with one env var:

| GPU | Command (Windows) | Model | Context |
|-----|-------------------|-------|---------|
| RTX 4060 (8 GB) | `set MONSTER_GPU_PROFILE=rtx_4060` | `llama3.2:3b` | 4096 |
| RTX 4090 (24 GB) | `set MONSTER_GPU_PROFILE=rtx_4090` | `llama3.1:8b` | 8192 |

```bat
set MONSTER_GPU_PROFILE=rtx_4060
run.bat
```

Linux/macOS: `export MONSTER_GPU_PROFILE=rtx_4090`

You can also edit `config.yaml` directly or use individual overrides:

```bash
set MONSTER_LLM_MODEL=llama3.1:8b
set MONSTER_LLM_NUM_CTX=8192
set MONSTER_PORT=7860
```

## API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic health check |
| `GET /status` | Self-repair state + module health |
| `GET /config` | Non-sensitive config summary (includes persona) |
| `GET /api/security/status` | Firewall + watchdog status |
| `GET /api/security/alerts` | Recent security alerts |
| `WS /api/security/ws/alerts` | Live security toasts in Web UI |
| `WS /ws/chat` | Real-time chat (supports `session_id` for roleplay) |
| `POST /api/generate/image` | ComfyUI image generation (+ LoRA) |
| `POST /api/generate/video` | Batch video (animatediff mode) |
| `POST /api/generate/tts` | Piper TTS |
| `GET /api/generate/checkpoints` | List ComfyUI checkpoints |
| `GET /api/generate/loras` | List ComfyUI LoRA models |
| `GET /api/generate/progress` | Long job progress |
| `GET/POST /api/roleplay/characters` | Character cards |
| `GET/POST /api/roleplay/sessions` | Roleplay sessions |

WebSocket message format:

```json
{
  "message": "Hello!",
  "persona_mode": "grok",
  "system": "You are a helpful assistant."
}
```

`persona_mode`: `grok` (default uncensored), `custom` (uses `system`), or `off`.

## Grok uncensored persona

Local Grok-style persona — witty, direct, no refusals. Enabled by default:

```yaml
persona:
  enabled: true
  default_mode: grok
```

In the **Chat** tab, pick **Grok / Custom / Off**. Pull a model:

```bat
scripts\setup_uncensored_model.bat
```

Customize tone in `data/personas/grok_default.yaml`.

## Firewall & security

Learning firewall scores requests and escalates repeat offenders to bans:

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

Security events appear as toasts in the Web UI and at `GET /api/security/alerts`.

## Full-auto code repair

When `repair.mode: full_auto`, the watchdog scans `data/logs/app.log` for tracebacks and attempts LLM-generated patches (with optional git snapshot + pytest):

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

Requires a git repo in `monster-ai/` for branch snapshots. Circuit breaker limits repairs per hour.

## Self-repair

Monster AI monitors Ollama every 30 seconds. If the primary model fails:

1. Retries with exponential backoff
2. Falls back to a built-in insurance LLM
3. Reports status at `/status`

You'll see `[Fallback mode]` in responses when Ollama is offline.

## Anti-collapse image quality system

Monster AI can automatically detect collapsed/bad images (black frames, flat color, oversaturation, noise walls) and retry with refined prompts.

### Enable in config

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

In the **Generate** tab, use **Quality filter** to toggle auto-retry per request.

### Quality modes (RTX 4060)

| Mode | Detection | VRAM impact |
|------|-----------|-------------|
| `rules` | Fast CPU heuristics (default) | None |
| `light` | Rules + CLIP alignment | CPU only |
| `full` | Rules + CLIP + aesthetic score | CPU only |

Install optional ML scoring:

```bat
python scripts\install_modules.py --with-quality
```

### Dataset layout

Archived images are stored for later training:

```
data/quality/
├── bad/              # failed quality checks (+ .json metadata)
├── good/             # passed images
└── quality_log.jsonl
```

### Train anti-collapse LoRA (4060)

After generating images with quality filter enabled:

```bat
pip install -r requirements-train.txt
python scripts\train_image_quality_4060.py --low-vram
```

Output: `data/models/lora/anti_collapse.safetensors` — copy to `ComfyUI/models/loras/` and select in the UI.

### Troubleshooting quality filter

| Issue | Fix |
|-------|-----|
| Too many retries / slow | Lower `max_retries` or disable **Quality filter** in UI |
| Dark art flagged as black | Set `allow_dark_style: true` in config |
| False positives on stylized art | Use `mode: rules` only; raise `min_clip_score` if using CLIP |

Check escalation state at `GET /status` under `image_repair`.

## Generation history

All image, video, TTS, and portrait jobs are logged under `data/logs/generation_history/`.

- Web: **Generate** tab → **Generation history**
- CLI: `python scripts\history_cli.py list --type image`
- Config: `history.retention_days: 30` with auto purge on startup

## Roleplay portraits

In the **Roleplay** tab:

1. Select a character
2. Open **Generate character portrait**
3. Click **Generate portrait** (uses quality filter)
4. Click **Set as avatar** to update the character card

API: `POST /api/roleplay/characters/{id}/portrait`, `PATCH .../avatar`

## Video output (.mp4)

Video generation outputs **`.mp4` only** (requires ffmpeg on PATH). Temporary frames are stored in `data/tmp/` and deleted after stitching.

Customize in the Generate tab or API:

```json
{ "prompt": "...", "width": 512, "height": 512, "fps": 8, "frames": 16 }
```

## Auto-download models

```bat
python scripts\download_models.py
```

Or during install:

```bat
python scripts\install_modules.py --download-models
```

Uses `data/models/manifest.yaml` and `MONSTER_GPU_PROFILE` (rtx_4060 / rtx_4090).

## Docker (full stack)

Requires Docker with NVIDIA GPU support:

```bat
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2
```

Services: **monster-ai** (:7860), **comfyui** (:8188), **ollama** (:11434).  
Uses [`config.docker.yaml`](config.docker.yaml) for in-container URLs.

## Enabling modules

Edit `config.yaml`:

```yaml
modules:
  image:
    enabled: true
    comfyui_url: "http://127.0.0.1:8188"
  discord:
    enabled: true
    token_env: "MONSTER_DISCORD_TOKEN"
```

See [monster_ai/modules/discord/README.md](monster_ai/modules/discord/README.md) for MonsterGuard setup and intercept capabilities.

### MonsterGuard (Discord anti-scam)

**Invite the bot to your server:** [MONSTERGUARD_INVITE.md](MONSTERGUARD_INVITE.md)  
Direct link: https://discord.com/oauth2/authorize?client_id=1519991508172804096&permissions=1099511723008&scope=bot%20applications.commands

After joining, run `/guard setup` in any text channel.

**Self-hosting:** copy `discord.token.local.example` → `discord.token.local`, enable **MESSAGE CONTENT INTENT**, then `scripts\start-monsterguard.bat`.

Intercepts: fake Nitro, verification scams, crypto scams, phishing links, malware attachments, raid/spam — see [monster_ai/modules/discord/README.md](monster_ai/modules/discord/README.md).

### Integrating local ComfyUI

If you run ComfyUI separately (default API: `http://127.0.0.1:8188`), enable the image module:

```yaml
modules:
  image:
    enabled: true
    comfyui_url: "http://127.0.0.1:8188"
```

Set `modules.image.checkpoint: auto` to use the first model in ComfyUI automatically.

```yaml
modules:
  image:
    enabled: true
    checkpoint: auto
    lora_strength: 0.8
  video:
    enabled: true
    mode: animatediff   # batch frames; falls back to per-frame if needed
    max_frames: 16
```

## Project structure

```
monster-ai/
├── main.py
├── config.yaml
├── run.bat / run.sh
├── scripts/
├── tests/
├── data/              # chats, logs (gitignored at runtime)
└── monster_ai/
    ├── core/          # Self-repair, health
    ├── llm/           # Ollama + fallback backends
    ├── api/           # HTTP + WebSocket routes
    ├── modules/       # Chat, image, Discord, TTS, training
    ├── protection/    # Firewall, rate limits, alerts
    ├── persona/       # Grok uncensored presets
    └── web/static/    # Web UI
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `127.0.0.1 refused connection` | Run `run.bat` and keep the window open |
| `error 10048` port in use | Close old `run.bat` or set `MONSTER_PORT=7861` |
| `No checkpoint in ComfyUI` | Add `.safetensors` to `ComfyUI/models/checkpoints/` or run `scripts\setup_comfyui_checkpoint.bat` |
| `Checkpoint 'x' missing` | Set `checkpoint: auto` in `config.yaml` and restart |
| `ComfyUI is not running` | Start `run_nvidia_gpu.bat` then open http://127.0.0.1:8188 |
| Video stuck / slow | Use `mode: animatediff` (batch); ensure checkpoint exists |
| `[Fallback mode]` chat | Start Ollama + `ollama pull llama3.2:latest` |

**Out of VRAM (RTX 4060)**

- `max_frames: 8`, image `512x512`, `xtts_enabled: false`
- Lower `num_ctx` in `config.yaml`

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## GPU notes (4060 vs 4090)

| | RTX 4060 8GB | RTX 4090 24GB |
|--|--------------|---------------|
| LLM | `llama3.2:latest`, ctx 4096 | `llama3.1:8b`, ctx 8192 |
| Video frames | 16 (default) | up to 32 in config |
| XTTS clone | keep `xtts_enabled: false` | can enable |
| ComfyUI | SD1.5 512px | SDXL workflows OK |

Set `MONSTER_GPU_PROFILE=rtx_4060` or `rtx_4090` before `run.bat`.

## Roadmap

1. Native AnimateDiff ComfyUI workflow (single-pass video)
2. ~~Discord bot bridge~~ (MonsterGuard shipped)
3. LoRA training launcher (unsloth)
4. Plugin API for third-party modules

## License

MIT — see [LICENSE](LICENSE).