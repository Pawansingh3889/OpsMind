# OpsMind multi-plant deployment guide

A practical runbook for taking OpsMind from a single-plant deployment to a
second (or third) site. The architecture is designed for this — schema
registry, env-var database wiring, swappable vector store. This guide walks
through what to change, what to leave alone, and what to validate before
going live.

> **Context:** OpsMind is currently deployed at one Hull fish-processing
> operation. Multi-plant validation is the scope of an in-flight Innovate UK
> AKT 6 application (deadline 15 July 2026). This document captures the
> deployment pattern the AKT 6 project will validate at scale.

---

## What stays the same across plants

The whole point of the schema registry pattern is that **the codebase does
not fork per plant**. Across every deployment you keep:

| Layer | Stays the same |
|---|---|
| Architecture | LangGraph 6-node agent (see `modules/agent_graph.py`) |
| Domain detection | Keyword router in `modules/schema_registry.py` |
| Safety model | Read-only SQL enforcement (`modules/sql_agent.py`); only `SELECT`/`WITH` allowed; `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER`/`TRUNCATE`/`EXEC`/`xp_`/`sp_` blocked |
| LLM | Gemma 3 12B via Ollama (or other Ollama-served model) |
| Vector store | ChromaDB by default, pgvector via `OPSMIND_VECTOR_DB=pgvector` |
| Query library mechanism | Regex-based fast path in `modules/query_library.py` |
| Eval harness | `tests/eval/` — golden set, library + LLM judges, failure taxonomy |
| Reports & charts | `app.py` Streamlit UI |

**No code edits, no forks, no patched releases.** Plant-specific behaviour
lives in configuration files, not the source tree.

---

## What changes per plant

Everything plant-specific is configuration:

| File / env var | Purpose | Required? |
|---|---|---|
| `schema.yaml` | Maps your tables and columns into OpsMind's seven business domains | Required |
| `OPSMIND_DB` | SQLAlchemy URL for the plant's ERP. Demo default is `sqlite:///data/demo.db` | Required |
| `OPSMIND_VECTOR_DB` | `chromadb` (default) or `pgvector`. Plant-local choice | Optional |
| `OPSMIND_CHROMA_DIR` | Where ChromaDB persists. Defaults to `data/chroma_store` | Optional |
| `OPSMIND_VECTOR_PG_URL` | Connection URL if using pgvector | Required only with pgvector |
| `OLLAMA_BASE_URL` | If Ollama runs on a different host on the plant network | Optional |
| `OLLAMA_MODEL` | Override the default `gemma3:12b` | Optional |
| `modules/query_library.py` | Add plant-specific regex shortcuts (high-frequency operator questions) | Optional, recommended |
| `Modelfile` | Customise the model's system prompt (plant terminology, retailer specs) | Optional |

The minimum viable second-plant deployment touches **two files**:
`schema.yaml` and an environment variable for `OPSMIND_DB`.

---

## Step-by-step: onboarding plant 2

Estimated time: **half a day for a competent operator**, including
hardware provisioning and validation.

### 0. Prerequisites

- A machine on the plant network with a GPU capable of running Gemma 3 12B
  via Ollama (~16 GB VRAM minimum, 24 GB comfortable). CPU-only works but is
  slow.
- A **read-only** SQL user on the plant's ERP. Read-only is enforced in the
  app layer too, but defence in depth at the database user level is the
  pattern for BRC-audited environments.
- Network connectivity from the OpsMind host to the ERP.
- Python 3.11+ and Ollama installed (`https://ollama.com/download`).

### 1. Provision and install

```bash
git clone https://github.com/Pawansingh3889/OpsMind.git
cd OpsMind
make setup        # creates venv, installs requirements
ollama pull gemma3:12b
```

### 2. Configure the database connection

Set `OPSMIND_DB` to your plant's ERP. SQLAlchemy URLs look like:

```bash
# SQL Server (Integreater, common in UK food manufacturing)
export OPSMIND_DB="mssql+pyodbc://opsmind_ro:password@PLANT2-SQL/ProductionDB?driver=ODBC+Driver+17+for+SQL+Server"

# SQL Server with Windows Authentication
export OPSMIND_DB="mssql+pyodbc://PLANT2-SQL/ProductionDB?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

# PostgreSQL
export OPSMIND_DB="postgresql://opsmind_ro:password@plant2-db/production"
```

Verify the connection responds and is read-only:

```bash
python -c "from modules.database import query; print(query('SELECT 1 AS ok'))"
```

If a `DELETE`/`UPDATE`/`INSERT` from the OpsMind host succeeds, the database
user has more privilege than it should. Fix the user grant before continuing.

### 3. Map the schema

Open `schema.yaml`. The file ships with the demo SQLite mapping and an
example SQL Server (SI Integreater) mapping commented out. For plant 2:

1. Identify the equivalent tables in the plant's ERP for each business
   domain (`traceability`, `production`, `orders`, `temperature`, `staff`,
   `stock`, `compliance`).
2. For each domain, list the tables OpsMind should consider, with their
   relevant columns.
3. Use **only columns the LLM needs to see** — fewer columns means tighter
   prompts and better SQL.

A real-world example (Cranswick meat processing rather than fish):

```yaml
traceability:
  description: Batch traceability from intake to dispatch
  tables:
    Carcass: CarcassID, BatchNo, Cut, AbattoirCode, ProcessingDate, InputKg, OutputKg, YieldPct, LineNo
    RawIntake: IntakeID, AbattoirCode, BatchNo, SupplierCode, QuantityKg, IntakeDate, UseByDate, TempOnArrival
    Products: ProductCode, ProductName, Cut, Category, CostPerKg, SellPricePerKg, Allergens
    SalesOrders: OrderID, CustomerCode, ProductCode, QuantityKg, OrderDate, DeliveryDate, Status, PricePerKg
    Customers: CustomerCode, CustomerName

compliance:
  description: Allergens, temperature, batch codes, non-conformance
  tables:
    Products: ProductCode, ProductName, Allergens, HazardClass
    TempLogs: LogID, Location, ReadingTime, TempC, TargetMin, TargetMax, InRange
    Carcass: CarcassID, BatchNo, Cut, ProcessingDate
    NonConformance: NCID, NCDate, BatchNo, ProductCode, NCType, Severity, Description, CorrectiveAction, Status
```

Two patterns to lean on:

- **Reuse the demo schema as a template.** Domain names are stable
  (`traceability`, `production`, ...). Change tables and columns, not domain
  keys.
- **Look at the commented `SI Integreater` block** in `schema.yaml` — it's
  the closest real-world example shipped with the repo and was used in the
  Hull deployment.

### 4. Validate the configuration

Run the smoke test from the repo:

```bash
# Read-only sanity check
python -m pytest tests/unit -v

# Smoke test against the new schema (no LLM required)
OPSMIND_EVAL_SKIP_LLM=1 pytest tests/eval -v -m eval_library

# Full eval (requires Ollama)
pytest tests/eval -v
```

The library-path eval should pass on day one — it doesn't touch the LLM and
exercises the regex shortcuts against your schema. The LLM-path eval is the
real measure of NL-to-SQL accuracy on your plant's data; expect some failures
on the first run, then use the failure-mode taxonomy in `failure_modes.md`
to tune.

### 5. Add plant-specific query library entries (recommended)

Operators tend to ask the same five questions a hundred times a day. Each
of those should be a regex pattern in `modules/query_library.py`:

```python
{
    "patterns": [
        r"yield.*today",
        r"today.*yield",
        r"how (much|many).*yield.*today",
    ],
    "domain": "production",
    "sql": """
        SELECT pp.Cut, AVG(c.YieldPct) AS avg_yield_pct
        FROM Carcass c
        JOIN Products pp ON c.ProductCode = pp.ProductCode
        WHERE c.ProcessingDate = {today}
        GROUP BY pp.Cut
        ORDER BY avg_yield_pct DESC
    """,
    "description": "Average yield per cut, today",
},
```

Each pattern bypasses the LLM and returns deterministic SQL. For a busy
plant, the library is the difference between an OpsMind that *seems* fast
and one that *is* fast.

### 6. Deploy and monitor

Run the Streamlit app:

```bash
streamlit run app.py
```

For production, run behind a systemd unit (or Windows service equivalent)
with logging redirected to a rotating file. Hook up the existing
`modules/monitoring.py` Sentry integration if the plant network allows
outbound HTTPS to Sentry (some BRC-audited environments do not — disable
Sentry by leaving `SENTRY_DSN` unset).

---

## Worked example: fish processing → meat processing

The Hull plant runs fish processing; the validation plant in the AKT 6 scope
is meat processing. The diff between the two deployments is small enough to
fit in this document.

### `schema.yaml` differences

| Concept | Fish deployment | Meat deployment |
|---|---|---|
| Species column | `Species` (cod, salmon, ...) | `Cut` (sirloin, mince, ...) |
| Origin metadata | `catch_area`, `vessel_name`, `landing_date` | `abattoir_code`, `processing_date` |
| Compliance focus | RSPCA fish welfare, MSC sustainability | Red Tractor, FSA approval |
| Temperature targets | `+2°C / +3°C superchill` | `0-4°C chill, -18°C frozen` |
| Lineage table | `prod_traceability` (fish-specific) | `Carcass` (meat-specific) |

### Query library overlap

Of the 18 fish-deployment patterns, roughly 12 are domain-agnostic and work
unchanged. Examples that transfer cleanly:

- *"top X by yield this week"* — same shape, swap table names
- *"open non-conformances"* — identical pattern
- *"stock by expiry date"* — identical pattern
- *"production this shift"* — identical pattern

Examples that need new patterns:

- *"yield by species"* (fish-only)
- *"vessel landings this week"* (fish-only)
- *"yield by cut"* (meat-only)
- *"abattoir intake this week"* (meat-only)

### LLM behaviour differences

Gemma 3 12B handles the schema swap without prompt engineering — the schema
registry filters tables before the LLM sees the question, so the LLM never
encounters fish-specific terminology when working a meat query. The
`Modelfile` may benefit from a small terminology block if operator questions
use plant-local jargon.

---

## Validation checklist before going live

Tick before declaring plant 2 deployed:

- [ ] `schema.yaml` maps every business domain operators will query
- [ ] `OPSMIND_DB` connects with a verified **read-only** user
- [ ] Library-path eval passes (`OPSMIND_EVAL_SKIP_LLM=1 pytest tests/eval`)
- [ ] LLM-path eval baseline recorded (note the accuracy percentage in the
      deployment log for AKT 6 reporting)
- [ ] At least 5 plant-specific query library entries added for
      high-frequency operator questions
- [ ] Streamlit app accessible from operator terminals
- [ ] Logging configured; failure modes captured in `failure_modes.md`
- [ ] Read-only enforcement verified end-to-end:
      `INSERT`/`UPDATE`/`DELETE` attempts blocked at both the app layer
      (`modules/sql_agent.py`) and the database user grant level
- [ ] Operator training session scheduled — see the operator guide below

---

## Operator training: what to teach in 30 minutes

Five things to cover with each operator group on go-live:

1. **Questions that work well.** "What was the yield for X yesterday?" /
   "Which line had the most rejects this week?" / "Show me open
   non-conformances." Domain-scoped, specific, time-bounded.
2. **Questions to avoid.** Free-form analytical questions ("which product
   line should we discontinue?") — OpsMind generates SQL, not strategy.
3. **How to read the agent trace.** The Streamlit UI shows which domain was
   detected, which library pattern matched (if any), and the generated SQL.
   Operators learn to spot when OpsMind is confused.
4. **Escalation path.** When the answer looks wrong, who to flag, and where
   the trace + question goes for follow-up tuning (add to
   `failure_modes.md`, escalate to OpsMind maintainer).
5. **Confidentiality model.** Reinforce: data does not leave the plant
   network. No cloud, no API keys, no telemetry. Important for retailer
   audit conversations.

---

## Known limitations (be honest)

- **Schema synonyms not yet supported.** If your operators say "rejects"
  but the column is `defect_count`, you need a library pattern to bridge.
- **LLM accuracy varies by domain complexity.** Simple aggregations are
  reliable; multi-join historical analytics are less so. The eval harness
  measures this per deployment.
- **First-query cold start.** Ollama takes ~30 seconds to warm up. The first
  operator query of the day is slow; subsequent queries are sub-second once
  the model is loaded.
- **pgvector backend is less battle-tested than ChromaDB.** Use ChromaDB by
  default unless your plant policy prefers Postgres for everything.
- **No multi-tenant isolation yet.** One OpsMind instance per plant. Cross-
  plant aggregation is out of scope for the current architecture and is on
  the v0.4 roadmap.

---

## Acknowledgements

The schema registry pattern was first deployed against an SI Integreater
ERP at a Hull fish-processing site (Copernus). This guide draws on the
deployment notes from that single-plant rollout, generalised for the AKT 6
multi-plant validation scope.
