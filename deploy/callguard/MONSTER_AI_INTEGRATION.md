# Monster AI 後端整合方式

**Developed by Suckbob | Monster AI Call Guard**

## 模組對應

| 元件 | 路徑 | 職責 |
|------|------|------|
| CallGuard API | `monster_ai/api/callguard.py` | REST 端點 |
| 評分引擎 | `monster_ai/protection/callguard/engine.py` | 本機規則 + LLM 深度分析 |
| 信任分數 | `monster_ai/protection/callguard/rules.py` | `trust_score = 100 - risk_score` |
| 匿名共識 | `monster_ai/protection/callguard/consensus.py` | ≥3 票、無留言板 |
| Tunnel 部署 | `run-tunnel.bat` / `scripts/deploy_cloudflare.py` | 公開 HTTPS |
| Web UI | `client/` → Cloudflare Pages | `VITE_MONSTER_API_URL` |

## 啟動順序

```bat
python main.py
run-tunnel.bat
```

`data/callguard/tunnel_url.txt` 自動由 deploy 腳本寫入。

## config.yaml

```yaml
protection:
  callguard:
    enabled: true
    connection_mode: cloudflare_tunnel
    tunnel_url_file: ./data/callguard/tunnel_url.txt
    consensus_min_votes: 3
    public_comment_board: false
```

## Dify 橋接

`monster_ai/api/dify.py` 可將 workflow 結果 POST 至 `/api/callguard/report`。

## Sentry

`integrations.sentry_dsn` — 後端異常 + Web UI `client/src/lib/sentry.ts`。

## Hugging Face

Dify workflow 節點 `hf_classify` 使用輕量模型；可替換為自訓練 spam 分類 LoRA。