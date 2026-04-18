# Contributing to OpsMind

OpsMind is an open-source AI query tool for manufacturing operations. It runs 100% locally — no cloud, no paid APIs, no data leaves your machine. We want to keep it that way.

## The Prime Directive

**No paid APIs.** This project runs strictly on local models (Ollama), local vector search (ChromaDB), and local databases (SQLite/SQL Server). Do not submit PRs that introduce dependencies on any paid cloud AI service.

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/OpsMind.git
cd OpsMind
make setup          # Install deps + seed demo database
make test           # Run the pytest suite
make eval-library   # Run the fast eval (no Ollama needed)
make run            # Start Streamlit app
```

## How to Contribute

1. **Find an issue.** Look for issues tagged `good first issue` or `help wanted`.
2. **Claim it.** Comment on the issue saying you are picking it up so we don't duplicate work.
3. **Branch.** Fork the repo and create a branch (`feature/your-feature-name` or `bugfix/issue-description`).
4. **Code.** Keep Python clean. Follow existing patterns. Comment non-obvious logic.
5. **Test.** Add focused tests under `tests/unit/` (one file per module; see the
   existing files). Cross-module smoke tests continue to live in
   `tests/test_core.py`. Run `make test` before submitting.
6. **Pull request.** Explain *what* you changed and *why*. Reference the issue number.
   One logical change per commit makes review easier.

## Current Focus Areas

We are actively looking for contributions in these areas:

### High Priority
- **Docker deployment** — Dockerfile + docker-compose with Ollama service ([#1](https://github.com/Pawansingh3889/OpsMind/issues/1))
- **More pre-built SQL patterns** — Expand the query library beyond 10 patterns ([#2](https://github.com/Pawansingh3889/OpsMind/issues/2))
- **PostgreSQL support** — Add PostgreSQL dialect alongside SQLite and SQL Server ([#3](https://github.com/Pawansingh3889/OpsMind/issues/3))

### Medium Priority
- **Test coverage** — Expand pytest coverage for compliance and alert modules ([#4](https://github.com/Pawansingh3889/OpsMind/issues/4))
- **Slack/Teams webhooks** — Push alert notifications to messaging platforms ([#5](https://github.com/Pawansingh3889/OpsMind/issues/5))
- **Model benchmarking** — Compare Ollama models on SQL generation accuracy

### Nice to Have
- **UI/UX improvements** — Better Streamlit dashboard for factory floor use
- **PDF parsing** — More robust extraction for scanned manufacturing SOPs
- **Multi-language support** — Queries in languages other than English
- **Scheduled reports** — Automated daily/weekly production summaries

## Project Structure

```
OpsMind/
├── app.py                    # Streamlit app (entry point)
├── config.py                 # Configuration
├── schema.yaml               # Business domain to table mapping
├── Modelfile                 # Custom Ollama model with baked-in schema
├── Makefile                  # setup, run, test, clean commands
├── modules/
│   ├── sql_agent.py          # NL to SQL (start here to understand the core)
│   ├── query_library.py      # Pre-built SQL patterns (easiest to contribute to)
│   ├── schema_registry.py    # Domain detection
│   ├── sql_dialect.py        # SQLite / SQL Server / PostgreSQL abstraction
│   ├── database.py           # SQLAlchemy connection
│   ├── doc_search.py         # ChromaDB RAG
│   ├── compliance.py         # Traceability, allergens, audit
│   ├── alerts.py             # 5 alert types
│   ├── waste_predictor.py    # Yield and waste analysis
│   └── llm.py                # Ollama connection
├── tests/
│   └── test_core.py          # 36 pytest tests
├── scripts/
│   ├── seed_demo_db.py       # Demo database generator
│   ├── ingest_documents.py   # PDF loader for RAG
│   └── benchmark_models.py   # Model comparison script
└── docs/                     # Landing page (GitHub Pages)
```

## How to add a question to the eval golden set

OpsMind's accuracy claim is backed by `tests/eval/golden_set.yaml`. When you
add a new library pattern or want to raise confidence on the LLM path, extend
the golden set. The workflow:

1. **Decide the path.**
   - `library` — your question should match a pre-built regex pattern in
     `modules/query_library.py`. Good for catching silent regressions when
     someone tweaks a pattern.
   - `llm` — your question has **no** library match and forces real NL-to-SQL
     generation. This is where the LLM accuracy number lives.

2. **Add a sample to `tests/eval/golden_set.yaml`.**

   Library sample — no hand-written SQL needed, the judge reads the library:
   ```yaml
   - id: q21
     question: which line had the lowest yield yesterday
     path: library
     expected_pattern_description: Yield by production line (last 7 days)
     expected_columns: [production_date, line_name, ...]
   ```

   LLM sample — include reference SQL the judge will execute against the
   demo database. Result sets are compared, not SQL text, so your SQL need
   only agree with the LLM's *in output*:
   ```yaml
   - id: q22
     question: how many temperature breaches happened last month
     path: llm
     expected_sql: |
       SELECT COUNT(*) AS breaches
       FROM temp_logs
       WHERE recorded_at >= date('now', '-30 days')
         AND temperature > 5
   ```

3. **Run it.**
   ```bash
   make eval-library          # fast path
   make eval-llm              # requires Ollama + gemma3:12b
   ```

4. **When the LLM fails, log the failure mode.**
   Append one line to `tests/eval/failure_modes.md` under the matching
   heading (`llm/sql-error`, `llm/value-mismatch`, etc.). Don't rewrite
   history — fixes close entries, they don't delete them. This is the
   Seeler "cluster failures before tuning prompts" pattern: the taxonomy is
   what drives prompt changes, not a single hot datapoint.

5. **If your fix touches a prompt or the query library,** rerun the full
   eval and update the "fixed:" marker on the failure-mode entry with the
   commit SHA.

## Code Standards

- Python 3.11+
- Follow existing patterns in the codebase
- One responsibility per module
- Add tests for new functionality
- Keep dependencies minimal — check `requirements.txt` before adding new packages
- SQL safety: all generated SQL must be validated (SELECT/WITH only)

## Reporting Bugs

Open an issue using the bug report template. Include:
- Steps to reproduce
- Expected vs actual behaviour
- Python version, OS, Ollama model
- Error traceback (if applicable)

## Feature Requests

Open an issue using the feature request template. Describe:
- The problem it solves
- How it should work
- Which module it affects

## Recognition

All contributors will be credited in the README. Significant contributions may lead to maintainer access.
