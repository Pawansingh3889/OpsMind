"""SQL validation layer -- validates generated SQL before execution.

Inspired by PyCon DE 2026 talk: "Before You Ship Your Agent" (Cerniauskas)
Applies least-privilege and input sanitization to NL-to-SQL output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

from config import DB_TYPE, SQL_MAX_ROWS


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Structured result from SQL validation."""

    is_valid: bool
    sql: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.is_valid

    @property
    def error_message(self) -> Optional[str]:
        """Return the first error, or ``None`` if validation passed."""
        return self.errors[0] if self.errors else None


# ---------------------------------------------------------------------------
# Injection-pattern detection
# ---------------------------------------------------------------------------

# Tautology patterns: WHERE 1=1, OR 'a'='a', OR ""="", etc.
_TAUTOLOGY_RE = re.compile(
    r"""(?ix)
    \b(\d+)\s*=\s*\1\b                # 1=1, 2=2, ...
    | '\w+'\s*=\s*'\w+'               # 'a'='a'
    | "\w+"\s*=\s*"\w+"               # "a"="a"
    | \bOR\s+1\s*=\s*1\b             # OR 1=1
    | \bOR\s+'[^']+'\s*=\s*'[^']+'\b # OR 'x'='x'
    """,
)

_COMMENT_INJECTION_RE = re.compile(r"--\s*$|/\*.*?\*/", re.DOTALL)

_UNION_INJECTION_RE = re.compile(
    r"\bUNION\b\s+(?:ALL\s+)?SELECT\b",
    re.IGNORECASE,
)

_STACKED_QUERY_RE = re.compile(r";\s*\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\b", re.IGNORECASE)


def _check_injection_patterns(sql: str) -> List[str]:
    """Return list of injection-related error strings (empty = clean)."""
    errors: List[str] = []

    if _TAUTOLOGY_RE.search(sql):
        errors.append("Blocked: query contains a tautology pattern (possible SQL injection).")
    if _UNION_INJECTION_RE.search(sql):
        errors.append("Blocked: UNION-based injection pattern detected.")
    if _COMMENT_INJECTION_RE.search(sql):
        errors.append("Blocked: SQL comment injection detected (-- or /* */).")
    if _STACKED_QUERY_RE.search(sql):
        errors.append("Blocked: stacked query detected (multiple statements).")

    return errors


# ---------------------------------------------------------------------------
# Statement-type check
# ---------------------------------------------------------------------------

DANGEROUS_KEYWORDS = frozenset({
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "EXEC", "EXECUTE", "XP_", "SP_",
    "GRANT", "REVOKE", "CREATE",
})


def _check_statement_type(sql: str) -> List[str]:
    """Ensure only SELECT / WITH statements are allowed."""
    errors: List[str] = []
    first_word = sql.strip().split()[0].upper() if sql.strip() else ""

    if first_word not in ("SELECT", "WITH"):
        errors.append(
            "For safety, OpsMind only runs read-only queries (SELECT/WITH). "
            "Please rephrase your question."
        )
        return errors

    sql_upper = sql.upper()
    for kw in DANGEROUS_KEYWORDS:
        if kw in sql_upper:
            errors.append(f'Blocked: query contains "{kw}". OpsMind is read-only.')
    return errors


# ---------------------------------------------------------------------------
# Schema-aware validation
# ---------------------------------------------------------------------------

def _extract_table_names(sql: str) -> List[str]:
    """Best-effort extraction of table names from SQL using sqlparse."""
    tables: List[str] = []
    parsed = sqlparse.parse(sql)
    if not parsed:
        return tables

    stmt = parsed[0]
    from_seen = False
    join_seen = False

    for token in stmt.tokens:
        if token.ttype is Keyword and token.normalized.upper() in ("FROM", "INTO"):
            from_seen = True
            join_seen = False
            continue
        if token.ttype is Keyword and "JOIN" in token.normalized.upper():
            join_seen = True
            from_seen = False
            continue
        if from_seen or join_seen:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    name = identifier.get_real_name()
                    if name:
                        tables.append(name)
                from_seen = False
                join_seen = False
            elif isinstance(token, Identifier):
                name = token.get_real_name()
                if name:
                    tables.append(name)
                from_seen = False
                join_seen = False
            elif token.ttype is not sqlparse.tokens.Whitespace:
                from_seen = False
                join_seen = False

    return tables


def _check_tables_exist(sql: str, known_tables: List[str]) -> List[str]:
    """Validate that referenced tables exist in the schema."""
    errors: List[str] = []
    if not known_tables:
        return errors

    known_lower = {t.lower() for t in known_tables}
    referenced = _extract_table_names(sql)

    for table in referenced:
        if table.lower() not in known_lower:
            errors.append(
                f'Unknown table "{table}". '
                f"Available tables: {', '.join(sorted(known_tables)[:15])}."
            )
    return errors


def _check_columns_exist(
    sql: str,
    known_tables: List[str],
    column_resolver,
) -> List[str]:
    """Validate that column references exist for their table.

    ``column_resolver`` is a callable(table_name) -> list[str] that
    returns column names for a given table (e.g. ``database.discover_columns``).
    """
    warnings: List[str] = []
    referenced = _extract_table_names(sql)

    if not known_tables:
        return warnings

    known_lower = {t.lower(): t for t in known_tables}

    for table in referenced:
        real_name = known_lower.get(table.lower())
        if not real_name:
            continue
        try:
            cols = column_resolver(real_name)
        except Exception:
            continue
        if not cols:
            continue

        cols_lower = {c.lower() for c in cols}
        # Quick heuristic: look for table.column references in SQL
        pattern = re.compile(rf"\b{re.escape(table)}\.(\w+)\b", re.IGNORECASE)
        for match in pattern.finditer(sql):
            col = match.group(1)
            if col.lower() not in cols_lower:
                warnings.append(
                    f'Column "{col}" not found in table "{real_name}". '
                    f"Available columns: {', '.join(cols[:10])}."
                )
    return warnings


# ---------------------------------------------------------------------------
# Row-limit enforcement
# ---------------------------------------------------------------------------

def _enforce_row_limit(sql: str, max_rows: int) -> str:
    """Append ``LIMIT <max_rows>`` if the query has no LIMIT / TOP clause."""
    sql_upper = sql.upper()

    # Already has a LIMIT or TOP clause -- leave it alone
    if re.search(r"\bLIMIT\s+\d+", sql_upper):
        return sql
    if re.search(r"\bTOP\s+\d+", sql_upper):
        return sql

    sql_stripped = sql.rstrip().rstrip(";")

    if DB_TYPE == "mssql":
        # For MSSQL, inject TOP into the SELECT keyword
        top_re = re.compile(r"\bSELECT\b", re.IGNORECASE)
        if top_re.search(sql_stripped):
            sql_stripped = top_re.sub(f"SELECT TOP {max_rows}", sql_stripped, count=1)
        return sql_stripped
    else:
        return f"{sql_stripped}\nLIMIT {max_rows}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_sql(
    sql: str,
    *,
    known_tables: Optional[List[str]] = None,
    column_resolver=None,
    max_rows: int = SQL_MAX_ROWS,
) -> ValidationResult:
    """Validate a generated SQL query before execution.

    Args:
        sql: The SQL string to validate.
        known_tables: List of table names that exist in the database.
            Pass ``database.discover_tables()`` in production.
        column_resolver: Callable(table_name) -> list[str] for column
            lookup. Pass ``database.discover_columns`` in production.
        max_rows: Maximum row limit to enforce. Defaults to
            ``config.SQL_MAX_ROWS``.

    Returns:
        A ``ValidationResult`` with ``is_valid``, ``sql`` (possibly
        amended with LIMIT), ``errors``, and ``warnings``.
    """
    if not sql or not sql.strip():
        return ValidationResult(
            is_valid=False,
            sql=sql,
            errors=["Empty SQL query."],
        )

    all_errors: List[str] = []
    all_warnings: List[str] = []

    # 1. Statement type (SELECT/WITH only)
    all_errors.extend(_check_statement_type(sql))
    if all_errors:
        return ValidationResult(is_valid=False, sql=sql, errors=all_errors)

    # 2. Injection patterns
    all_errors.extend(_check_injection_patterns(sql))
    if all_errors:
        return ValidationResult(is_valid=False, sql=sql, errors=all_errors)

    # 3. Schema validation -- tables
    if known_tables:
        all_errors.extend(_check_tables_exist(sql, known_tables))

    # 4. Schema validation -- columns (best-effort, warnings only)
    if known_tables and column_resolver:
        all_warnings.extend(
            _check_columns_exist(sql, known_tables, column_resolver)
        )

    if all_errors:
        return ValidationResult(
            is_valid=False,
            sql=sql,
            errors=all_errors,
            warnings=all_warnings,
        )

    # 5. Enforce row limit
    amended_sql = _enforce_row_limit(sql, max_rows)

    return ValidationResult(
        is_valid=True,
        sql=amended_sql,
        errors=[],
        warnings=all_warnings,
    )
