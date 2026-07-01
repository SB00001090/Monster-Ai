# Mini Monster AI v1.0

**Developed by Suckbob** — 縮小化、無審查、高成功率 R18+ 圖像生成，與 Monster AI 生態雙向整合。

## 一鍵安裝

```powershell
python scripts/install_mini_monster_ai.py
# 或
apps\mini_monster_ai\run-mini.bat
```

## 專案結構

```
monster_ai/modules/mini/          # 核心模組
  prompts.py                      # R18+ 模板與 Negative Prompt
  multilingual.py                 # 多語言提示詞
  workflow_builder.py             # 輕量 ComfyUI workflow
  workflows/mini_sdxl_*.json
  success_tracker.py              # 98% 成功率追蹤
  network_learning.py             # 可選網絡學習
  service.py                      # MiniMonsterService

monster_ai/api/mini.py            # REST API
monster_ai/web/static/mini/       # Neon Cyberpunk UI
data/mini/                        # 指標、同意書、快取
scripts/install_mini_monster_ai.py
```

## API

| 端點 | 說明 |
|------|------|
| `GET /api/mini/info` | 版本、模板、成功率 |
| `POST /api/mini/generate` | R18+ 生成 |
| `POST /api/mini/optimize` | 多語言提示詞優化 |
| `POST /api/mini/feedback` | 成功/失敗回饋 |
| `GET /api/mini/success` | 成功率統計 |
| `POST /api/mini/network/consent` | 網絡學習同意 |

UI: http://127.0.0.1:7860/mini/index.html

## 與 Monster AI 整合

- 共用 `ImageService`、品質評分、`ImageKnowledgeLearner`
- 成功/失敗圖寫入 `data/quality/` → 觸發 LoRA 訓練
- `share_with_monster_ai: true` 同步學習引擎 evolution log
- 共用 ComfyUI、Ollama、自修復 orchestrator

## 98% 路線圖（至 2026/09/01）

| 階段 | 時間 | 目標成功率 | 重點 |
|------|------|------------|------|
| P0 | 現在 | 70%+ | 模板 + 品質重試 + 負向詞 |
| P1 | +4 週 | 85% | image_knowledge 標籤自動套用 |
| P2 | +8 週 | 92% | anti_collapse LoRA + 用戶回饋 |
| P3 | +12 週 | 96% | ADetailer/局部重修（ComfyUI 節點擴展） |
| P4 | 2026/09/01 | **98%+** | 合成數據 + 專用 LoRA fine-tune |

## 測試

```powershell
python -m pytest tests/test_mini_monster_ai.py -q
```