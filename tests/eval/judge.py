"""Judge for the OpsMind golden evaluation set.

Two judges, one per path:

- ``judge_library(sample)``: the question must match a ``query_library`` pattern,
  the returned description must equal ``expected_pattern_description``, the SQL
  must execute cleanly, and the resulting DataFrame must expose every column in
  ``expected_columns``. No LLM is called.

- ``judge_llm(sample)``: the question must NOT match any library pattern (that
  would invalidate the test). We execute both ``expected_sql`` and the LLM's
  output via ``modules.sql_agent.run_query`` against the live demo DB and
  compare result sets.

Comparison is intentionally tolerant: column renames are fine (LLMs pick
slightly different aliases), but the *shape* of the answer must match — same
number of columns, same row count, and values that agree after sorting. For
floats we allow a small absolute tolerance so rounding choices don't trip the
judge.

Output is a ``Verdict`` dataclass the pytest runner turns into readable
assertion failures, plus a ``FailureMode`` label that gets appended to
``failure_modes.md`` for the taxonomy workflow (see Martin Seeler's "AI Evals
Done Right" — cluster failures before tuning prompts).
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Make the project root importable no matter where pytest is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

GOLDEN_SET_PATH = Path(__file__).with_name("golden_set.yaml")

# Floats within this absolute tolerance are considered equal (e.g. 94.2 vs 94.17).
FLOAT_TOLERANCE = 0.5


@dataclass
class Verdict:
    sample_id: str
    question: str
    path: str
    passed: bool
    reason: str
    failure_mode: str | None = None  # matches a heading in failure_modes.md


# --- Failure mode taxonomy -------------------------------------------------
# Seed entries — the taxonomy grows as real failures arrive. Keep strings in
# sync with the headings in tests/eval/failure_modes.md.
FM_LIBRARY_NO_MATCH = "library/no-match"
FM_LIBRARY_WRONG_PATTERN = "library/wrong-pattern"
FM_LIBRARY_SQL_ERROR = "library/sql-error"
FM_LIBRARY_COLUMN_MISSING = "library/column-missing"
FM_LLM_UNEXPECTED_LIBRARY_HIT = "llm/unexpected-library-hit"
FM_LLM_SQL_ERROR = "llm/sql-error"
FM_LLM_SHAPE_MISMATCH = "llm/shape-mismatch"
FM_LLM_VALUE_MISMATCH = "llm/value-mismatch"
FM_LLM_EMPTY_RESULT = "llm/empty-result"
FM_LLM_BLOCKED = "llm/blocked-by-validator"


# --- Helpers ---------------------------------------------------------------

def load_samples(path: Path = GOLDEN_SET_PATH) -> list[dict[str, Any]]:
    """Load golden_set.yaml. Raises FileNotFoundError with a useful message."""
    if not path.exists():
        raise FileNotFoundError(f"Golden set not found at {path}")
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return list(data.get("samples", []))


_EVAL_ENGINE = None


def _execute(sql: str) -> pd.DataFrame:
    """Execute SQL against the demo database.

    Deliberately bypasses ``modules.database`` so the library-path eval has
    no streamlit dependency — CI boxes and contributor laptops without the
    full app installed can still run ``make eval-library``. The LLM-path
    judge reaches into the real agent anyway, so the Streamlit cost only
    applies when it's genuinely needed.
    """
    global _EVAL_ENGINE
    if _EVAL_ENGINE is None:
        from sqlalchemy import create_engine

        db_url = os.environ.get("OPSMIND_DB") or f"sqlite:///{_PROJECT_ROOT / 'data' / 'demo.db'}"
        _EVAL_ENGINE = create_engine(db_url, echo=False)
    return pd.read_sql(sql, _EVAL_ENGINE)


def _frames_equivalent(expected: pd.DataFrame, actual: pd.DataFrame) -> tuple[bool, str]:
    """Compare two result frames tolerantly.

    Rules:
    - Same number of columns (column names may differ — LLMs rename freely).
    - Same number of rows.
    - Row-by-row equality after sorting both frames on their column order.
    - Floats compared with :data:`FLOAT_TOLERANCE` absolute tolerance.
    - NaN vs NaN treated as equal (stdlib ``pd.isna``).
    """
    if expected.shape[1] != actual.shape[1]:
        return False, (
            f"column count mismatch — expected {expected.shape[1]} "
            f"({list(expected.columns)}), got {actual.shape[1]} ({list(actual.columns)})"
        )
    if expected.shape[0] != actual.shape[0]:
        return False, (
            f"row count mismatch — expected {expected.shape[0]}, got {actual.shape[0]}"
        )

    # Sort both by all columns to normalise ordering, reset index so positional
    # comparison is meaningful.
    exp_sorted = expected.sort_values(by=list(expected.columns)).reset_index(drop=True)
    act_sorted = actual.sort_values(by=list(actual.columns)).reset_index(drop=True)

    for row_idx in range(len(exp_sorted)):
        for col_idx in range(exp_sorted.shape[1]):
            e_val = exp_sorted.iat[row_idx, col_idx]
            a_val = act_sorted.iat[row_idx, col_idx]
            if pd.isna(e_val) and pd.isna(a_val):
                continue
            if isinstance(e_val, (int, float)) and isinstance(a_val, (int, float)):
                if math.isnan(float(e_val)) and math.isnan(float(a_val)):
                    continue
                if abs(float(e_val) - float(a_val)) <= FLOAT_TOLERANCE:
                    continue
                return False, (
                    f"numeric diff at row {row_idx} col {col_idx}: "
                    f"expected {e_val}, got {a_val}"
                )
            if str(e_val) == str(a_val):
                continue
            return False, (
                f"value diff at row {row_idx} col {col_idx}: "
                f"expected {e_val!r}, got {a_val!r}"
            )
    return True, "equivalent"


# --- Judges ----------------------------------------------------------------

def judge_library(sample: dict[str, Any]) -> Verdict:
    """Library-path check — no LLM involved."""
    from modules.query_library import find_matching_query

    sid = sample["id"]
    question = sample["question"]
    expected_desc = sample.get("expected_pattern_description", "")
    expected_columns = sample.get("expected_columns", [])

    sql, desc = find_matching_query(question)
    if sql is None:
        return Verdict(
            sid, question, "library", False,
            "query_library.find_matching_query returned no match",
            FM_LIBRARY_NO_MATCH,
        )
    if expected_desc and desc != expected_desc:
        return Verdict(
            sid, question, "library", False,
            f"matched wrong pattern — expected {expected_desc!r}, got {desc!r}",
            FM_LIBRARY_WRONG_PATTERN,
        )
    try:
        df = _execute(sql)
    except Exception as exc:  # noqa: BLE001 — we want to surface any SQL error
        return Verdict(
            sid, question, "library", False,
            f"library SQL failed to execute: {exc}",
            FM_LIBRARY_SQL_ERROR,
        )
    missing = [c for c in expected_columns if c not in df.columns]
    if missing:
        return Verdict(
            sid, question, "library", False,
            f"library result missing columns {missing} — got {list(df.columns)}",
            FM_LIBRARY_COLUMN_MISSING,
        )
    return Verdict(sid, question, "library", True, "library path OK")


def judge_llm(sample: dict[str, Any]) -> Verdict:
    """LLM-path check — runs the real agent against Ollama.

    Skipped at pytest layer when ``OPSMIND_EVAL_SKIP_LLM=1`` or when Ollama
    isn't reachable; this function assumes the caller already verified the
    agent stack is up.
    """
    from modules.query_library import find_matching_query
    from modules.sql_agent import run_query

    sid = sample["id"]
    question = sample["question"]
    expected_sql = sample["expected_sql"]

    # Guard: LLM samples must NOT match a library pattern, otherwise the test
    # isn't measuring the LLM at all.
    sql, _ = find_matching_query(question)
    if sql is not None:
        return Verdict(
            sid, question, "llm", False,
            "question unexpectedly matched a library pattern — move it to library path",
            FM_LLM_UNEXPECTED_LIBRARY_HIT,
        )

    try:
        expected_df = _execute(expected_sql)
    except Exception as exc:  # noqa: BLE001
        return Verdict(
            sid, question, "llm", False,
            f"expected_sql failed to execute (fix golden set): {exc}",
            FM_LLM_SQL_ERROR,
        )

    result = run_query(question)
    if result.get("error"):
        # Distinguish "validator blocked it" from "LLM produced bad SQL".
        explanation = (result.get("explanation") or "").lower()
        mode = FM_LLM_BLOCKED if "blocked" in explanation or "read-only" in explanation else FM_LLM_SQL_ERROR
        return Verdict(
            sid, question, "llm", False,
            f"run_query error: {result.get('explanation')}",
            mode,
        )

    actual_df = result.get("data")
    if actual_df is None or not isinstance(actual_df, pd.DataFrame):
        return Verdict(
            sid, question, "llm", False,
            "run_query returned no DataFrame",
            FM_LLM_SQL_ERROR,
        )

    if expected_df.empty and actual_df.empty:
        # Both empty — count as pass (matches factory reality of quiet days),
        # but tag so we can review whether the question is low-signal.
        return Verdict(sid, question, "llm", True, "both empty — low-signal sample")

    if actual_df.empty and not expected_df.empty:
        return Verdict(
            sid, question, "llm", False,
            "LLM SQL returned 0 rows while expected_sql returned rows",
            FM_LLM_EMPTY_RESULT,
        )

    ok, reason = _frames_equivalent(expected_df, actual_df)
    if not ok:
        mode = FM_LLM_SHAPE_MISMATCH if "mismatch" in reason and "row" in reason or "column" in reason else FM_LLM_VALUE_MISMATCH
        return Verdict(sid, question, "llm", False, reason, mode)
    return Verdict(sid, question, "llm", True, "llm path OK")


# --- CLI -------------------------------------------------------------------

def _summarise(verdicts: list[Verdict]) -> str:
    by_path: dict[str, list[Verdict]] = {}
    for v in verdicts:
        by_path.setdefault(v.path, []).append(v)
    lines = []
    for path, vs in sorted(by_path.items()):
        passed = sum(1 for v in vs if v.passed)
        lines.append(f"{path}: {passed}/{len(vs)}")
    return "  |  ".join(lines)


def main() -> int:
    """Run every sample and print a summary. Exits non-zero if any fail."""
    samples = load_samples()
    skip_llm = os.environ.get("OPSMIND_EVAL_SKIP_LLM") == "1"
    verdicts: list[Verdict] = []
    for sample in samples:
        path = sample.get("path", "library")
        if path == "llm" and skip_llm:
            print(f"[SKIP] {sample['id']}  {sample['question']}  (OPSMIND_EVAL_SKIP_LLM=1)")
            continue
        judge = judge_library if path == "library" else judge_llm
        verdict = judge(sample)
        verdicts.append(verdict)
        mark = "PASS" if verdict.passed else "FAIL"
        print(f"[{mark}] {verdict.sample_id}  {verdict.question}")
        if not verdict.passed:
            print(f"       -> {verdict.reason}")
            if verdict.failure_mode:
                print(f"       failure_mode: {verdict.failure_mode}")
    print()
    print("SUMMARY: " + _summarise(verdicts))
    return 0 if all(v.passed for v in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
