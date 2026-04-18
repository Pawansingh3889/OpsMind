"""Collision tests for ``modules.query_library``.

The library dispatches by order-sensitive regex matching, so a broad pattern
declared earlier in the list can steal traffic from a narrower, later one.
Exactly that bug (pattern 5 greedy-matching "production") was caught by the
eval harness — this file prevents recurrence and covers the other pairs
where an overlap is plausible.

Every test maps a canonical operator phrasing to the description string of
the expected library entry. Strings are intentionally opaque (not imported
as constants) so a silent description change shows up as a loud test diff.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.query_library import find_matching_query  # noqa: E402


def _match(question: str) -> tuple[str | None, str | None]:
    """Convenience wrapper returning (sql_present, description)."""
    sql, desc = find_matching_query(question)
    return (sql if sql is None else "sql-present", desc)


# ---------------------------------------------------------------------------
# One happy-path assertion per library pattern.
#
# If a pattern is reordered or a regex tightens too much, the corresponding
# test here fails with a clear mismatch between expected and actual
# description. That's cheaper to diagnose than a silent routing change.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("question", "expected_description"),
    [
        ("what did we produce today",                   "Today's production summary by product"),
        ("which products have the most waste this week","Top products by waste this week"),
        ("show me pending orders",                      "All pending orders by customer"),
        ("any temperature excursions this week",        "Temperature excursions in the last 7 days"),
        ("average yield by product",                    "Average yield by product (last 30 days)"),
        ("who has worked overtime this week",           "Staff overtime status"),
        ("what raw materials are expiring soon",        "Raw materials expiring within 3 days"),
        ("how much money did we lose to waste this week","Total waste cost breakdown"),
        ("which customer ordered the most this month",  "Customer orders breakdown (last 30 days)"),
        ("which suppliers delivered in the last 30 days","Supplier deliveries (last 30 days)"),
        ("yield by production line last week",          "Yield by production line (last 7 days)"),
        ("trace batch BC-0001",                         "Traceability chain: run to catch vessel"),
        ("shift productivity day vs night",             "Shift productivity comparison (last 14 days)"),
        ("any open critical non-conformances",          "Open non-conformances by severity"),
    ],
)
def test_canonical_question_hits_expected_pattern(
    question: str, expected_description: str
) -> None:
    sql, desc = find_matching_query(question)
    assert sql is not None, f"{question!r} unexpectedly missed the library"
    assert desc == expected_description, (
        f"{question!r} routed to {desc!r}, expected {expected_description!r}"
    )


# ---------------------------------------------------------------------------
# Explicit regression guards for known collisions.
# ---------------------------------------------------------------------------

class TestPatternCollisions:
    def test_product_line_yield_routes_to_line_pattern(self) -> None:
        """Regression: "yield by production line" was routing to pattern 5
        (yield by product) because the "product" alternative was not
        word-bound and matched "production". See
        tests/eval/failure_modes.md > library/wrong-pattern."""
        sql, desc = find_matching_query("yield by production line last week")
        assert desc == "Yield by production line (last 7 days)"

    def test_product_yield_still_routes_to_product_pattern(self) -> None:
        """The fix (word-bounded alternatives on pattern 5) must not
        accidentally stop product-oriented questions hitting pattern 5."""
        sql, desc = find_matching_query("average yield by product")
        assert desc == "Average yield by product (last 30 days)"

    def test_waste_product_stays_on_waste_pattern(self) -> None:
        """'most waste' could conceivably match pattern 5 via "product",
        but pattern 2 is declared first and is the intended route."""
        sql, desc = find_matching_query("which products have the most waste")
        assert desc == "Top products by waste this week"

    # Intentionally NOT asserted: patterns 4 and 13 both legitimately cover
    # temperature questions — pattern 4 against the legacy ``temp_logs``
    # table, pattern 13 against the production ERP ``prod_temperature_logs``.
    # Which one "should" win for a bare "temperature breach" question is an
    # owner-level design decision, not a test-level assertion. If the owner
    # settles this, add the assertion back and pick a canonical question.


# ---------------------------------------------------------------------------
# Misses — questions that should NOT match any library pattern so the LLM
# path is exercised. If one of these unexpectedly starts matching, someone
# has widened a regex and it's time to re-check golden_set.yaml's llm path.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "question",
    [
        "how many products have salmon in their name",
        "which operator ran the most production batches in the last 30 days",
        "which product has the highest profit margin per kg",
        "list orders that were delivered late in the last 30 days",
        "how many production batches had waste above 20 kilograms last week",
        "average temperature by location in the last 7 days",
    ],
)
def test_llm_path_questions_do_not_match_library(question: str) -> None:
    sql, desc = find_matching_query(question)
    assert sql is None, (
        f"{question!r} unexpectedly matched {desc!r} — this question is on "
        f"the LLM path in golden_set.yaml and a library match invalidates "
        f"the LLM accuracy measurement."
    )


# ---------------------------------------------------------------------------
# Return-shape contract
# ---------------------------------------------------------------------------

class TestReturnShape:
    def test_no_match_returns_none_tuple(self) -> None:
        sql, desc = find_matching_query("something nobody would ask a factory")
        assert sql is None
        assert desc is None

    def test_match_returns_sql_and_description_strings(self) -> None:
        sql, desc = find_matching_query("what did we produce today")
        assert isinstance(sql, str) and sql.strip().lower().startswith("select")
        assert isinstance(desc, str) and desc


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
