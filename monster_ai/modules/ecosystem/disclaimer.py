"""Network ecosystem install — privacy & legal notice."""
from __future__ import annotations

PRIVACY_ZH = """【Monster AI 一鍵網絡安裝 · 隱私與免責】

Developed by Suckbob | Monster AI

1. **網絡下載需您明確同意** — 將從 HuggingFace、GitHub、Ollama 等來源下載開源模型與擴展。
2. **R18+ 模組** — 僅供成年用戶本地私人使用；您對生成內容負全部責任。
3. **Likeness** — 僅可使用您有權的參考素材；禁止未授權模仿真實人物。
4. **匿名學習** — 可選上傳成功率/相似度統計，不含個人可識別資料。不爬取 Rule34 等第三方站點。
5. **加密** — 建議在可信網絡環境使用；可選 VPN/Tor（需自行配置）。
6. **商業** — 首 7 日免費試用；一次性付費永久解鎖。區域定價依香港/東南亞/美歐不同。
7. **Web3 隱私** — 核心運算本地優先；網絡操作可選、匿名化；資料僅存於您的機器。

點擊「同意並安裝」即表示您已閱讀並接受上述條款，且已年滿 18 歲。"""


def privacy_notice(locale: str = "zh-TW") -> dict[str, str]:
    if locale.startswith("en"):
        return {
            "locale": "en",
            "text": "Monster AI network install requires consent. Downloads from HF/GitHub/Ollama. "
            "Adult content local-only. You are responsible for lawful likeness use.",
        }
    return {"locale": locale, "text": PRIVACY_ZH}