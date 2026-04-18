# OpsMind failure-mode taxonomy

Pattern: annotate bad outputs -> cluster into failure modes -> build a taxonomy -> use the taxonomy as the judge rubric. (Martin Seeler, "AI Evals Done Right", PyCon DE 2026.)

This document is a **living record**. Every real failure surfaced by `make eval` gets one line under the right heading. Don't rewrite history — append. The taxonomy drives prompt changes; prompt changes must not delete entries (only close them with the commit SHA that fixed them).

Labels below are the string constants `judge.py` writes to verdicts; keep them in sync.

---

## library/no-match

`query_library.find_matching_query` returned `None` for a question we said was on the fast path. Means either the question wording drifted from real operator vocabulary, or the regex patterns got too narrow.

_no entries yet_

## library/wrong-pattern

Pattern matched, but not the one the golden set expected — two patterns overlap. Fix is usually reordering patterns or tightening a regex, not adding a new one.

- 2026-04-18  q11  "yield by production line last week"  pattern 5 `(yield|yields).*(product|by product|trend|average)` wins over pattern 11 `yield.*(line|production line)` because "product" greedily matches "production". Fixed by tightening pattern 5's alternatives to `\bproduct\b`, `\bby\s+product\b`, etc.  (fixed: see commit — query_library.py pattern 5)

## library/sql-error

A library SQL template crashed. Look for: column renamed in `seed_demo_db.py`, new SQLite version breaking a date function, schema drift between demo and production configs.

_no entries yet_

## library/column-missing

Library SQL ran but returned a different column set than the golden set documents. Either the library changed (update the golden set) or someone broke the contract (revert).

_no entries yet_

---

## llm/unexpected-library-hit

An LLM-path question started matching a library pattern (because someone added a broader pattern). Either move the question to the library path or tighten the new pattern.

_no entries yet_

## llm/sql-error

LLM generated SQL that SQLite refused to execute. Common causes:
- Hallucinated column names
- Wrong date function for dialect (SQLite vs MSSQL)
- Wrong quoting on string literals

_no entries yet_

## llm/blocked-by-validator

`sql_validator` rejected the SQL before execution — usually because the LLM wrote `INSERT`/`UPDATE`/`DELETE` or a dangerous pattern. Rare, and usually a prompt issue.

_no entries yet_

## llm/shape-mismatch

SQL executed, but column count or row count diverged from expected. Often means the LLM picked wrong aggregation granularity (daily vs weekly, or forgot a `GROUP BY`).

_no entries yet_

## llm/value-mismatch

Same shape, wrong values. This is the subtle one — usually a wrong filter, wrong join, or wrong date window. Look here before tuning prompts on other categories.

_no entries yet_

## llm/empty-result

Expected rows, got zero. Usually a filter that's too tight (wrong date range, wrong case sensitivity on a `LIKE`, wrong join key).

_no entries yet_

---

## Entry template

When adding an entry, keep it one line:

```
- YYYY-MM-DD  qNN  "<question>"  <observation>  (fixed: <commit-sha or "pending">)
```

Example:
```
- 2026-04-18  q16  "which operator ran the most batches"  LLM returned ALL operators instead of top 1 — missing LIMIT  (fixed: pending)
```
