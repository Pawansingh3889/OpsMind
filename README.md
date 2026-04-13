<div align="center">

# OpsMind

**AI query tool for manufacturing — runs on your machine, not the cloud**

[![Docs](https://img.shields.io/badge/Docs-Website-0f172a?style=flat-square&logo=googlechrome&logoColor=white)](https://pawansingh3889.github.io/OpsMind/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![Tests](https://img.shields.io/badge/Tests-36_passed-22c55e?style=flat-square&logo=pytest&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)]()

</div>

## Links
- [GitHub](https://github.com/Pawansingh3889/OpsMind)
- [Documentation](https://pawansingh3889.github.io/OpsMind/)
- [Profile](https://github.com/Pawansingh3889)
- [PyPI (sql-sop)](https://pypi.org/project/sql-sop/)
- [Download Stats](https://pypistats.org/packages/sql-sop)

---

Manufacturing teams query data through Excel exports and IT requests. OpsMind lets any operator ask the database in English — offline, on-prem, no API keys.

Includes production ERP integration with 19 tables covering batch-centric runs, waterfall yield tracking (RSPCA/GG/Almaria tiers), batch lineage for OCM scan-back traceability, and shelf life management.

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

---

## Run the tests

```
$ make test

tests/test_core.py::TestConfig::test_config_loads               PASSED
tests/test_core.py::TestSQLDialect::test_days_ago_sqlite         PASSED
tests/test_core.py::TestSchemaRegistry::test_detect_domain        PASSED
tests/test_core.py::TestDatabase::test_query_returns_dataframe    PASSED
tests/test_core.py::TestCompliance::test_trace_batch              PASSED
tests/test_core.py::TestAlerts::test_check_all_alerts             PASSED
tests/test_core.py::TestWastePredictor::test_predict_waste        PASSED
tests/test_core.py::TestSQLAgentSafety::test_blocks_insert        PASSED
tests/test_core.py::TestDocSearch::test_search_returns_list        PASSED
... 27 more tests

36 passed, 0 failed
```

Covers: config, SQL dialect abstraction, schema registry, database queries, compliance checks, alert detection, waste prediction, SQL injection prevention, document search.

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
| LLM | Ollama (Gemma 3 12B) | English → SQL, result explanation |
| Database | SQLAlchemy | SQLite (demo) + SQL Server (production) |
| Vector Search | ChromaDB or PostgreSQL+pgvector + sentence-transformers | PDF search (RAG) |
| UI | Streamlit (7 tabs) | Dashboard, chat, charts |
| Charts | Plotly | Production and waste visualisation |
| Config | YAML | Schema registry — 7 domains, up to 147 tables |
| Tests | pytest | 36 unit + integration tests |

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
```

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

**SQL safety validation** -- every query passes through a two-layer check (allowlist + blocklist) before execution. INSERT, UPDATE, DELETE, DROP, and other write operations are always blocked.

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
| LLM accuracy | ~60% on novel complex queries. Pre-built library handles top 10 questions reliably. |
| Speed | 10-25 sec per query on 16GB RAM. LLM is the bottleneck. |
| Auth | Password via Streamlit secrets. No multi-user roles. |
| Safety | Read-only. SELECT only — INSERT/UPDATE/DELETE blocked. |

---

**[Docs](https://pawansingh3889.github.io/OpsMind/)** &#183; **[Report Bug](https://github.com/Pawansingh3889/OpsMind/issues)** &#183; **[Request Feature](https://github.com/Pawansingh3889/OpsMind/issues)**
