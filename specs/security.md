# Security Model

## Overview

OpsMind generates SQL from user input via an LLM. Every query passes through a 5-stage validation pipeline before execution. The system enforces read-only access by design.

## Validation Pipeline

Implemented in `modules/sql_validator.py`. Returns a `ValidationResult` with pass/fail, amended SQL, and warnings.

### Stage 1: Statement Type Check
- Only `SELECT` and `WITH` (CTEs) are allowed
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE` are blocked
- Check is case-insensitive on the first keyword

### Stage 2: Injection Pattern Detection
| Pattern | What it catches | Example |
|---------|----------------|---------|
| Tautologies | Always-true conditions | `WHERE 1=1`, `OR 'a'='a'` |
| UNION injection | Appended queries | `UNION SELECT password FROM users` |
| Comment injection | Query truncation | `--`, `/*` mid-query |
| Stacked queries | Multiple statements | `; DROP TABLE` |

### Stage 3: Table Existence
- Extracts table names from the SQL using sqlparse
- Validates each against `database.discover_tables()`
- Fails if any referenced table does not exist in the connected database

### Stage 4: Column Existence
- Extracts column references from the SQL
- Validates against `database.discover_columns(table_name)`
- Warns (does not fail) for unresolvable columns since SQL aliases can cause false positives

### Stage 5: Row Limit Enforcement
- If no `LIMIT` clause is present, appends one automatically
- Default: 1000 rows (configurable via `SQL_MAX_ROWS`)
- DB-specific syntax: `LIMIT N` for SQLite, `TOP N` for SQL Server

## Additional Safety

- Database connection uses read-only credentials in production (configured externally)
- Pre-built query library (20 queries) bypasses LLM entirely for common questions
- Sentry monitoring captures all exceptions with full stack traces
- Domain scoping limits which tables the LLM sees (4-10 tables per domain vs 147+ total)

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| SQL injection via user question | 5-stage validation pipeline |
| Data exfiltration | Row limits, domain scoping |
| Schema discovery | Only relevant tables exposed per domain |
| Privilege escalation | Read-only enforcement, no DDL/DML |
| Prompt injection | System prompt hardening, pre-built query priority |
