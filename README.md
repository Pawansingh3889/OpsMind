<div align="center">

# OpsMind

**AI query tool for manufacturing — runs on your machine, not the cloud**

[![Docs](https://img.shields.io/badge/Docs-Website-0f172a?style=flat-square&logo=googlechrome&logoColor=white)](https://pawansingh3889.github.io/OpsMind/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![Tests](https://img.shields.io/badge/Tests-passing-22c55e?style=flat-square&logo=pytest&logoColor=white)](https://github.com/Pawansingh3889/OpsMind/actions)
[![Eval](https://img.shields.io/badge/Eval-measured-2563eb?style=flat-square)](tests/eval/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)

</div>

## Links
- [GitHub](https://github.com/Pawansingh3889/OpsMind)
- [Documentation](https://pawansingh3889.github.io/OpsMind/)
- [Profile](https://github.com/Pawansingh3889)
- [PyPI (sql-sop)](https://pypi.org/project/sql-sop/)
- [Download Stats](https://pypistats.org/packages/sql-sop)
- **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`GOVERNANCE.md`](GOVERNANCE.md) · [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) · [`SECURITY.md`](SECURITY.md)

---

## What Problem Does This Solve?

Factory managers and shift leads need answers from production data — yield, waste, compliance, traceability. Today, they either write SQL themselves (error-prone), wait for IT (slow), or export to Excel (outdated by the time it opens). OpsMind lets anyone type a question in plain English and get an answer in 5 seconds, directly from the production database.

### Key Features

- **Ask in English, get answers in seconds** — no SQL knowledge required
- **Runs entirely on your machine** — no data leaves the factory network
- **SQL injection protection** — validates every query before execution
- **Covers 7 business areas** — production, waste, orders, compliance, staff, suppliers, traceability
- **Smart alerts** — flags yield drops, temperature breaches, and overtime automatically
- **Domain-aware** — loads compliance, production, and waste rules at runtime for context-aware answers

---

Manufacturing teams query data through Excel exports and IT requests. OpsMind lets any operator ask the database in English — offline, on-prem, no API keys.

Includes production ERP integration with 19 tables covering batch-centric runs, waterfall yield tracking (Premium/Standard/Export tiers), batch lineage for OCM scan-back traceability, and shelf life management.

---

## See it run

<div align="center">
<img src="docs/app-preview.png" alt="OpsMind dashboard" width="100%">
</div>

```
$ ollama pull gemma3:12b
$ streamlit run app.py

┌─────────────────────────────────────────────────┐
│ OpsMind — 7 tabs loaded                         │
│                                                 │
│ > "What was the yield for cod fillets last week?"│
│                                                 │
│ Detecting domain... production (2 tables)       │
│ Generating SQL...                               │
│ SELECT ProductCode, AVG(YieldPercent)            │
│   FROM ProductionRuns                           │
│   WHERE ProductCode = 'COD-F'                   │
│   AND ProductionDate >= date('now', '-7 days')  │
│   GROUP BY ProductCode;                         │
│                                                 │
│ ┌──────────┬──────────────┐                     │
│ │ Product  │ Avg Yield %  │                     │
│ ├──────────┼──────────────┤                     │
│ │ COD-F    │ 94.2%        │                     │
│ └──────────┴──────────────┘                     │
│                                                 │
│ "Cod fillet yield averaged 94.2% last week,     │
│  which is 1.8% above your 30-day average."      │
└─────────────────────────────────────────────────┘
```

---

## How it works

```
User asks: "What was yesterday's waste?"
      │
      ▼
┌─────────────┐     ┌──────────────────┐
│ Query Library│────▶│ 10 pre-built SQL │──── Match? ───▶ Execute instantly
│ (fast path)  │     │ patterns          │
└─────────────┘     └──────────────────┘
      │ No match
      ▼
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ Schema       │────▶│ Pick 4 tables    │────▶│ Ollama LLM   │
│ Registry     │     │ from 19          │     │ (Gemma3 12B)  │
│ (7 domains)  │     │ (domain match)   │     │              │
└─────────────┘     └──────────────────┘     └──────────────┘
                                                    │
                                                    ▼
                                             ┌──────────────┐
                                             │ SQLAlchemy    │
                                             │ execute       │
                                             └──────────────┘
                                                    │
                                             ┌──────┴──────┐
                                             ▼             ▼
                                        Result Table   Plotly Chart
                                             │
                                             ▼
                                        LLM explains in
                                        plain English
```

**Step 1 — Domain detection.** User asks about "orders" → schema registry maps it to 2 tables out of 19. Only those go to the LLM.

**Step 2 — SQL generation.** Ollama converts the question to SQL. Pre-built library short-circuits the 10 most common questions.

**Step 3 — Execution.** SQLAlchemy runs the query (read-only — INSERT/UPDATE/DELETE blocked). Result rendered as table + Plotly chart.

**Step 4 — Explanation.** LLM summarises the result in English with context ("above average", "trending down").

---

## All 7 modules in action

```
┌─────────────────────────────────────────────────────────────┐
│  TAB 1: SQL Chat                                            │
│  "How many orders shipped late this month?"                 │
│  → 12 orders, 3.4% of total. Worst day: Tuesday 18th.     │
│                                                             │
│  TAB 2: Document Search (RAG)                               │
│  Upload: allergen-procedure-v3.pdf                          │
│  "What's the allergen cleaning protocol?"                   │
│  → "Section 4.2: All surfaces must be cleaned with..."     │
│  → Source: allergen-procedure-v3.pdf, page 8               │
│                                                             │
│  TAB 3: Production Dashboard                                │
│  Output: 2,841 kg  │ Waste: 187 kg  │ Yield: 93.8%        │
│  Orders: 38 open   │ Shipped: 412   │ Late: 12            │
│                                                             │
│  TAB 4: Compliance & Traceability                           │
│  Batch COD-2024-0847:                                       │
│    Raw material → Supplier ABC, intake 06:12                │
│    Production → Line 2, yield 95.1%                         │
│    Despatch → Customer XYZ, temp 2.1°C ✓                   │
│                                                             │
│  TAB 5: Smart Alerts                                        │
│  ⚠ Yield drop: Haddock -4.2% vs 30-day avg                │
│  ⚠ Cold Room 2: 5.3°C (threshold: 5.0°C)                  │
│  ⚠ 3 batches expiring within 48 hours                      │
│                                                             │
│  TAB 6: Excel Upload                                        │
│  Uploaded: march-production.xlsx (340 rows)                 │
│  "What product had the most waste?"                         │
│  → Salmon fillets: 42kg waste (8.1% of output)             │
│                                                             │
│  TAB 7: Schema Registry                                     │
│  7 domains │ up to 147 tables │ 4 selected for current query     │
└─────────────────────────────────────────────────────────────┘
```

---

## Build it

```bash
# Step 1: Get Ollama running
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:12b      # default model, better SQL accuracy

# Step 2: Clone and install
git clone https://github.com/Pawansingh3889/OpsMind.git
cd OpsMind
pip install -r requirements.txt

# Step 3: Seed demo data (60 days of synthetic manufacturing data)
python scripts/seed_demo_db.py
# → Products: 10 | Runs: 662 | Orders: 451 | Temp logs: 3,600 | Materials: 282

# Step 4: Index documents for RAG search
python scripts/ingest_documents.py
# → Indexing PDFs into ChromaDB vectors...

# Step 5: Run
streamlit run app.py
# → OpsMind running at http://localhost:8501
```

Or one-liner: `make setup && make run`

## Docker deployment (production)

Isolated deployment pattern inspired by PyCon DE 2026: "Building Secure Environments for CLI Code Agents" (Nezbeda).

```bash
# One-command deployment: app + Ollama in isolated containers
docker compose up -d

# OpsMind: http://localhost:8501
# Ollama:  http://localhost:11434
```

What this gives you:
- OpsMind runs as non-root user in a minimal Python 3.11 container
- Ollama runs in a separate container (isolated bridge network)
- Model weights persist in a named volume
- Logs persist outside containers at `./logs/`
- Health checks on both services with auto-restart
- No secrets in images — all configuration via environment variables

## Audit logging

Every agent interaction is logged to `logs/audit.jsonl` as structured JSON.

```bash
# Last 10 SQL executions
jq -c 'select(.event == "sql_executed")' logs/audit.jsonl | tail -10

# All validation failures
jq -c 'select(.event == "sql_validated" and .passed == false)' logs/audit.jsonl

# Questions per day
jq -r 'select(.event == "question_asked") | .timestamp[:10]' logs/audit.jsonl | sort | uniq -c
```

Events logged: `question_asked`, `sql_generated`, `sql_validated`, `sql_executed`, `llm_call`.

Required for BRC traceability — every query, who asked, what SQL ran, what came back.

---

## Run the tests

Three suites, three commands:

```bash
make test           # cross-module smoke (tests/test_core.py) + per-module (tests/unit/)
make eval-library   # library fast-path eval — no Ollama needed
make eval           # full eval (library + LLM paths) — needs Ollama + gemma3:12b
```

Coverage at a glance:

| Suite | File | What it covers |
|---|---|---|
| Smoke | `tests/test_core.py` | Config, SQL dialect, schema registry, database, compliance, alerts, waste, SQL safety, doc search — one test per concern. |
| Per-module | `tests/unit/test_sql_validator.py` | Every stage of the 5-stage SQL validation pipeline (statement type, injection, table existence, column resolution, row-limit injection). |
| Per-module | `tests/unit/test_query_library.py` | One canonical question per library pattern + explicit regex-collision guards. |
| Per-module | `tests/unit/test_schema_registry.py` | Domain detection for all 7 domains, edge cases, registry contracts. |
| Eval | `tests/eval/golden_set.yaml` | 20 factory questions — 14 library-path, 6 LLM-path. Judge compares result sets against the demo database. |

Failure-mode taxonomy for the eval harness lives in
[`tests/eval/failure_modes.md`](tests/eval/failure_modes.md) — it's a
living document that grows as the LLM path hits real failures.

---

## Connect to production SQL Server

```bash
# Environment variable — connection string
OPSMIND_DB=mssql+pyodbc://user:pass@server/database?driver=ODBC+Driver+17+for+SQL+Server

# Windows Auth
OPSMIND_DB=mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

Then edit `schema.yaml` to map your tables to OpsMind's 7 business domains:

```yaml
traceability:
  tables:
    ProductionBatch: BatchID, BatchNo, ProductCode, ProductionDate
    RawMaterialIntake: IntakeID, ProductCode, BatchNo, SupplierCode

production:
  tables:
    ProductionRuns: RunID, ProductCode, FinishedOutputKg, WasteKg

# Also: orders, temperature, staff, stock, compliance
```

> **Production ERP integration:** Includes 19 production ERP tables (runs, traceability, temperature, non-conformance, shifts, despatch, shelf life, yield tiers) with 8 pre-built SQL queries and 3 production-specific alerts.

> Production data follows a batch-centric run structure: one batch feeds one run producing multiple products across RSPCA (Tier 1), GG (Tier 2), and catch-all (Tier 3) tiers. The schema registry maps these tables to 7 business domains for efficient NL-to-SQL query generation.

## Production Queries

8 pre-built production queries for instant results (no LLM round-trip):

| # | Query | Description |
|---|---|---|
| 1 | Daily yield by production line | Yield % per line for a given date, compared to 30-day average |
| 2 | Batch traceability lookup (batch to vessel) | Full lineage from finished batch back to raw material vessel/intake |
| 3 | Temperature breach report | All cold-store and in-process readings outside threshold in a date range |
| 4 | Allergen changeover check | Validates cleaning records between allergen-class changeovers on a line |
| 5 | Shift productivity (day vs night) | Output kg, waste kg, and yield % split by shift for comparison |
| 6 | Giveaway analysis by product | Overweight giveaway per product vs target, ranked by cost impact |
| 7 | Open critical non-conformances | All open NCs with severity = Critical, grouped by category and age |
| 8 | MSC/ASC certification status | Current certification status per species/supplier with expiry dates |

## Production Alerts

3 production-specific alerts monitored continuously:

- **Yield drops** — flags when line yield falls below the 30-day rolling average by a configurable threshold
- **Temperature breaches** — triggers when any cold-store or in-process sensor exceeds its defined limit
- **Open critical NCs** — alerts when critical non-conformances remain unresolved past the SLA window

---

## Vector Search Backend

OpsMind supports two vector backends for RAG document search:

### ChromaDB (default)

Local, embedded vector store. No external services needed -- works out of the box.

```bash
# No extra config required. ChromaDB is the default.
OPSMIND_VECTOR_DB=chromadb   # optional, this is the default
```

### PostgreSQL + pgvector (production)

Shared, production-grade vector store backed by PostgreSQL with the pgvector extension. Recommended when multiple OpsMind instances need to share the same document index, or when you want vector search co-located with your existing PostgreSQL database.

```bash
# 1. Install pgvector in your PostgreSQL instance
#    https://github.com/pgvector/pgvector

# 2. Point OpsMind at the database
OPSMIND_VECTOR_DB=pgvector
OPSMIND_VECTOR_PG_URL=postgresql+psycopg2://user:pass@host:5432/opsmind
```

OpsMind will automatically create the `documents` table and the pgvector extension on first use. If PostgreSQL is unreachable, the system falls back to ChromaDB so the app keeps working.

---

## Stack

| Layer | Tool | What it does |
|---|---|---|
| LLM | Ollama (Gemma 3 12B) | English to SQL, result explanation |
| Agent | LangGraph (6-node state graph) | Structured NL-to-SQL pipeline with conditional routing |
| MCP Servers | FastMCP (database + doc search) | Decoupled tool servers via Model Context Protocol |
| SQL Validation | sqlparse + custom validator | Injection detection, schema checks, row limits |
| Database | SQLAlchemy | SQLite (demo) + SQL Server (production) |
| Vector Search | ChromaDB or PostgreSQL+pgvector | PDF and SOP search (RAG) |
| Domain Docs | Runtime-loaded markdown | Compliance, production, waste rules injected into LLM context |
| UI | Streamlit (7 tabs) | Dashboard, chat, charts |
| Charts | Plotly | Production and waste visualisation |
| Config | YAML + env vars | Schema registry, alert thresholds, MCP settings |
| Tests | pytest | Unit + integration tests |
| Lint | ruff + ty (Astral) | Linting and type checking in CI |

---

## Architecture

```
User Question (plain English)
    |
    v
[LangGraph Agent] --- 6-node state graph
    |
    +---> [Query Library] --- 8 pre-built queries (fast path)
    |
    +---> [Schema Registry] --- 7 domains, 19 tables
    |
    +---> [Ollama / Gemma 3 12B] --- NL-to-SQL generation
    |
    v
[SQL Validation] --- read-only enforcement
    |
    v
[SQLAlchemy] --- execute query
    |
    v
[Results + Explanation]

RAG: ChromaDB or PostgreSQL pgvector
Monitoring: Sentry (opt-in)

MCP Servers (opt-in):
    [Database Server :9000] --- query, discover tables/columns, domain schema
    [Doc Search Server :9001] --- semantic search, domain context
    [MCP Client] --- connects to servers or falls back to direct module calls
```

## MCP Server Architecture

OpsMind can optionally expose database and document search as [MCP](https://modelcontextprotocol.io/) servers, decoupling data access from agent logic. This follows patterns from the PyCon DE 2026 talk on building agentic systems with LangGraph and MCP.

| Server | Port | Tools |
|---|---|---|
| Database | 9000 | `query_database`, `discover_tables`, `discover_columns`, `get_schema_for_domain` |
| Doc Search | 9001 | `search_documents`, `get_document_count`, `get_domain_context` |

MCP is opt-in. Set `MCP_ENABLED=true` to use the servers. When disabled (default), OpsMind calls modules directly — no behaviour change.

```bash
# Start MCP servers
python -m mcp_servers.database_server
python -m mcp_servers.doc_search_server

# Run OpsMind with MCP
MCP_ENABLED=true streamlit run app.py
```

See `specs/mcp-servers.md` for full documentation.

## Agent Architecture

OpsMind uses a LangGraph state graph to structure the NL-to-SQL pipeline as a multi-step agent with 6 nodes:

```
question -> [detect_domain] -> [check_library] --match--> [validate_sql] -> [execute_sql] -> [explain_results]
                                     |                          |
                                  no match                  invalid SQL
                                     |                          |
                               [generate_sql] -------->     END (error)
```

| Node | Purpose |
|---|---|
| `detect_domain` | Maps the question to one of 7 business domains via keyword scoring |
| `check_library` | Checks 18 pre-built regex patterns for a fast-path match (no LLM needed) |
| `generate_sql` | LLM generates SQL from the question and domain-scoped schema |
| `validate_sql` | Safety gate -- only SELECT/WITH allowed, blocks dangerous keywords |
| `execute_sql` | Runs the validated query via SQLAlchemy (read-only) |
| `explain_results` | LLM explains results in plain English with business context |

**Pre-built library fast path** -- the 18 most common production questions bypass LLM generation entirely, returning tested SQL in milliseconds.

**SQL safety validation** -- every query passes through a 5-stage validation pipeline: statement type check, injection pattern detection (tautologies, UNION, comments, stacked queries), table existence, column existence, and automatic row limit enforcement. See `specs/security.md` for the full threat model.

**Structured state flow** -- the full state `{question, domain, sql, results, explanation, error}` flows through each node, making the pipeline observable and debuggable.

See `modules/agent_graph.py` for the implementation.

---

## Error Monitoring

OpsMind supports optional error monitoring via [Sentry](https://sentry.io). Set the `SENTRY_DSN` environment variable to enable it. If not set, monitoring is completely disabled (no-op).

```bash
export SENTRY_DSN="https://examplePublicKey@o0.ingest.sentry.io/0"
export ENVIRONMENT="production"   # optional, defaults to "development"
```

Errors in the SQL agent pipeline are automatically reported when Sentry is enabled.

---

## Limitations

| Area | Reality |
|---|---|
| LLM accuracy | Measured per release — see `tests/eval/golden_set.yaml` (library path + LLM path). Run `make eval` locally to get current numbers for your model + schema. |
| Speed | 10-25 sec per query on 16GB RAM. LLM is the bottleneck. |
| Auth | Password via Streamlit secrets. No multi-user roles. |
| Safety | Read-only. SELECT only — INSERT/UPDATE/DELETE blocked. |

### Evaluation

The accuracy claim is backed by a golden set (`tests/eval/golden_set.yaml`) with
two paths:

- **Library path** — 14 questions that should hit pre-built SQL patterns. Runs
  with no LLM, catches regressions when someone edits `query_library.py`.
- **LLM path** — 6 questions the library can't match, forcing real NL-to-SQL
  generation. Generated SQL is executed against the demo database and compared
  to a reference SQL's result set.

```bash
make eval-library   # fast, CI-safe, no Ollama needed
make eval-llm       # requires Ollama + gemma3:12b
make eval           # both
```

Failure modes are catalogued in `tests/eval/failure_modes.md` — the taxonomy
grows as real failures arrive (pattern from Martin Seeler's "AI Evals Done
Right", PyCon DE 2026).

---

## Contributing

OpsMind is solo-maintained with an open door for contributors.

- Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for how to set up, test, and
  open a PR.
- Read [`GOVERNANCE.md`](GOVERNANCE.md) before large changes — roles,
  response-time commitments, and the four hard scope lines live there.
- Security issues go through [`SECURITY.md`](SECURITY.md) (private
  advisory), not public issues.
- Behavioural expectations are in [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- Third-party licence attributions are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md); the project's own copyright notice is in [`NOTICE`](NOTICE).

Good first issues are labelled `good first issue`. First-PR-wins on any
issue: claim by commenting, ship within 7 days, or the next contributor
may take it.

**If OpsMind is useful to you, a GitHub star is the easiest way to help
— it makes the project more discoverable for people with the same
problem.**

---

**[Docs](https://pawansingh3889.github.io/OpsMind/)** &#183; **[Report Bug](https://github.com/Pawansingh3889/OpsMind/issues)** &#183; **[Request Feature](https://github.com/Pawansingh3889/OpsMind/issues)** &#183; **[Security](SECURITY.md)**
