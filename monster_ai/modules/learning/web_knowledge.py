"""Network knowledge acquisition — search, fetch, and persist web facts."""
from __future__ import annotations

import json
import re
import time
from typing import Any
from urllib.parse import quote, urlparse

import httpx

from monster_ai.config import LearningSettings
from monster_ai.core.self_repair import SelfRepairEngine
from monster_ai.modules.learning.store import LearningStore

SUMMARIZE_SYSTEM = """You are a knowledge curator for Monster AI.
Given web search snippets about a topic, extract durable facts.
Output JSON only: {"facts":[{"fact":"...","source":"..."}],"summary":"one paragraph"}
Use Traditional Chinese for facts when the query is Chinese."""

AUTO_SEARCH_MARKERS = (
    r"\?",
    r"什麼",
    r"為何",
    r"為什麼",
    r"如何",
    r"怎麼",
    r"哪裡",
    r"哪裡",
    r"誰",
    r"幾時",
    r"最新",
    r"今年",
    r"202[4-9]",
    r"\bwhat\b",
    r"\bwhy\b",
    r"\bhow\b",
    r"\bwhen\b",
    r"\bwho\b",
    r"\bwhere\b",
    r"搜尋",
    r"查一下",
    r"上網",
    r"網路",
    r"learn",
    r"search",
)

USER_AGENT = (
    "MonsterAI/2.1 (local knowledge learner; https://monster-ai.local) "
    "httpx/0.28 (+https://w.wiki/4wJS)"
)

ALLOWED_FETCH_HOSTS = (
    "wikipedia.org",
    "wikimedia.org",
    "duckduckgo.com",
    "github.com",
    "stackoverflow.com",
    "developer.mozilla.org",
    "docs.python.org",
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip())[:200]


class WebKnowledgeLearner:
    def __init__(
        self,
        store: LearningStore,
        settings: LearningSettings,
        repair: SelfRepairEngine | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.repair = repair
        self._network_allowed: Any = None
        self._stats = {"searches": 0, "learned": 0, "cache_hits": 0, "errors": 0}

    def set_network_guard(self, guard: Any) -> None:
        """Optional callable returning (allowed: bool, reason: str)."""
        self._network_allowed = guard

    def _can_use_network(self, *, network_override: bool = False) -> tuple[bool, str]:
        if not network_override and not self.settings.web_learning_enabled:
            return False, "web_learning_disabled"
        if self._network_allowed is not None:
            try:
                ok, reason = self._network_allowed()
                if not ok:
                    return False, reason or "network_blocked"
            except Exception:
                return False, "network_guard_error"
        return True, ""

    def should_auto_search(self, message: str) -> bool:
        if not self.settings.web_auto_search:
            return False
        text = message.strip()
        if len(text) < 4:
            return False
        return any(re.search(p, text, re.I) for p in AUTO_SEARCH_MARKERS)

    def _load_facts(self) -> dict[str, Any]:
        default = {"facts": [], "topics": {}, "updated_at": 0.0}
        return self.store.read_json(self.store.web_facts, default)

    def _save_facts(self, data: dict[str, Any]) -> None:
        data["updated_at"] = time.time()
        self.store.write_json(self.store.web_facts, data)

    def _topic_key(self, query: str) -> str:
        return _normalize_query(query).lower()

    def _cache_fresh(self, topic_key: str) -> bool:
        data = self._load_facts()
        topic = data.get("topics", {}).get(topic_key)
        if not topic:
            return False
        age_h = (time.time() - float(topic.get("ts", 0))) / 3600
        return age_h < self.settings.web_cache_hours

    def retrieve_local(self, query: str, limit: int = 6) -> list[str]:
        data = self._load_facts()
        facts = data.get("facts", [])
        tokens = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", query.lower()))
        scored: list[tuple[float, str]] = []
        q_lower = query.lower()
        for item in facts:
            fact = str(item.get("fact", ""))
            if not fact:
                continue
            fact_lower = fact.lower()
            fact_tokens = set(re.findall(r"[\w\u4e00-\u9fff]{2,}", fact_lower))
            overlap = len(tokens & fact_tokens)
            if not overlap:
                overlap = sum(1 for t in tokens if t in fact_lower or t in q_lower and t in fact_lower)
            if overlap or (len(q_lower) >= 2 and q_lower in fact_lower):
                score = overlap + float(item.get("confidence", 0.5))
                if q_lower in fact_lower:
                    score += 2
                scored.append((score, fact))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:limit]]

    async def _http_get(self, url: str) -> str | None:
        timeout = self.settings.web_fetch_timeout_seconds
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": USER_AGENT})
                if r.status_code == 200:
                    return r.text
        except httpx.HTTPError:
            self._stats["errors"] += 1
        return None

    async def _search_wikipedia(self, query: str, lang: str) -> list[dict[str, str]]:
        q = quote(query)
        search_url = (
            f"https://{lang}.wikipedia.org/w/api.php"
            f"?action=opensearch&search={q}&limit={self.settings.web_max_results}&format=json"
        )
        raw = await self._http_get(search_url)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list) or len(data) < 4:
            return []
        titles, descriptions, urls = data[1], data[2], data[3]
        out: list[dict[str, str]] = []
        for title, desc, url in zip(titles, descriptions, urls, strict=False):
            if not title:
                continue
            summary = desc
            sum_url = (
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
            )
            sum_raw = await self._http_get(sum_url)
            if sum_raw:
                try:
                    sum_data = json.loads(sum_raw)
                    extract = str(sum_data.get("extract", "")).strip()
                    if extract:
                        summary = extract
                except json.JSONDecodeError:
                    pass
            out.append(
                {
                    "title": title,
                    "snippet": summary[:1200],
                    "url": url,
                    "source": f"wikipedia:{lang}",
                }
            )
        return out

    async def _search_duckduckgo(self, query: str) -> list[dict[str, str]]:
        q = quote(query)
        url = f"https://api.duckduckgo.com/?q={q}&format=json&no_html=1&skip_disambig=1"
        raw = await self._http_get(url)
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        out: list[dict[str, str]] = []
        abstract = str(data.get("AbstractText", "")).strip()
        if abstract:
            out.append(
                {
                    "title": str(data.get("Heading", query)),
                    "snippet": abstract[:1200],
                    "url": str(data.get("AbstractURL", "")),
                    "source": "duckduckgo",
                }
            )
        for topic in (data.get("RelatedTopics") or [])[: self.settings.web_max_results]:
            if not isinstance(topic, dict):
                continue
            text = str(topic.get("Text", "")).strip()
            if text:
                out.append(
                    {
                        "title": text.split(" - ")[0][:80],
                        "snippet": text[:1200],
                        "url": str(topic.get("FirstURL", "")),
                        "source": "duckduckgo_related",
                    }
                )
        return out

    async def search(self, query: str, *, network_override: bool = False) -> dict[str, Any]:
        allowed, reason = self._can_use_network(network_override=network_override)
        if not allowed:
            return {"ok": False, "reason": reason, "results": []}

        q = _normalize_query(query)
        if not q:
            return {"ok": False, "reason": "empty_query", "results": []}

        self._stats["searches"] += 1
        results: list[dict[str, str]] = []
        for lang in self.settings.web_search_langs:
            results.extend(await self._search_wikipedia(q, lang))
        results.extend(await self._search_duckduckgo(q))

        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in results:
            key = (item.get("title", "") + item.get("snippet", ""))[:120].lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= self.settings.web_max_results * 2:
                break

        return {"ok": True, "query": q, "results": deduped}

    async def fetch_url(self, url: str, *, network_override: bool = False) -> dict[str, Any]:
        allowed, reason = self._can_use_network(network_override=network_override)
        if not allowed:
            return {"ok": False, "reason": reason}
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not any(host.endswith(h) for h in ALLOWED_FETCH_HOSTS):
            return {"ok": False, "reason": "host_not_allowed"}
        raw = await self._http_get(url)
        if not raw:
            return {"ok": False, "reason": "fetch_failed"}
        text = _strip_html(raw)[:8000]
        return {"ok": True, "url": url, "text": text}

    async def learn(
        self,
        query: str,
        *,
        force_refresh: bool = False,
        network_override: bool = False,
    ) -> dict[str, Any]:
        topic_key = self._topic_key(query)
        if not force_refresh and self._cache_fresh(topic_key):
            self._stats["cache_hits"] += 1
            local = self.retrieve_local(query, limit=8)
            return {
                "ok": True,
                "query": query,
                "cached": True,
                "facts": local,
                "fact_count": len(local),
            }

        search = await self.search(query, network_override=network_override)
        if not search.get("ok"):
            return search

        snippets = search.get("results") or []
        facts: list[dict[str, Any]] = []
        summary = ""

        if self.repair and snippets:
            blob = "\n\n".join(
                f"[{s.get('source')}] {s.get('title')}: {s.get('snippet')}" for s in snippets
            )
            try:
                raw = await self.repair.generate(
                    f"Topic: {query}\n\nWeb snippets:\n{blob}",
                    system=SUMMARIZE_SYSTEM,
                )
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    parsed = json.loads(match.group())
                    summary = str(parsed.get("summary", "")).strip()
                    for item in parsed.get("facts", []):
                        fact = str(item.get("fact", "")).strip()
                        if len(fact) < 6:
                            continue
                        facts.append(
                            {
                                "fact": fact,
                                "source": str(item.get("source", "web")),
                                "confidence": 0.75,
                                "topic": topic_key,
                                "ts": time.time(),
                            }
                        )
            except Exception:
                pass

        if not facts:
            for s in snippets:
                snippet = str(s.get("snippet", "")).strip()
                if len(snippet) < 20:
                    continue
                facts.append(
                    {
                        "fact": snippet[:500],
                        "source": s.get("source", "web"),
                        "confidence": 0.6,
                        "topic": topic_key,
                        "ts": time.time(),
                    }
                )

        data = self._load_facts()
        existing = data.setdefault("facts", [])
        seen = {str(f.get("fact", "")).lower() for f in existing}
        for f in facts:
            key = str(f.get("fact", "")).lower()
            if key and key not in seen:
                existing.append(f)
                seen.add(key)
        data["facts"] = existing[-2000:]
        topics = data.setdefault("topics", {})
        topics[topic_key] = {
            "query": query,
            "ts": time.time(),
            "fact_count": len(facts),
            "summary": summary[:600],
        }
        self._save_facts(data)

        self.store.append_jsonl(
            self.store.web_learned_log,
            {
                "query": query,
                "facts_added": len(facts),
                "sources": [s.get("source") for s in snippets],
            },
        )
        self._stats["learned"] += 1

        return {
            "ok": True,
            "query": query,
            "cached": False,
            "facts_added": len(facts),
            "summary": summary,
            "fact_count": len(data["facts"]),
            "snippets": len(snippets),
        }

    async def context_for_message(self, message: str, *, force: bool = False) -> str:
        if not self.settings.web_learning_enabled:
            return ""
        local = self.retrieve_local(message)
        parts: list[str] = []
        if local:
            parts.append("[Web knowledge — local]\n" + "\n".join(f"- {f}" for f in local[:5]))

        if force or self.should_auto_search(message):
            learned = await self.learn(message)
            if learned.get("ok") and not learned.get("cached"):
                summary = str(learned.get("summary", "")).strip()
                if summary:
                    parts.append(f"[Web knowledge — fresh]\n{summary}")
                fresh = self.retrieve_local(message, limit=4)
                extra = [f for f in fresh if f not in local]
                if extra:
                    parts.append("\n".join(f"- {f}" for f in extra[:4]))

        return "\n\n".join(parts)

    def status(self) -> dict[str, Any]:
        data = self._load_facts()
        return {
            "enabled": self.settings.web_learning_enabled,
            "auto_search": self.settings.web_auto_search,
            "total_facts": len(data.get("facts", [])),
            "topics_learned": len(data.get("topics", {})),
            "stats": dict(self._stats),
            "langs": self.settings.web_search_langs,
        }