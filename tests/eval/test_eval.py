"""Pytest runner for the golden evaluation set.

Usage
-----

Fast path only (no Ollama needed, runs in <5 s):

    pytest tests/eval/ -v -m eval_library

Full run (requires Ollama + gemma3:12b on localhost:11434):

    pytest tests/eval/ -v

Library-only is the target you want in CI. LLM-path is opt-in and noisy —
tail it locally, collect failure modes into ``failure_modes.md``, then tune.

Pattern reference
-----------------
- Cheuk Ting Ho, PyCon DE 2026 — task + metric + custom metric structure.
- Martin Seeler, PyCon DE 2026 — cluster failures before tuning prompts.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.eval.judge import (
    judge_library,
    judge_llm,
    load_samples,
)

# When ``OPSMIND_EVAL_SKIP_LLM=1`` is set, the LLM path is skipped entirely —
# useful for CI where Ollama isn't available.
SKIP_LLM = os.environ.get("OPSMIND_EVAL_SKIP_LLM") == "1"


# Load once at collection so parametrized IDs are visible in pytest output.
_SAMPLES = load_samples()
_LIBRARY_SAMPLES = [s for s in _SAMPLES if s.get("path", "library") == "library"]
_LLM_SAMPLES = [s for s in _SAMPLES if s.get("path") == "llm"]


def _ensure_demo_db() -> None:
    """Seed the demo DB if it doesn't exist. Matches tests/test_core.py."""
    root = Path(__file__).resolve().parents[2]
    demo_db = root / "data" / "demo.db"
    if demo_db.exists():
        return
    # Late import so collection doesn't require the seed module to be valid
    # when the DB already exists.
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from scripts.seed_demo_db import seed
    seed()


@pytest.fixture(scope="module", autouse=True)
def _demo_db() -> None:
    _ensure_demo_db()


# --- Library path ----------------------------------------------------------

@pytest.mark.eval_library
@pytest.mark.parametrize("sample", _LIBRARY_SAMPLES, ids=[s["id"] for s in _LIBRARY_SAMPLES])
def test_library_path(sample: dict) -> None:
    """Library questions must match the expected pattern and execute cleanly."""
    verdict = judge_library(sample)
    assert verdict.passed, (
        f"\n[{verdict.sample_id}] {verdict.question}\n"
        f"  reason: {verdict.reason}\n"
        f"  failure_mode: {verdict.failure_mode}"
    )


# --- LLM path --------------------------------------------------------------

@pytest.mark.eval_llm
@pytest.mark.skipif(SKIP_LLM, reason="OPSMIND_EVAL_SKIP_LLM=1 (CI / no Ollama)")
@pytest.mark.parametrize("sample", _LLM_SAMPLES, ids=[s["id"] for s in _LLM_SAMPLES])
def test_llm_path(sample: dict) -> None:
    """LLM questions: generated SQL must return a result set equivalent to expected_sql."""
    verdict = judge_llm(sample)
    assert verdict.passed, (
        f"\n[{verdict.sample_id}] {verdict.question}\n"
        f"  reason: {verdict.reason}\n"
        f"  failure_mode: {verdict.failure_mode}"
    )
