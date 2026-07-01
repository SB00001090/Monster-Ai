# Monster AI — Cloudflare 快速上架

Developed by Suckbob | Monster AI

## 架構

```
[用戶瀏覽器] → Cloudflare Pages (免費 *.pages.dev)
                    ↓ API / WebSocket
              Cloudflare Tunnel (加密)
                    ↓
         本機 Monster AI :7860 + Ollama + ComfyUI
```

## 方式 A：Dashboard 連接 Git（推薦）

1. 登入 https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. 選擇 repo：`SB00001090/Monster-Ai-Bot`
3. 建置設定（與 `deploy/cloudflare/pages-dashboard.json` 一致）：

| 欄位 | 值 |
|------|-----|
| Production branch | `main` |
| Build command | `pnpm install && pnpm build` |
| Build output directory | `dist/public` |
| Root directory | `/` |

4. **Environment variables**（Production + Preview）：
   - `VITE_MONSTER_API_URL` = 你的 Tunnel URL（例 `https://xxx.trycloudflare.com`）
   - `NODE_VERSION` = `20`

5. **Save and Deploy** → 取得 `https://monster-ai.pages.dev`

6. 本機 `config.yaml` 加入 CORS：
```yaml
web:
  cors_origins:
    - "https://monster-ai.pages.dev"
```

## 方式 B：Wrangler CLI 直接部署

```bat
python scripts\setup_cloudflare_pages.py --login
python scripts\setup_cloudflare_pages.py --build --deploy
```

或使用 API Token（免瀏覽器登入）：
```bat
set CLOUDFLARE_API_TOKEN=你的token
set CLOUDFLARE_ACCOUNT_ID=你的account_id
python scripts\setup_cloudflare_pages.py --build --deploy
```

## 方式 C：GitHub Actions 自動部署

在 GitHub repo → Settings → Secrets：
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Variables：
- `VITE_MONSTER_API_URL`

Push 到 `main` 即觸發 `.github/workflows/cloudflare-pages.yml`。

## 幾分鐘內公開（Checklist）

- [ ] `pnpm install && pnpm build`
- [ ] Git push → Cloudflare Pages 連接 repo，建置指令 `pnpm build`，輸出 `dist/public`
- [ ] Pages 環境變數 `VITE_MONSTER_API_URL` = Tunnel 網址
- [ ] 本機 `python main.py`（或 `run.bat`）
- [ ] `python scripts/deploy_cloudflare.py --tunnel` 取得 Tunnel URL
- [ ] 設定 `config.yaml` → `web.cors_origins` 加入你的 `*.pages.dev` 網址
- [ ] 瀏覽器開啟 `https://monster-ai.pages.dev`（或自訂網域）

## 一鍵腳本

```bat
python scripts\deploy_cloudflare.py --build
python scripts\deploy_cloudflare.py --tunnel
```

## 隱私

- 生成運算在本機；Tunnel 僅轉發 API
- R18+ 須年滿 18 歲；Likeness 僅限有權參考素材
- 網絡下載模組需用戶明確同意（Ecosystem 頁）