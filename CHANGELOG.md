# Changelog

All notable user-facing changes to OpsMind are logged here.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
OpsMind is deployed, not released — so entries accumulate under
`[Unreleased]` and only gain a version + date when a tagged release is
cut (none today; see `GOVERNANCE.md` § Release cadence for the rule).

## [Unreleased]

### Added

- **Eval harness** (`tests/eval/`) — golden set of 20 factory questions
  across library and LLM paths, judge with result-set equivalence,
  failure-mode taxonomy in `tests/eval/failure_modes.md`. Runs via
  `make eval-library` (no Ollama) or `make eval` (full).
- **Four golden-set make targets** — `make eval`, `make eval-library`,
  `make eval-llm`, `make typecheck-ty` for CI-parity type checking.
- **Per-module unit tests** under `tests/unit/` — `test_sql_validator.py`
  (28 tests + 1 documented xfail covering all 5 pipeline stages),
  `test_query_library.py` (regex-collision guards + happy paths),
  `test_schema_registry.py` (all 7 domains + edges).
- **Governance paperwork** — `GOVERNANCE.md`, `SECURITY.md`,
  `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `THIRD_PARTY_NOTICES.md`,
  plus `NOTICE` per Apache 2.0 § 4(d). Full contributor contract now
  visible on the repo without anyone asking.
- **Contributor-experience automation** — PR template with checklist,
  CODEOWNERS auto-routing reviews, first-contributor welcome workflow,
  conventional-commit PR-title validator.
- **MCP tool docstrings expanded** — every tool in
  `mcp_servers/database_server.py` and `doc_search_server.py` now
  carries "Use this when" context, full domain lists, and example
  inputs/outputs so LLM clients pick the right tool without a
  round-trip.

### Changed

- **Relicensed from MIT to Apache 2.0.** Solo-authored codebase, so the
  relicense is clean. Apache 2.0 adds an explicit patent grant and the
  NOTICE convention. `sql-sop` stays on MIT separately because it's a
  published PyPI package and downstream users expect that licence.
- **CI opts into Node.js 24** via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`
  (closes #9). Covers the full lint + 3.11 + 3.12 test matrix.
- **Library path pattern 5 tightened** to word-boundary the `product`
  alternative so "yield by production line" no longer greedy-matches.
  Caught by the eval harness on its first run; fix lands with
  test coverage in `tests/unit/test_query_library.py`.
- **README accuracy claim** — replaced the unverified "~60%" with a
  pointer to `tests/eval/`. Current number is whatever the harness
  reports on your model + schema.

### Fixed

- **Pattern-16 regex collision** (giveaway) — same class of bug as the
  pattern-5 fix. `(product|plu).*waste` now uses word-boundaries so
  "production batches with waste" no longer steals that route.
- **`test_sql_validator.py` lint nit** — extra blank line after import
  block dropped per ruff I001.

### Closed issues

- #1 Add Dockerfile for containerised deployment
- #2 Add more pre-built query patterns (10 → 18)
- #9 Upgrade GitHub Actions to Node.js 24

---

*Earlier history lives in the git log — `git log --oneline` on any
commit on `main`.*
