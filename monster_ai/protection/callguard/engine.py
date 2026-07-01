"""CallGuard engine — local rules + optional LLM deep analysis."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from monster_ai.config import CallGuardSettings
from monster_ai.protection.callguard.consensus import ReportConsensus
from monster_ai.protection.callguard.report import build_anonymous_report
from monster_ai.protection.callguard.rules import CallScoreResult, load_threat_db, score_call

logger = logging.getLogger(__name__)


@dataclass
class CallGuardState:
    enabled: bool = False
    rejects_today: int = 0
    analyzes_today: int = 0
    reports_today: int = 0
    threat_db_version: str = ""


class CallGuardEngine:
    def __init__(
        self,
        settings: CallGuardSettings,
        root: Path,
        repair_engine: Any | None = None,
        monsterlock: Any | None = None,
    ) -> None:
        self.settings = settings
        self.root = root
        self.repair = repair_engine
        self.monsterlock = monsterlock
        self.state = CallGuardState()
        self._data_dir = root / settings.data_dir.lstrip("./")
        self._db_path = self._data_dir / "threat_db.yaml"
        self._events: list[dict[str, Any]] = []
        self._db = load_threat_db(self._db_path)
        self._consensus = ReportConsensus(
            self._data_dir,
            min_votes=settings.consensus_min_votes,
            adopt_threshold=settings.consensus_adopt_threshold,
        )
        self._consensus.apply_to_db(self._db)

    def _record(self, level: str, message: str, **extra: Any) -> None:
        self._events.append({"ts": time.time(), "level": level, "message": message, **extra})
        self._events = self._events[-300:]

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if not self._db_path.exists():
            self._db_path.write_text(yaml.dump(self._db, allow_unicode=True), encoding="utf-8")
        self.state.enabled = True
        self.state.threat_db_version = str(self._db.get("version", "unknown"))

    async def stop(self) -> None:
        pass

    def reload_db(self) -> None:
        self._db = load_threat_db(self._db_path)
        self.state.threat_db_version = str(self._db.get("version", "unknown"))

    async def analyze_call(
        self,
        number: str,
        *,
        display_name: str = "",
        deep: bool = False,
    ) -> CallScoreResult:
        result = score_call(number, display_name=display_name, db=self._db)
        self.state.analyzes_today += 1

        use_llm = (
            deep
            and self.settings.llm_analysis_enabled
            and self.repair
            and getattr(self.repair, "llm_analysis_enabled", True)
            and result.score >= self.settings.deep_analyze_threshold
            and result.score < self.settings.auto_reject_threshold
        )
        if use_llm:
            try:
                raw = await self.repair.generate(
                    f"HK phone threat check. Number pattern: {number[:6]}*** Display: {display_name}\n"
                    "Is this likely debt-collection scam or telecom fraud? "
                    'Reply JSON only: {"score":0-100,"category":"...","scam":true/false}',
                    system="Hong Kong anti-scam call classifier. JSON only.",
                )
                import json

                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(raw[start:end])
                    llm_score = int(data.get("score", 0))
                    if data.get("scam") and llm_score > result.score:
                        result.score = llm_score
                        result.category = str(data.get("category", "llm_scam"))
                        result.signals.append("llm:confirmed")
                        result.blocked = result.score >= int(self._db.get("block_threshold", 70))
                        result.reject = result.score >= self.settings.auto_reject_threshold
                        result.summary = f"LLM: {result.category}"
            except Exception:  # noqa: BLE001
                pass

        if result.reject:
            self.state.rejects_today += 1
            self._record("block", f"Auto-reject call {number[:6]}***", result=result.to_dict())

        return result

    def get_threat_db(self) -> dict[str, Any]:
        return self._db

    def issue_client_token(self) -> tuple[str, float]:
        """Short-lived token for mobile app (uses MonsterLock credential if available)."""
        cred = getattr(self.monsterlock, "_credential", None) if self.monsterlock else None
        if cred and hasattr(cred, "current"):
            tok = cred.current()
            if tok:
                return tok.value, tok.expires_at
        import secrets

        return secrets.token_urlsafe(24), time.time() + 300

    def submit_report(
        self,
        number: str,
        result: CallScoreResult,
        *,
        device_contact: dict[str, Any] | None = None,
        reporter_id: str = "",
    ) -> dict[str, Any]:
        report = build_anonymous_report(
            number,
            category=result.category,
            signals=result.signals,
            score=result.score,
        )
        if device_contact:
            report["device_contact"] = device_contact
        consensus = self._consensus.submit(
            number,
            category=result.category,
            score=result.score,
            signals=result.signals,
            reporter_id=reporter_id,
        )
        report["consensus"] = consensus
        if consensus.get("adopted"):
            self._db = self._consensus.apply_to_db(self._db)
            self._db_path.write_text(yaml.dump(self._db, allow_unicode=True), encoding="utf-8")
        self.state.reports_today += 1
        self._record("ok", "Anonymous report generated", report_id=report["number_hash"][:12])
        reports_dir = self._data_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        path = reports_dir / f"{int(time.time())}_{report['number_hash'][:8]}.yaml"
        path.write_text(yaml.dump(report, allow_unicode=True), encoding="utf-8")
        return report

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._events[-limit:]))

    def recent_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        reports_dir = self._data_dir / "reports"
        if not reports_dir.is_dir():
            return []
        files = sorted(reports_dir.glob("*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict[str, Any]] = []
        for path in files[:limit]:
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                out.append({
                    "category": data.get("category", "unknown"),
                    "number_hash": data.get("number_hash", ""),
                    "score": data.get("score", 0),
                    "ts": data.get("ts", 0),
                    "signals": (data.get("signals") or [])[:4],
                })
            except Exception:  # noqa: BLE001
                continue
        return out

    @staticmethod
    def _resolve_apk(root: Path) -> tuple[str, str, str, str]:
        """Return apk_filename, sha256, version, changelog."""
        import hashlib
        import re

        dist = root / "dist"
        apks = sorted(dist.glob("MonsterCallGuard-v*-signed.apk"), reverse=True)
        if not apks:
            return "", "", "1.0.0", ""
        apk = apks[0]
        match = re.search(r"v([\d.]+)-signed", apk.name)
        version = match.group(1) if match else "1.0.0"
        sha_file = dist / f"{apk.name}.sha256"
        if sha_file.exists():
            sha = sha_file.read_text(encoding="utf-8").split()[0].strip()
        else:
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
        changelog = (
            f"v{version}: Whocall 式來電辨識 · Cloudflare Tunnel 連線 · "
            "信任分數 · 匿名 hash 回報（無公開留言板）· ADCC 18222"
        )
        return apk.name, sha, version, changelog

    def to_dict(self) -> dict[str, Any]:
        red_dot = self.state.rejects_today > 0
        return {
            "enabled": self.state.enabled,
            "status": "alert" if red_dot else "ok",
            "red_dot": red_dot,
            "green_dot": self.state.enabled and not red_dot,
            "rejects_today": self.state.rejects_today,
            "analyzes_today": self.state.analyzes_today,
            "reports_today": self.state.reports_today,
            "threat_db_version": self.state.threat_db_version,
            "auto_reject_threshold": self.settings.auto_reject_threshold,
            "hk_hotline": self.settings.hk_hotline,
            "events": self.recent_events(10),
            "consensus": self._consensus.status(),
            "public_comment_board": self.settings.public_comment_board,
            "connection_mode": "cloudflare_tunnel",
        }

    def app_manifest(self, *, apk_url: str = "", apk_sha256: str = "") -> dict[str, Any]:
        filename, sha, version, changelog = self._resolve_apk(self.root)
        releases = self.settings.github_releases_page.rstrip("/")
        repo_base = releases.split("/releases")[0] if "/releases" in releases else releases
        default_gh = (
            f"{repo_base}/releases/download/v{version}/{filename}"
            if filename and repo_base.startswith("http")
            else ""
        )
        resolved_url = apk_url or default_gh or (f"/downloads/{filename}" if filename else "")
        resolved_sha = apk_sha256 or sha
        version_code = int(version.replace(".", "")) if version else 1
        return {
            "app_version": version,
            "app_version_code": version_code,
            "apk_url": resolved_url,
            "apk_filename": filename,
            "apk_sha256": resolved_sha,
            "releases_page": releases or "https://github.com/Suckbob/monster-ai/releases/latest",
            "changelog": changelog,
            "threat_db_version": self.state.threat_db_version,
            "package": "ai.monster.callguard",
            "distribution": "github_releases",
            "connection_mode": "cloudflare_tunnel",
            "qr_code_enabled": False,
            "hk_hotline": self.settings.hk_hotline,
            "developer": "Suckbob | Monster AI Call Guard",
        }