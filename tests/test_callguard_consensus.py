"""CallGuard anonymous consensus — no public board."""
from __future__ import annotations

from pathlib import Path

from monster_ai.protection.callguard.consensus import ReportConsensus
from monster_ai.protection.callguard.report import hash_number
from monster_ai.protection.callguard.rules import score_call


def test_consensus_requires_three_votes(tmp_path: Path) -> None:
    c = ReportConsensus(tmp_path, min_votes=3, adopt_threshold=70)
    for i in range(2):
        r = c.submit("+85291234567", category="scam", score=80, signals=["test"], reporter_id=f"r{i}")
        assert not r["adopted"]
    r3 = c.submit("+85291234567", category="scam", score=85, signals=["test"], reporter_id="r2")
    assert r3["adopted"]
    assert len(c.adopted_hashes()) == 1


def test_no_duplicate_reporter(tmp_path: Path) -> None:
    c = ReportConsensus(tmp_path, min_votes=2)
    c.submit("+85290000001", category="x", score=90, signals=[], reporter_id="same")
    r2 = c.submit("+85290000001", category="x", score=90, signals=[], reporter_id="same")
    assert r2["duplicate"]


def test_hash_blocklist_scoring(tmp_path: Path) -> None:
    c = ReportConsensus(tmp_path, min_votes=1, adopt_threshold=70)
    num = "+85291112222"
    c.submit(num, category="scam", score=90, signals=["test"], reporter_id="a")
    db = {"hash_blocklist": c.adopted_hashes(), "block_threshold": 70, "reject_threshold": 85}
    result = score_call(num, db=db)
    assert result.score >= 70
    assert "consensus:hash_block" in result.signals


def test_status_no_public_board(tmp_path: Path) -> None:
    c = ReportConsensus(tmp_path)
    st = c.status()
    assert st["public_comment_board"] is False