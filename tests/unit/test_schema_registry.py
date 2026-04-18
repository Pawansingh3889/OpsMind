"""Focused tests for ``modules.schema_registry``.

The cross-module suite in ``tests/test_core.py`` covers one canonical question
per domain but doesn't exercise:

* the compliance and stock domains (7 domains total, 5 were tested)
* mixed-signal questions where two domains share keywords
* ``get_tables_for_domain`` with an unknown domain (falls back to production)
* the empty / gibberish inputs where the default domain kicks in
* the contract of ``get_prompt_for_question`` — what it emits, and that the
  domain keyword landed in the prompt

This file fills those gaps one concern per class.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules import schema_registry  # noqa: E402

# ``get_prompt_for_question`` lazily imports ``modules.domain_docs`` which
# pulls streamlit in for a cache decorator. Skip only those tests if
# streamlit isn't installed — the rest of this module works fine without it.
_HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


# ---------------------------------------------------------------------------
# Domain detection — one happy-path assertion per domain
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("question", "expected_domain"),
    [
        ("trace batch BC-0001 back to the vessel",                "traceability"),
        ("what was our yield this week",                          "production"),
        ("any pending orders for Customer A",                     "orders"),
        ("cold room temperature last night",                      "temperature"),
        ("who worked overtime this week",                         "staff"),
        ("what raw materials are running low",                    "stock"),
        ("allergen changeover check on line 2",                   "compliance"),
    ],
)
def test_detect_domain_happy_paths(question: str, expected_domain: str) -> None:
    assert schema_registry.detect_domain(question) == expected_domain


# ---------------------------------------------------------------------------
# Domain detection — edges
# ---------------------------------------------------------------------------

class TestDetectDomainEdges:
    def test_empty_string_falls_back_to_default(self) -> None:
        # The contract is "default when no keyword hits" — production today.
        assert schema_registry.detect_domain("") == "production"

    def test_pure_gibberish_falls_back_to_default(self) -> None:
        assert schema_registry.detect_domain("xyzzy plugh frobnitz") == "production"

    def test_case_insensitive_match(self) -> None:
        assert schema_registry.detect_domain("TRACE BATCH BC-0001") == "traceability"
        assert schema_registry.detect_domain("Trace Batch BC-0001") == "traceability"

    def test_more_keywords_wins(self) -> None:
        """A question mixing traceability + temperature keywords where
        temperature wins by keyword count, not declaration order."""
        # "temperature" + "cold room" + "breach" + "degrees" = 4 hits for
        # temperature; "batch" = 1 hit for traceability.
        q = "cold room temperature breach degrees above target on batch BC-0001"
        assert schema_registry.detect_domain(q) == "temperature"

    def test_single_domain_keyword_wins_against_zero(self) -> None:
        assert schema_registry.detect_domain("just an order please") == "orders"


# ---------------------------------------------------------------------------
# get_tables_for_domain
# ---------------------------------------------------------------------------

class TestGetTablesForDomain:
    def test_valid_domain_returns_non_empty_dict(self) -> None:
        tables = schema_registry.get_tables_for_domain("production")
        assert isinstance(tables, dict)
        assert tables, "production domain must expose at least one table"

    def test_every_documented_domain_has_tables(self) -> None:
        for domain in (
            "production", "orders", "compliance", "traceability",
            "temperature", "staff", "stock",
        ):
            tables = schema_registry.get_tables_for_domain(domain)
            assert tables, f"domain {domain!r} returned no tables"

    def test_unknown_domain_falls_back_to_production(self) -> None:
        tables = schema_registry.get_tables_for_domain("not_a_real_domain")
        production = schema_registry.get_tables_for_domain("production")
        assert tables == production


# ---------------------------------------------------------------------------
# get_all_table_names
# ---------------------------------------------------------------------------

class TestGetAllTableNames:
    def test_returns_unique_names_only(self) -> None:
        names = schema_registry.get_all_table_names()
        assert len(names) == len(set(names))

    def test_includes_key_demo_tables(self) -> None:
        names = set(schema_registry.get_all_table_names())
        # Demo schema tables that should always be present.
        assert {"products", "production", "orders"}.issubset(names)


# ---------------------------------------------------------------------------
# get_prompt_for_question
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _HAS_STREAMLIT,
    reason="get_prompt_for_question transitively imports streamlit via domain_docs",
)
class TestGetPromptForQuestion:
    def test_returns_string_with_sql_directive(self) -> None:
        prompt = schema_registry.get_prompt_for_question("show waste by product")
        assert isinstance(prompt, str)
        assert "SQL" in prompt

    def test_includes_tables_for_detected_domain(self) -> None:
        prompt = schema_registry.get_prompt_for_question("show waste by product")
        # Production is the detected domain — its canonical tables should
        # appear verbatim in the prompt.
        assert "production" in prompt
        assert "products" in prompt

    def test_temperature_question_emits_temp_logs_table(self) -> None:
        prompt = schema_registry.get_prompt_for_question("cold room temperature last night")
        assert "temp_logs" in prompt or "prod_temperature_logs" in prompt


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
