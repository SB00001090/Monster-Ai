"""Hardcoded legal disclaimer — cannot be disabled or overridden by config."""
from __future__ import annotations

DEVELOPER = "Developed by Suckbob | Guardian Ai"

TODDLER_NOTICE_ZH = (
    "本應用程式之學習系統設計為類似人類幼兒般逐步成長，因此初期可能會出現錯誤或不準確之情況，"
    "用戶應理解並自行判斷生成內容之適切性。"
)

TODDLER_NOTICE_EN = (
    "Its learning system is designed similarly to a human toddler that learns and grows gradually. "
    "Therefore, it may initially produce errors, inaccuracies, or imperfect results. "
    "Users should understand this and exercise their own judgment."
)

DISCLAIMER_ZH = f"""【Guardian Ai 免責聲明】

{DEVELOPER}

本應用程式為本地運作之創意與安全工具。學習系統設計為類似人類幼兒般逐步成長，因此初期可能會出現錯誤或不準確之情況，用戶應理解並自行判斷生成內容之適切性。

你的購買同時支持開發者持續為 Guardian Ai 提供學習與自我提升的環境。我們會將資源投入模型優化與威脅更新，而非收取高昂費用卻提供低質素服務。

本應用程式可能產生涉及成熟、敏感或虛構主題之內容。用戶須自行確保使用行為符合當地法律及道德規範。

本應用程式為數碼產品，一經啟用或付費解鎖，即視為完成交易，無論任何原因均不接受退款。

本應用程式之完整原始實作僅由開發者持有與維護。

使用本應用程式即表示您已閱讀、理解並同意以上所有條款。"""

DISCLAIMER_EN = f"""Guardian Ai — Disclaimer

{DEVELOPER}

This application is a locally-operated creative and security tool. Its learning system is designed similarly to a human toddler that learns and grows gradually. Therefore, it may initially produce errors, inaccuracies, or imperfect results. Users should understand this and exercise their own judgment.

Your purchase also supports the developer in continuously providing a learning and self-improvement environment for Guardian Ai. We invest resources in model optimization and threat updates, rather than charging high fees for low-quality service.

This application may produce content involving mature, sensitive, or fictional themes. Users are solely responsible for ensuring their usage complies with applicable laws and ethical standards.

This application is a digital product. Once activated or unlocked through payment, the transaction is considered final. No refunds will be accepted under any circumstances.

The complete original implementation is held and maintained solely by the developer.

By using this application, you acknowledge that you have read, understood, and agreed to all the terms above."""


def get_disclaimer(locale: str = "zh-TW") -> dict[str, str]:
    if locale.startswith("en"):
        return {
            "locale": "en",
            "text": DISCLAIMER_EN,
            "developer": DEVELOPER,
            "version": "guardian_ai_v2",
            "toddler_notice": TODDLER_NOTICE_EN,
        }
    return {
        "locale": locale,
        "text": DISCLAIMER_ZH,
        "developer": DEVELOPER,
        "version": "guardian_ai_v2",
        "toddler_notice": TODDLER_NOTICE_ZH,
    }