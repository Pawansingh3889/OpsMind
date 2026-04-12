# AGENTS.md

> Context file for AI assistants working on this codebase.

## Project Overview

OpsMind is an on-prem, natural-language-to-SQL query tool for manufacturing (fish processing). It lets factory operators ask questions in English and get SQL results, charts, and plain-English explanations -- all offline, with no cloud API keys required. The LLM runs locally via Ollama (Gemma 3 12B).

## Architecture

```
User question
    |
    v
Query Library (fast path) -- 18 pre-built regex patterns, guaranteed-correct SQL
    |  no match
    v
Schema Registry (7 domains) -- keyword detection picks relevant tables
    |
    v
LLM (Ollama) -- generates SQL from question + filtered schema
    |
    v
SQL Agent -- safety check, then SQLAlchemy execution (read-only)
    |
    v
Result table + Plotly chart + LLM explanation
```

### LangGraph Agent (`modules/agent_graph.py`)

The NL-to-SQL pipeline is implemented as a LangGraph state graph with 6 nodes and conditional edges:

1. **detect_domain** -- calls `schema_registry.detect_domain()` to identify the business domain.
2. **check_library** -- calls `query_library.find_matching_query()` for a pre-built SQL match.
3. **generate_sql** -- if no library match, generates SQL via the LLM with domain-scoped schema.
4. **validate_sql** -- safety gate: only `SELECT`/`WITH` allowed; blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`, `xp_`, `sp_`.
5. **execute_sql** -- runs the validated query via `database.query()`.
6. **explain_results** -- LLM explains results in plain English for managers.

**Edge logic:**
- If `check_library` finds a match, the graph skips `generate_sql` and jumps to `validate_sql`.
- If `validate_sql` detects unsafe SQL, the graph short-circuits to END with an error.

**State schema:** `{question, domain, sql, results, explanation, error}`

**Entry point:** `ask(question)` builds and invokes the compiled graph, returning the final state dict.

### Seven Business Domains

The schema registry maps questions to one of seven domains via keyword matching: `traceability`, `production`, `orders`, `temperature`, `staff`, `stock`, `compliance`. Each domain exposes only its relevant tables to the LLM prompt, keeping context small.

### RAG Document Search

The vector search backend is pluggable. Set `OPSMIND_VECTOR_DB` to `chromadb` (default) or `pgvector`.

- **ChromaDB** (default) -- local embedded store via `modules/doc_search.py`. No external services.
- **PostgreSQL + pgvector** -- production backend via `modules/doc_search_pg.py`. Requires `OPSMIND_VECTOR_PG_URL`. Falls back to ChromaDB if PostgreSQL is unreachable.

Both backends store factory PDFs (SOPs, HACCP plans, audit reports) as 384-dimensional embeddings from `all-MiniLM-L6-v2`. Ingestion splits PDFs into ~500-char overlapping chunks. The public API is identical: `search()`, `ingest_pdf()`, `ingest_text()`, `add_document()`, `get_doc_count()`.

## Key Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit entry point, 7-tab UI (SQL Chat, Document Search, Dashboard, Compliance, Alerts, Excel Upload, Schema Registry) |
| `config.py` | All configuration: Ollama model, database URL, ChromaDB path, alert thresholds |
| `modules/agent_graph.py` | LangGraph multi-step agent: 6-node state graph (detect_domain, check_library, generate_sql, validate_sql, execute_sql, explain_results) with conditional edges |
| `modules/sql_agent.py` | NL-to-SQL pipeline: query library check, LLM fallback, safety validation, execution, explanation |
| `modules/schema_registry.py` | Domain detection (keyword scoring), table filtering, LLM prompt construction. Contains `DEFAULT_SCHEMA` and `DOMAIN_KEYWORDS` |
| `modules/query_library.py` | 18 pre-built SQL patterns with regex matching. Returns tested SQL for common questions without invoking the LLM |
| `modules/doc_search.py` | ChromaDB vector search for factory PDFs. Functions: `search()`, `ingest_pdf()`, `add_document()` |
| `modules/doc_search_pg.py` | Pluggable vector search (pgvector or ChromaDB). Same public API as `doc_search.py` with PostgreSQL+pgvector backend and automatic fallback |
| `modules/sql_dialect.py` | SQL dialect abstraction layer. Generates correct date functions for SQLite (demo) vs SQL Server (production) |
| `modules/database.py` | SQLAlchemy engine creation and management |
| `modules/llm.py` | Ollama API integration (prompt/response, streaming) |
| `modules/compliance.py` | Batch tracing, temperature excursions, allergen matrix, compliance scoring |
| `modules/alerts.py` | Threshold-based alert detection (yield drops, temp breaches, overtime, expiring stock) |
| `modules/waste_predictor.py` | Waste trends, yield analysis, AI-driven waste predictions |
| `modules/excel_agent.py` | Excel/CSV upload and ad-hoc analysis |
| `scripts/seed_demo_db.py` | Generates 60 days of synthetic manufacturing data into `data/demo.db` |
| `scripts/ingest_documents.py` | Indexes PDFs from `docs/` into ChromaDB |
| `tests/test_core.py` | All 36 tests in a single file |

## Database Schema

19 tables total: 8 original tables + 11 production ERP tables (`prod_*` prefix).

**Original tables:** `products`, `raw_materials`, `production`, `orders`, `waste_log`, `temp_logs`, `staff`, `documents`

**Production ERP tables:** `prod_products`, `prod_runs`, `prod_lines`, `prod_transactions`, `prod_run_totals`, `prod_traceability`, `prod_temperature_logs`, `prod_non_conformance`, `prod_case_verification`, `prod_despatch`, `prod_shifts`

All tables use `snake_case` naming. Demo data is SQLite; production targets SQL Server via the `OPSMIND_DB` environment variable.

## Running Tests

```bash
python -m pytest tests/ -v
```

All 36 tests are in `tests/test_core.py`. Tests auto-seed the demo database if it does not exist (see the `ensure_demo_db` fixture). Test coverage includes: config loading, SQL dialect abstraction, schema registry domain detection, database queries, compliance/traceability, alert detection, waste prediction, SQL injection prevention, and document search.

## Running the App

```bash
# Pull the LLM model
ollama pull gemma3:12b

# Seed demo data
python scripts/seed_demo_db.py

# Index documents for RAG
python scripts/ingest_documents.py

# Launch
streamlit run app.py
```

Or: `make setup && make run`

## Safety and Security Constraints

**This is critical -- all generated SQL must be read-only.**

The `sql_agent.py` module enforces two layers of protection:

1. **Allowlist:** Only queries starting with `SELECT` or `WITH` (CTEs) are executed.
2. **Blocklist:** Queries containing any of the following keywords are rejected: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`, `EXECUTE`, `xp_`, `sp_`.

Any change to SQL generation or execution must preserve these safety checks. Never allow write operations against the database.

## Conventions

- **Read-only SQL only.** `SELECT` and `WITH` (CTEs) are the only allowed statement types.
- **Snake_case everywhere.** All table names, column names, and Python identifiers use `snake_case`.
- **Query library first.** The pre-built query library is checked before invoking the LLM. Add new patterns there for frequently asked questions.
- **Domain-scoped prompts.** The LLM only sees tables relevant to the detected domain, not the full schema.
- **SQL dialect abstraction.** Use functions from `modules/sql_dialect.py` (`days_ago()`, `days_ahead()`, `days_until()`, etc.) instead of raw date SQL. This keeps queries portable between SQLite and SQL Server.
- **Currency in GBP, weights in kg.** All monetary values are British pounds; all weights are kilograms.
- **Streamlit caching.** SQL query results are cached for 5 minutes via `@st.cache_data(ttl=300)`.
- **Environment variables for config.** Database connection: `OPSMIND_DB`. Ollama model: `OLLAMA_MODEL`. Schema file: `SCHEMA_CONFIG`. ChromaDB directory: `OPSMIND_CHROMA_DIR`. Vector backend: `OPSMIND_VECTOR_DB` (`chromadb` or `pgvector`). pgvector connection: `OPSMIND_VECTOR_PG_URL`.

## Adding a New Pre-Built Query

1. Add a new entry to the `QUERY_LIBRARY` list in `modules/query_library.py`.
2. Each entry needs: `patterns` (list of regex strings), `sql` (a lambda returning the SQL string), and `description` (short human-readable label).
3. Use dialect functions from `modules/sql_dialect.py` for date expressions.
4. Add a test in `tests/test_core.py` to verify the pattern matches.

## Adding a New Domain

1. Add the domain to `DEFAULT_SCHEMA` in `modules/schema_registry.py` with its tables and columns.
2. Add keywords to `DOMAIN_KEYWORDS` in the same file.
3. Add corresponding pre-built queries to `modules/query_library.py` if applicable.
