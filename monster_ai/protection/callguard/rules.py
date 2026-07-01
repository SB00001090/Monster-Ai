"""HK scam and illegal debt-collection phone rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_THREAT_DB: dict[str, Any] = {
    "version": "callguard-hk-2026.06",
    "locale": "zh-HK",
    "prefixes_high_risk": ["+8529", "+8524", "+861", "+886", "+234", "+91"],
    "prefixes_debt_collection": ["+852", "852"],
    "keywords_display": [
        "收數", "財務公司", "追債", "還款", "逾期", "律師行", "法院",
        "警察", "入境", "海關", "稅務", "投資", "加密貨幣", "中獎",
    ],
    "known_scam_numbers": [],
    "hash_blocklist": [],
    "block_threshold": 70,
    "reject_threshold": 85,
}


@dataclass
class CallScoreResult:
    score: int = 0
    blocked: bool = False
    reject: bool = False
    category: str = ""
    signals: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        trust = max(0, min(100, 100 - self.score))
        return {
            "score": self.score,
            "trust_score": trust,
            "blocked": self.blocked,
            "reject": self.reject,
            "category": self.category,
            "signals": self.signals[:10],
            "summary": self.summary,
        }


def load_threat_db(path: Path) -> dict[str, Any]:
    if path.exists():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if data.get("version"):
            return data
    return DEFAULT_THREAT_DB.copy()


def normalize_number(number: str) -> str:
    n = re.sub(r"[^\d+]", "", number.strip())
    if n.startswith("852") and not n.startswith("+852"):
        n = "+" + n
    return n


def score_call(
    number: str,
    *,
    display_name: str = "",
    db: dict[str, Any] | None = None,
) -> CallScoreResult:
    rules = db or DEFAULT_THREAT_DB
    result = CallScoreResult()
    num = normalize_number(number)
    if not num:
        return result

    block_t = int(rules.get("block_threshold", 70))
    reject_t = int(rules.get("reject_threshold", 85))
    max_score = 0

    from monster_ai.protection.callguard.report import hash_number

    nh = hash_number(number)
    for blocked_hash in rules.get("hash_blocklist", []):
        if nh == blocked_hash:
            result.signals.append("consensus:hash_block")
            max_score = max(max_score, 92)
            result.category = "community_verified"

    for known in rules.get("known_scam_numbers", []):
        if num.endswith(str(known)) or num == str(known):
            result.signals.append(f"known:{known}")
            max_score = max(max_score, 95)
            result.category = "known_scam"

    for prefix in rules.get("prefixes_high_risk", []):
        if num.startswith(prefix.replace(" ", "")):
            result.signals.append(f"prefix:{prefix}")
            max_score = max(max_score, 75)
            if not result.category:
                result.category = "high_risk_prefix"

    for kw in rules.get("keywords_display", []):
        if kw in (display_name or ""):
            result.signals.append(f"display:{kw}")
            max_score = max(max_score, 88)
            result.category = "debt_collection_scam" if "收數" in kw or "追債" in kw else "scam_keyword"

    debt_kw = ["收數", "財務", "追債", "還款", "逾期"]
    if any(k in (display_name or "") for k in debt_kw):
        max_score = max(max_score, 90)
        result.category = "hk_debt_collection"

    if num.startswith("+234") or num.startswith("+91"):
        max_score = max(max_score, 92)
        result.category = "international_scam"

    result.score = min(100, max_score)
    result.blocked = result.score >= block_t
    result.reject = result.score >= reject_t
    if result.signals:
        result.summary = f"Call threat: {result.category or 'suspicious'}"
    return result