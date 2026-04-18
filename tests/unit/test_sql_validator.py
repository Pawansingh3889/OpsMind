"""Focused tests for ``modules.sql_validator.validate_sql``.

README advertises a "5-stage validation pipeline" — this file covers each
stage with targeted cases so a change to any one stage fails a single
readable test instead of a generic smoke test.

Stages (see ``modules/sql_validator.py``):

1. Statement type check — only ``SELECT``/``WITH`` allowed, dangerous
   keywords rejected even inside an otherwise-SELECT query.
2. Injection patterns — tautologies, ``UNION SELECT``, ``-- /* */``
   comments, stacked queries.
3. Tables exist — referenced tables must appear in ``known_tables``.
4. Columns exist — referenced ``table.column`` refs must resolve. Emits
   warnings, not errors.
5. Row-limit enforcement — valid SQL without ``LIMIT`` / ``TOP`` gets
   one injected before execution.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``modules`` importable when pytest is launched from the repo root.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from modules.sql_validator import validate_sql  # noqa: E402


# ---------------------------------------------------------------------------
# Stage 1 — statement type
# ---------------------------------------------------------------------------

class TestStatementType:
    def test_plain_select_passes(self) -> None:
        result = validate_sql("SELECT 1")
        assert result.is_valid, result.errors

    def test_with_cte_passes(self) -> None:
        result = validate_sql("WITH x AS (SELECT 1) SELECT * FROM x")
        assert result.is_valid, result.errors

    def test_insert_blocked(self) -> None:
        result = validate_sql("INSERT INTO products VALUES (1, 'hack')")
        assert not result.is_valid
        assert any("read-only" in e.lower() or "select/with" in e.lower() for e in result.errors)

    def test_update_blocked(self) -> None:
        result = validate_sql("UPDATE products SET name='x'")
        assert not result.is_valid

    def test_delete_blocked(self) -> None:
        result = validate_sql("DELETE FROM products")
        assert not result.is_valid

    def test_drop_blocked(self) -> None:
        result = validate_sql("DROP TABLE products")
        assert not result.is_valid

    def test_select_containing_dangerous_keyword_blocked(self) -> None:
        # SELECT that smuggles a dangerous keyword in a string/subquery — the
        # validator conservatively rejects the whole query.
        result = validate_sql("SELECT 1 WHERE 'INSERT' = 'INSERT'")
        assert not result.is_valid

    def test_empty_string_rejected(self) -> None:
        result = validate_sql("")
        assert not result.is_valid

    def test_whitespace_only_rejected(self) -> None:
        result = validate_sql("   \n\t  ")
        assert not result.is_valid


# ---------------------------------------------------------------------------
# Stage 2 — injection-pattern detection
# ---------------------------------------------------------------------------

class TestInjectionPatterns:
    def test_tautology_numeric_blocked(self) -> None:
        result = validate_sql("SELECT * FROM products WHERE 1=1")
        assert not result.is_valid
        assert any("tautology" in e.lower() for e in result.errors)

    def test_tautology_string_blocked(self) -> None:
        result = validate_sql("SELECT * FROM products WHERE 'a'='a'")
        assert not result.is_valid

    def test_union_injection_blocked(self) -> None:
        result = validate_sql("SELECT id FROM products UNION SELECT password FROM users")
        assert not result.is_valid
        assert any("union" in e.lower() for e in result.errors)

    def test_block_comment_blocked(self) -> None:
        result = validate_sql("SELECT id /* evil payload */ FROM products")
        assert not result.is_valid
        assert any("comment" in e.lower() for e in result.errors)

    def test_trailing_line_comment_blocked(self) -> None:
        # The line-comment regex (`--\s*$`) catches ``--`` only when it sits
        # at the very end of the string — this covers the "dangling comment
        # trying to neutralise trailing SQL" pattern.
        result = validate_sql("SELECT id FROM products --")
        assert not result.is_valid
        assert any("comment" in e.lower() for e in result.errors)

    @pytest.mark.xfail(
        reason=(
            "Known gap: _COMMENT_INJECTION_RE only matches '--' at end-of-string "
            "or block comments, so a mid-query line comment with benign content "
            "sneaks through this rule specifically. (In practice a mid-query "
            "'--' followed by anything dangerous is caught by the stage-1 "
            "keyword check — so this is a defence-in-depth gap, not an "
            "exploitable one yet.) Tracked as a tightening task for "
            "sql_validator."
        ),
        strict=True,
    )
    def test_embedded_line_comment_with_benign_content_blocked(self) -> None:
        # The payload here contains no dangerous keywords, so stage 1 doesn't
        # catch it; the comment rule is the only remaining defence, and it
        # currently lets this through.
        result = validate_sql("SELECT id FROM products -- benign trailing text")
        assert not result.is_valid

    def test_stacked_query_blocked(self) -> None:
        result = validate_sql("SELECT id FROM products; SELECT * FROM users")
        assert not result.is_valid
        assert any("stacked" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# Stage 3 — table existence
# ---------------------------------------------------------------------------

class TestTableExistence:
    def test_unknown_table_rejected(self) -> None:
        result = validate_sql(
            "SELECT * FROM widgets",
            known_tables=["products", "orders"],
        )
        assert not result.is_valid
        assert any("widgets" in e.lower() for e in result.errors)

    def test_known_table_accepted(self) -> None:
        result = validate_sql(
            "SELECT * FROM products",
            known_tables=["products", "orders"],
        )
        assert result.is_valid, result.errors

    def test_table_check_case_insensitive(self) -> None:
        result = validate_sql(
            "SELECT * FROM Products",
            known_tables=["products"],
        )
        assert result.is_valid, result.errors

    def test_no_known_tables_means_no_table_check(self) -> None:
        # Calling without ``known_tables`` must not reject the query just
        # because we don't have a schema to check against.
        result = validate_sql("SELECT * FROM anything_at_all")
        assert result.is_valid, result.errors


# ---------------------------------------------------------------------------
# Stage 4 — column resolution (warnings, not errors)
# ---------------------------------------------------------------------------

class TestColumnResolution:
    @staticmethod
    def _resolver(table: str) -> list[str]:
        return {"products": ["id", "name", "species"]}.get(table, [])

    def test_unknown_column_produces_warning_not_error(self) -> None:
        result = validate_sql(
            "SELECT products.made_up_column FROM products",
            known_tables=["products"],
            column_resolver=self._resolver,
        )
        assert result.is_valid, "column issues should be warnings"
        assert any("made_up_column" in w.lower() for w in result.warnings)

    def test_known_column_no_warning(self) -> None:
        result = validate_sql(
            "SELECT products.name FROM products",
            known_tables=["products"],
            column_resolver=self._resolver,
        )
        assert result.is_valid
        assert not result.warnings


# ---------------------------------------------------------------------------
# Stage 5 — row-limit enforcement
# ---------------------------------------------------------------------------

class TestRowLimitEnforcement:
    def test_limit_injected_when_missing(self) -> None:
        result = validate_sql("SELECT * FROM products", max_rows=250)
        assert result.is_valid
        assert "LIMIT 250" in result.sql

    def test_existing_limit_preserved(self) -> None:
        result = validate_sql("SELECT * FROM products LIMIT 5", max_rows=250)
        assert result.is_valid
        assert result.sql.count("LIMIT") == 1
        assert "LIMIT 5" in result.sql

    def test_trailing_semicolon_stripped_before_limit(self) -> None:
        result = validate_sql("SELECT * FROM products;", max_rows=100)
        assert result.is_valid
        # The LIMIT must land after the stripped semicolon, not before it.
        assert result.sql.rstrip().endswith("LIMIT 100")


# ---------------------------------------------------------------------------
# Result object contract
# ---------------------------------------------------------------------------

class TestValidationResultContract:
    def test_result_truthy_when_valid(self) -> None:
        result = validate_sql("SELECT 1")
        assert bool(result) is True

    def test_result_falsy_when_invalid(self) -> None:
        result = validate_sql("DROP TABLE products")
        assert bool(result) is False

    def test_error_message_returns_first_error(self) -> None:
        result = validate_sql("DROP TABLE products")
        assert result.error_message is not None
        assert result.error_message == result.errors[0]

    def test_error_message_none_when_valid(self) -> None:
        result = validate_sql("SELECT 1")
        assert result.error_message is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
