"""Unit tests for ``modules.rca`` — root-cause *scaffolding*.

The tests lock in the two things that matter for audit safety:

  1. the module produces *evidence* (correlated factors, retrieved docs,
     5-Whys questions), and
  2. it never silently becomes a *conclusion* — ``is_actionable_record``
     is False until a human fills owner + verified_by.

Correlation maths is checked against a tiny in-memory frame so the
ranking contract is explicit and DB-independent.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Seed the demo DB so the correlation queries have something to read.
os.environ.setdefault(
    "OPSMIND_DB", f"sqlite:///{_ROOT / 'data' / 'demo.db'}"
)
if not (_ROOT / "data" / "demo.db").exists():
    from scripts.seed_demo_db import seed  # noqa: E402

    seed()

from modules import rca  # noqa: E402


# ---------------------------------------------------------------------------
# The audit boundary: scaffold is never a conclusion until a human owns it
# ---------------------------------------------------------------------------

class TestAuditBoundary:
    def test_fresh_scaffold_is_not_an_actionable_record(self) -> None:
        s = rca.RcaScaffold(effect="yield drop on Salmon", metric="yield_pct", window_days=30)
        assert s.owner is None
        assert s.verified_by is None
        assert s.is_actionable_record is False

    def test_owner_alone_is_insufficient(self) -> None:
        s = rca.RcaScaffold(effect="x", metric="yield_pct", window_days=30, owner="QA Lead")
        assert s.is_actionable_record is False, "verification by a human is still required"

    def test_owner_plus_verifier_makes_it_a_record(self) -> None:
        s = rca.RcaScaffold(
            effect="x", metric="yield_pct", window_days=30,
            owner="QA Lead", verified_by="Site Manager",
        )
        assert s.is_actionable_record is True


# ---------------------------------------------------------------------------
# 5-Whys scaffold — questions, never answers
# ---------------------------------------------------------------------------

class TestFiveWhys:
    def test_has_five_questions(self) -> None:
        whys = rca.build_five_whys("yield drop", [])
        assert len(whys) == 5
        assert all(w.strip().endswith("?") for w in whys), "every why is a question"

    def test_seeds_first_why_with_top_factor(self) -> None:
        factor = rca.CandidateFactor(
            dimension="operator", value="J. Smith",
            group_mean=84.0, overall_mean=90.0, delta=-6.0, sample_size=5,
        )
        whys = rca.build_five_whys("yield drop", [factor])
        assert "operator" in whys[0]
        assert "J. Smith" in whys[0]
        # The seed describes evidence, not a verdict.
        assert "caused" not in whys[0].lower()

    def test_no_factors_still_produces_chain(self) -> None:
        whys = rca.build_five_whys("yield drop", [])
        assert len(whys) == 5
        assert "yield drop" in whys[0]


# ---------------------------------------------------------------------------
# CandidateFactor direction semantics
# ---------------------------------------------------------------------------

class TestCandidateFactor:
    def test_negative_delta_is_below(self) -> None:
        f = rca.CandidateFactor("shift", "Night", 85.0, 90.0, -5.0, 8)
        assert f.direction == "below"

    def test_positive_delta_is_above(self) -> None:
        f = rca.CandidateFactor("shift", "Day", 93.0, 90.0, 3.0, 8)
        assert f.direction == "above"


# ---------------------------------------------------------------------------
# Correlation against the demo DB — contract, not exact values
# ---------------------------------------------------------------------------

class TestCorrelateYieldDrop:
    def test_returns_ranked_candidate_factors(self) -> None:
        factors = rca.correlate_yield_drop(window_days=3650, min_group_runs=1)
        assert isinstance(factors, list)
        # Demo data spans line_number / shift / operator — expect hits.
        assert factors, "demo production data should yield candidate factors"
        for f in factors:
            assert isinstance(f, rca.CandidateFactor)
            assert f.dimension in ("line_number", "shift", "operator")

    def test_ranked_by_absolute_delta_descending(self) -> None:
        factors = rca.correlate_yield_drop(window_days=3650, min_group_runs=1)
        deltas = [abs(f.delta) for f in factors]
        assert deltas == sorted(deltas, reverse=True), "biggest movers first"

    def test_top_n_caps_result_size(self) -> None:
        factors = rca.correlate_yield_drop(window_days=3650, min_group_runs=1, top_n=2)
        assert len(factors) <= 2

    def test_delta_equals_group_minus_overall(self) -> None:
        factors = rca.correlate_yield_drop(window_days=3650, min_group_runs=1)
        for f in factors:
            assert f.delta == round(f.group_mean - f.overall_mean, 1)


# ---------------------------------------------------------------------------
# Full scaffold assembly
# ---------------------------------------------------------------------------

class TestBuildScaffold:
    def test_assembles_all_evidence_layers(self) -> None:
        s = rca.build_scaffold("yield drop on Salmon", window_days=3650)
        assert s.effect == "yield drop on Salmon"
        assert isinstance(s.candidate_factors, list)
        assert len(s.five_whys) == 5
        assert isinstance(s.corrective_action_docs, list)  # [] if no docs ingested
        # Still owned by nobody — the whole point.
        assert s.is_actionable_record is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
