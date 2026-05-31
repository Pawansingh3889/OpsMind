# Migrating OpsMind to a large company SQL database

What changes when the source isn't a tidy demo database but a live,
high-volume company ERP — millions of rows, dozens of schemas, real
factory load.

This guide is the **scale + data-flow** companion to two existing docs:

- [`connect-to-production-database.md`](connect-to-production-database.md)
  — the DBA-facing read-only connection setup (grants, connection
  string, the three safety layers). Do that **first**.
- [`multi-plant-deployment.md`](multi-plant-deployment.md) — extending
  the schema map to a second site.

This doc assumes the connection is already proven read-only and
focuses on the question that only shows up at scale: *how do you query
a huge table without dragging it across the wire or loading factory
production?*

> **Confidentiality note.** Everything here uses placeholder names
> (`fact_production`, `dim_product`, `HOST`, `YourDB`). Never commit a
> real schema, table name, connection string, or row of company data
> to this repo — it is public. Real schema mapping lives in your
> private `schema.yaml`, which is git-ignored for production
> deployments.

---

## The one principle that governs everything: push the work down

The single most important rule when the source table is large:

> **Aggregate in the database. Move only the small result.**

A 5-million-row `fact_production` table must never become a
5-million-row dataframe. The database engine (SQL Server, PostgreSQL)
is built to aggregate at that scale; an in-process dataframe is not.

```
WRONG — drags the whole table over the wire, then reduces in RAM:
   df = pd.read_sql("SELECT * FROM fact_production", engine)   # 5M rows
   result = df.groupby("line").size()                          # ~20 rows out

RIGHT — the engine aggregates; OpsMind receives ~20 rows:
   SELECT line, COUNT(*) FROM fact_production GROUP BY line
```

OpsMind's LLM already generates aggregate SQL (`GROUP BY`, `COUNT`,
`SUM`, `WHERE` date filters) rather than `SELECT *`, so the right
pattern is the default. The migration job is to make sure it *stays*
that way against a real schema, and to cap the failure cases. Three
guardrails do that:

| Guardrail | Where | What it caps |
|---|---|---|
| Row cap | `OPSMIND_SQL_MAX_ROWS` (default 1000) | A result set that slips through un-aggregated is truncated, not loaded whole |
| Read-only validator | `modules/sql_validator.py` (shipped) | No write ever reaches the DB |
| Schema scoping | `schema.yaml` | The LLM only sees the tables for the detected domain, so it can't join the whole warehouse |

At a small result size (tens to low-thousands of rows), the
pandas-vs-Polars question is irrelevant — the difference is
microseconds. It only re-enters if you do heavy *local* analytics on a
large intermediate set (see § Heavy local analytics).

---

## Step 1 — Prove the read-only connection (prerequisite)

Do not start here. Complete
[`connect-to-production-database.md`](connect-to-production-database.md)
end to end first: read-only DB user, `ApplicationIntent=ReadOnly` (SQL
Server) or replica DSN (PostgreSQL), and the three verification
commands. Then set:

```
OPSMIND_DB=mssql+pyodbc://opsmind_ro:<pw>@HOST:1433/YourDB?driver=ODBC+Driver+17+for+SQL+Server&ApplicationIntent=ReadOnly
```

**Point this at a read replica / Always-On secondary, never the
primary.** Analytical queries on the primary contend with OCM
scan-back and SI scale writes. The replica shares no lock manager with
the primary, so OpsMind cannot add latency to the line. This is the
whole reason the connection model exists.

---

## Step 2 — Map the company schema (the real work)

The demo ships a 19-table schema across six domains. A company ERP has
hundreds of tables. You do **not** map them all — you map the slice
operators actually ask about.

### 2.1 Interview, don't guess

List the 30–80 questions operators and QA actually ask. Group them by
domain (production, waste, orders, compliance, staff, supplier).
Each question points at 1–3 tables. That set — usually 15–40 tables —
is your map. The other hundreds stay invisible to the LLM, which is
both safer and faster.

### 2.2 Write the mapping in `schema.yaml`

`schema.yaml` tells OpsMind which physical tables/columns back each
domain. For a company DB you typically map a *view* per concept rather
than the raw ERP table, so ERP refactors don't break OpsMind:

```yaml
# schema.yaml — PLACEHOLDER names; real one is git-ignored in prod
domains:
  production:
    tables:
      production:
        source: analytics.vw_production_runs   # a read-only view you own
        columns:
          run_id:     {type: int,    desc: "production run identifier"}
          line:       {type: text,   desc: "packing line name"}
          product_id: {type: int,    desc: "FK to dim_product"}
          good_kg:    {type: float,  desc: "good output in kg"}
          waste_kg:   {type: float,  desc: "waste in kg"}
          run_date:   {type: date,   desc: "date of the run"}
```

Why views, not raw tables:

- **Stable contract** — the ERP team can refactor `fact_production`
  underneath; you only re-point the view.
- **Column whitelist** — the view exposes only the columns OpsMind
  needs. Retailer-confidential or PII columns never enter the LLM's
  schema context.
- **Pre-filtering** — the view can scope to the relevant plant /
  recent window, shrinking what any query can touch.

Set `SCHEMA_MODE=mapped` (not `auto`) for a company DB so OpsMind uses
your explicit map rather than introspecting every table it can see.

### 2.3 Index for the query shapes OpsMind generates

OpsMind's questions translate to `WHERE date >= ...`, `GROUP BY
line/product`, and joins on the FK columns. Ask the DBA to confirm the
replica has indexes on:

- the date column used for "this week / last 30 days" filters
- the grouping columns (line, product_id, customer_id)
- the join keys between fact and dimension tables

Without these, a `GROUP BY` over millions of rows does a full scan.
With them, it's an index range. This is the difference between a
2-second answer and a 2-minute one — entirely on the DB side, nothing
OpsMind controls.

---

## Step 3 — Decide the read path: live replica vs nightly cache

Two supported patterns. Pick by how much analytical load you want on
the replica during the working day.

### Pattern A — Live replica reads (simplest)

Every operator question runs against the read replica in real time.

- **Pro:** answers reflect the latest replicated data (lag usually <1s).
- **Pro:** zero extra infrastructure.
- **Con:** every question is a query on the replica. Fine for tens of
  questions an hour with good indexes; reconsider at high concurrency.

This is the default. Use it unless you have a specific reason not to.

### Pattern B — Nightly snapshot to a local cache (strongest isolation)

A DBA-owned overnight job exports the whitelisted views to a local
columnar cache (DuckDB / Parquet) inside OpsMind's container. During
the working day, OpsMind queries the cache — the source DB sees **zero**
OpsMind traffic.

```
03:00  DBA job:  views  ──►  Parquet / DuckDB  ──►  /app/data/cache.duckdb
day:   operator question  ──►  OpsMind  ──►  DuckDB (local, in-container)
```

- **Pro:** source DB completely insulated during production hours.
- **Pro:** DuckDB is columnar — aggregations over tens of millions of
  cached rows run locally in well under a second.
- **Con:** data is as fresh as the last snapshot (yesterday's close).
  Right for audit / trend questions, wrong for "what's happening on
  the line right now."
- **Status:** `[scoped for v0.4]` — the DuckDB cache layer is designed
  (see [`architecture.md`](architecture.md) § 7) but not yet shipped.
  Until it lands, use Pattern A.

A common hybrid: real-time domains (current orders, live production) on
Pattern A; heavy historical domains (compliance audit, 12-month trend)
on Pattern B.

---

## Step 4 — Heavy local analytics (where Polars/DuckDB earn their place)

Most OpsMind questions reduce to a small result and need no local
dataframe muscle. The exception: analysis the SQL engine can't express
cleanly on a *large intermediate* set — multi-step window math,
feature engineering for a forecast, cross-domain reshaping.

Decision rule, measured on this project's own data:

| Local result size | Tool | Why |
|---|---|---|
| < ~500k rows | pandas (already a dep) | Difference vs Polars is sub-second; not worth the churn |
| ~1M–10M rows | Polars or DuckDB | 3–5× faster and lower memory; the gap grows with volume |
| > 10M rows | DuckDB (out-of-core) | Streams from disk; doesn't need the set to fit in RAM |

If you reach for Polars/DuckDB, the read-only safety model is
unchanged — they operate on data already pulled through the read-only
connection or the cache. They never open a write path.

Keep the aggregation in SQL whenever SQL can do it. Only pull a large
intermediate set local when the computation genuinely can't be
expressed server-side.

---

## Step 5 — Verify before go-live

Run these against the company replica, in order. Each maps to a risk.

```bash
# 1. Connection + read-only confirmed (Layer 1+2)
#    see connect-to-production-database.md for the exact write-attempt test

# 2. Schema map resolves — every mapped table/view is reachable
python -c "from modules.schema_registry import get_all_table_names; print(get_all_table_names())"

# 3. A real aggregate question returns a SMALL result (push-down working)
#    Ask OpsMind: "yield by line last week" — confirm the generated SQL
#    has GROUP BY and returns tens of rows, not a full-table pull.
#    The query log at /app/logs/queries.jsonl shows the generated SQL.

# 4. Row cap holds — ask a deliberately broad question and confirm the
#    result is capped at OPSMIND_SQL_MAX_ROWS, not unbounded.

# 5. Eval harness against the new schema (adapt tests/eval/golden_set.yaml
#    to company-vocabulary questions first)
make eval-library          # deterministic, no LLM
make eval-llm              # full, needs Ollama
```

The eval step is the one that turns "we connected it" into "we
validated it" — the same discipline the AKT 6 validation report is
built on. Don't skip it.

---

## IT / DBA checklist for the migration

Hand this to whoever owns the company database.

- [ ] Read-only DB user created with explicit `DENY` on writes (Layer 1)
- [ ] Connection routed to a **read replica / Always-On secondary**, not the primary
- [ ] `ApplicationIntent=ReadOnly` (SQL Server) or replica DSN (PostgreSQL) in the connection string
- [ ] Read-only **views** created for the mapped concepts (not raw ERP tables)
- [ ] Views expose only non-confidential, non-PII columns OpsMind needs
- [ ] Indexes confirmed on date-filter, group-by, and join columns
- [ ] (If Pattern B) nightly export job scheduled, DBA-owned, off-hours
- [ ] Firewall allows OpsMind container → replica host on the DB port only
- [ ] `schema.yaml` for the company DB kept private / git-ignored
- [ ] Eval harness adapted to company vocabulary and run green before go-live

---

## What stays the same

The migration changes the *source*, not the *safety model*. Unchanged:

- The four read-only enforcement layers ([`architecture.md`](architecture.md) § 1)
- `sql-guard` static analysis on every generated query
- The on-prem Ollama LLM with no internet egress
- The audit log of every question + generated SQL
- The temperature-out-of-NL-surface decision (real-time monitoring
  stays in SCADA / the compliance dashboard)

A bigger, faster, real database behind the same boundaries.

---

## Related documents

- [`connect-to-production-database.md`](connect-to-production-database.md) — read-only connection setup (do first)
- [`multi-plant-deployment.md`](multi-plant-deployment.md) — second-plant onboarding
- [`architecture.md`](architecture.md) — full system + safety model, DuckDB cache design
- `tests/eval/AKT6-extension.md` — how the eval harness scales to validate a new deployment
