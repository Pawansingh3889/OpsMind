# OpsMind — System Architecture & Production-Safety Model

> Audience: corporate IT, network security, infrastructure managers, and BRC
> auditors evaluating whether OpsMind can be deployed alongside production-
> critical factory floor systems (OCM scan-back, SI weighing scales,
> packing-line PLCs, ERP integration layer).
>
> Intent: document the controls that make the platform safe to run against
> production data and demonstrate, control by control, that OpsMind cannot
> alter, lock, or starve any system it touches.
>
> Status legend used throughout:
> `[shipped]` — in the v0.3.1 codebase today.
> `[scoped]` — design is fixed, code lands in v0.4.x.
> `[planned]` — on the roadmap, no code yet.

---

## 1. Executive summary

OpsMind is a read-only natural-language query layer over factory data. It
does not write to source systems, does not call external APIs at query
time, and does not consume measurable compute on the production database.

Safety is enforced by **four independent layers**. A single failure in
any one layer does not introduce write capability; an attacker or
operator error would have to defeat all four simultaneously.

| Layer | Control | What it prevents |
|---|---|---|
| L1 — Database grants | Dedicated read-only DB user; explicit `DENY INSERT/UPDATE/DELETE/EXEC/ALTER` | Any write reaching the source database |
| L2 — Connection string | `ApplicationIntent=ReadOnly` (SQL Server) / read replica endpoint (PostgreSQL) | Any write routed to a primary node |
| L3 — `sql-guard` static analysis | Parses every generated SQL statement before execution; rejects DDL, DML, multi-statement, comment-injection | Any write semantics in generated SQL |
| L4 — App-layer validator | `modules/sql_validator.py` — second-pass parse with row-cap injection, identifier allow-list | Defence-in-depth for L3 false-negatives; bounds result-set size |

The remainder of this document walks each architectural boundary in detail
so a network/security reviewer can verify the controls themselves rather
than trust the summary table.

---

## 2. Component inventory

| Component | Role | Status | Network exposure |
|---|---|---|---|
| Streamlit UI | Operator query surface | `[shipped]` | TCP 8501, internal only |
| LangGraph agent (6 nodes) | Query routing, SQL generation, validation, execution | `[shipped]` | Container-local |
| Ollama runtime | On-prem LLM serving (gemma3:12b) | `[shipped]` | TCP 11434, container network only |
| ChromaDB / pgvector | Domain documentation embeddings (RAG) | `[shipped]` | Container-local / DB-side |
| `sql-guard` (sql-sop pkg) | Pre-execution SQL static analysis | `[shipped]` | None (in-process library) |
| `modules/sql_validator.py` | App-layer SQL parse + row-cap injection | `[shipped]` | None |
| pyodbc / SQLAlchemy | Read-only ODBC client to source DB | `[shipped]` | Egress to source DB only |
| DuckDB analytical cache | Local columnar cache of snapshotted reads | `[scoped]` v0.4 | Container-local file |
| dbt local models | Reproducible transforms over the DuckDB cache | `[scoped]` v0.4 | Container-local |
| MCP server (database / docs) | Optional tool surface for LLM clients | `[shipped]`, disabled by default | TCP 9000 / 9001, off unless `MCP_ENABLED=true` |
| Push alerts (`modules/alerts.py`) | Threshold-driven notifications | `[shipped]` | Outbound webhook only |

---

## 3. High-level data flow

```
                       ┌─────────────────────────────────────────────────┐
                       │ Windows host (factory IT-managed laptop / VM)   │
                       │                                                 │
   Operator browser    │   ┌─────────────────────────────────────────┐   │
   (corp LAN)  ──────▶ │   │ Docker Engine / WSL2 (Linux VM)         │   │
                       │   │                                         │   │
                       │   │  ┌──────────────────────────────────┐   │   │
                       │   │  │ opsmind-app container            │   │   │
                       │   │  │  • Streamlit :8501               │   │   │
                       │   │  │  • LangGraph 6-node agent        │   │   │
                       │   │  │  • sql-guard + sql_validator     │   │   │
                       │   │  │  • DuckDB cache  [scoped]        │   │   │
                       │   │  └────────┬─────────────────┬───────┘   │   │
                       │   │           │                 │           │   │
                       │   │           ▼                 ▼           │   │
                       │   │  ┌─────────────────┐  ┌──────────────┐  │   │
                       │   │  │ opsmind-ollama  │  │ pyodbc /     │  │   │
                       │   │  │  :11434         │  │ psycopg2     │  │   │
                       │   │  │  gemma3:12b     │  │ ODBC driver  │  │   │
                       │   │  └─────────────────┘  └──────┬───────┘  │   │
                       │   │  (no internet egress)        │          │   │
                       │   └──────────────────────────────┼──────────┘   │
                       └──────────────────────────────────┼──────────────┘
                                                          │ TCP 1433 / 5432
                                                          │ Windows Auth (Kerberos)
                                                          ▼
                                              ┌──────────────────────┐
                                              │ Read-only replica /  │
                                              │ Always-On secondary  │
                                              │ (SQL Server / PG)    │
                                              └──────────┬───────────┘
                                                         │ async replication
                                                         ▼
                                              ┌──────────────────────┐
                                              │ Production primary   │  ◀── OCM, SI scales, ERP
                                              │ (OPSMIND NEVER       │
                                              │  CONNECTS HERE)      │
                                              └──────────────────────┘
```

Read-path summary: operator → Streamlit → LangGraph → (Ollama for SQL
generation) → `sql-guard` → `sql_validator` → ODBC → **replica**. The
production primary is unreachable from the OpsMind network path.

---

## 4. Section 1 — Compute and OS boundary (Docker / VM isolation)

### 4.1 Why a Linux container on a Windows host

The deployment target on most factory desks is a Windows laptop joined
to the corporate Active Directory domain. OpsMind is packaged as a
Linux-only Docker image (`python:3.11-slim`) and runs under either
Hyper-V (Docker Desktop) or WSL2. This achieves three things relevant
to IT:

1. **Process isolation from the Windows host.** The container's process
   table is a separate kernel namespace inside the WSL2/Hyper-V Linux
   VM. The Streamlit process cannot enumerate, signal, or attach to
   Windows host processes. ERP fat-client services, SI Integreater
   agents, or scanner middleware running on the same laptop are
   invisible to OpsMind.
2. **Filesystem isolation.** Only two host paths are bind-mounted
   (`./data` for the SQLite demo + Chroma store, `./logs` for audit
   logs). No mount touches `C:\Program Files`, the user profile, ERP
   data directories, or network shares. The container's root filesystem
   is the image — no host write access.
3. **Independent package set.** Python 3.11, ODBC drivers, and all
   transitive dependencies live inside the image. Upgrades to the
   Windows host's Python or ODBC stack do not affect OpsMind, and
   OpsMind cannot pollute the host's package state.

### 4.2 Hard isolation controls in `docker-compose.yml`

The following lines from `docker-compose.yml` are the enforceable
contract reviewers should verify:

| Setting | Effect |
|---|---|
| `security_opt: no-new-privileges:true` | Container processes cannot gain capabilities via setuid binaries — privilege escalation paths inside the container are closed. |
| `USER opsmind` (UID 1000) in the Dockerfile | The Streamlit process runs as a non-root user with no sudo capability. |
| `networks: opsmind-net` (driver: bridge) | The app and Ollama share a private bridge network. The Ollama port is **not** published to the host except for development; in factory deployment the `ports:` block on `ollama` is removed and Ollama is reachable only via service DNS inside the bridge. |
| `ports: ["8501:8501"]` (Streamlit only) | One single port is exposed to the host. Bind it to `127.0.0.1:8501` in factory deployment for laptop-local access, or to the corp LAN address for shared kiosk deployment. |
| `restart: unless-stopped` | Service self-recovers but does not restart on operator-initiated stop, supporting maintenance windows. |
| `HEALTHCHECK` (Streamlit `/_stcore/health` and `ollama list`) | Container orchestration can detect a wedged process within 30s and recycle it without operator action. |

### 4.3 Resource caps (compute starvation prevention) `[scoped]`

The shipped compose file does not yet set CPU/RAM caps. The v0.4
deployment manifest will add:

```yaml
services:
  opsmind:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4G
        reservations:
          memory: 1G
  ollama:
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 16G          # gemma3:12b needs ~10GB resident
          # GPU via device_requests if NVIDIA runtime present
```

Effect on the host: OpsMind is capped at ~6 CPU cores and ~20 GB RAM
combined. On a typical 16-core / 32 GB factory laptop, this leaves the
host with at least 10 cores and 12 GB free for ERP clients, scanner
drivers, antivirus, and Windows itself. The container scheduler cannot
starve host processes — cgroup v2 enforces these caps at the kernel
level inside the WSL2 VM.

### 4.4 What this section does NOT claim

- It does not claim the Windows host itself is hardened — that's IT's
  responsibility (patching, EDR, Windows Defender, BitLocker).
- It does not claim the bridge network is air-gapped — outbound ODBC
  to the source DB is required and explicit (see Section 5).
- It does not claim the LLM cannot be tricked into emitting malicious
  SQL — Section 6 covers exactly how that case is blocked.

---

## 5. Section 2 — Database connectivity gateway (zero production disturbance)

### 5.1 Three independent controls on the connection itself

OpsMind never touches the production primary. The connection path is:

```
opsmind-app container
   │
   │  pyodbc / psycopg2  ──┐
   │                       │  Control 1: dedicated read-only DB user
   │                       │  Control 2: ApplicationIntent=ReadOnly (SQL Server) / replica DSN (PG)
   │                       │  Control 3: Windows Authentication (no shared password)
   │                       ▼
   └────────▶  Read-only replica / Always-On secondary
```

#### Control 1 — Dedicated read-only DB user with explicit DENY

The DBA provisions a service account (`opsmind_ro` / `OPSMIND\\opsmind_svc`)
with **only** the grants needed for OpsMind to function:

```sql
-- SQL Server
GRANT CONNECT, SELECT ON DATABASE::FactoryDB TO opsmind_ro;
DENY  INSERT, UPDATE, DELETE, ALTER, EXECUTE TO opsmind_ro;
DENY  CREATE TABLE, CREATE PROCEDURE, CREATE VIEW TO opsmind_ro;

-- PostgreSQL
GRANT CONNECT ON DATABASE factorydb TO opsmind_ro;
GRANT USAGE ON SCHEMA public TO opsmind_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO opsmind_ro;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
       ON ALL TABLES IN SCHEMA public FROM opsmind_ro;
```

Full grant script is in `docs/connect-to-production-database.md`. The
**DENY** verbs are belt-and-braces: even if a future GRANT to `public`
or a role inheritance accidentally widens permissions, the explicit
DENY wins in SQL Server's permission resolution, and PostgreSQL's
REVOKE on `public` blocks the default-grant escape.

#### Control 2 — Connection-string flag forces the read replica

For SQL Server with Always On Availability Groups, the connection
string carries `ApplicationIntent=ReadOnly`. The listener routes the
session to a read-only secondary. Any session that arrives at the
primary with this intent is rejected, so an operator who somehow
re-pointed the DSN to the primary would still be refused.

For PostgreSQL, the connection string targets the read-replica
endpoint by hostname (e.g. `factorydb-ro.internal:5432`). Replicas are
physically separate database instances; write attempts return
`ERROR: cannot execute INSERT in a read-only transaction`.

#### Control 3 — Windows Authentication (Kerberos / AD)

Production deployment uses `trusted_connection=yes`. The opsmind-app
container receives a Kerberos ticket via `gMSA` (group managed service
account) or the operator's own AD identity if the deployment is per-
desk. Effect for IT:

- No password lives in environment variables, config files, or images.
- Connection attempts appear in AD audit logs under the named service
  account, not a generic "app" user.
- Disabling the AD account at the DC immediately revokes OpsMind's
  database access globally, without redeploying.

### 5.2 Why analytical reads do not lock transactional tables

Two reasons, both physical:

1. **The OCM / SI / packing-line traffic hits the primary.** OpsMind
   hits the replica. They are different database instances on different
   storage. There is no lock contention because there is no shared lock
   manager.
2. **Snapshot isolation on the replica.** Both SQL Server Always On
   readable secondaries and PostgreSQL streaming replicas serve reads
   from a transactionally consistent snapshot. SELECT statements
   acquire no row, page, or table locks that affect writers on the
   primary; the replica's apply process is asynchronous from the
   reader's perspective.

The maximum latency OpsMind can introduce on production OCM scan-back
or SI weigh transactions is **zero**, by construction. The replica's
own replication lag (typically <1s) is a property of the storage
layer, not of OpsMind's query load.

### 5.3 Snapshot strategy as fallback `[scoped]`

For sites without a true read replica (smaller deployments,
legacy ERP), v0.4 will support a scheduled snapshot pattern:

- A 03:00 cron job (DBA-owned, not OpsMind-owned) takes a logical
  dump or `pg_dump`/`bcp` snapshot of OpsMind's whitelisted tables.
- The snapshot loads into OpsMind's local DuckDB cache (see Section 7).
- OpsMind queries the cache. The source DB sees zero query traffic
  during the working day.

This pattern is the strongest possible isolation — the source DB and
OpsMind are physically decoupled except during the off-hours snapshot
window.

---

## 6. Section 3 — Security and data governance (`sql-guard` enforcement)

### 6.1 The pipeline position

```
LangGraph SQL-generation node
        │
        ▼  raw SQL string
   ┌──────────────────────────────┐
   │ sql-guard (sql-sop package)  │  ← 38 rules, 149+ tests
   │  • Stage 1: tokenise         │
   │  • Stage 2: AST parse        │
   │  • Stage 3: rule application │
   │  • Stage 4: severity filter  │
   │  • Stage 5: emit allow/deny  │
   └──────────────┬───────────────┘
                  │
        DENY ◀────┤    ALLOW
                  ▼
        ┌──────────────────────────┐
        │ modules/sql_validator.py │  ← second independent parser
        │  • row-cap injection     │
        │  • identifier allow-list │
        │  • multi-statement reject│
        └──────────────┬───────────┘
                       ▼
                ODBC execute
```

`sql-guard` runs before any database call. The validator runs after
`sql-guard` and is a defence-in-depth check using a different parser
(sqlparse vs sql-guard's hybrid regex/sqlparse), so a parsing bug in
one will not pass through both.

### 6.2 What `sql-guard` blocks

The rule pack (`sql_guard.rules`) rejects, with exit-code semantics:

| Category | Example rule IDs | Caught patterns |
|---|---|---|
| Schema mutation | E001–E008 | `CREATE`, `DROP`, `ALTER`, `TRUNCATE`, `RENAME` |
| Data mutation | E010–E019 | `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `UPSERT` |
| Privilege change | E020–E024 | `GRANT`, `REVOKE`, `DENY` |
| Code execution | E030–E034 | `EXEC`, `EXECUTE`, `xp_cmdshell`, OPENROWSET file paths |
| Multi-statement | E040 | `;` separating two top-level statements |
| Comment injection | W050–W055 | Trailing `-- ` or `/* ... */` after the SQL body |
| Assertion malformed | W025 | (sql-sop only — for SQL-SOP authoring, not OpsMind execution) |

The pack is open source and independently maintained at
github.com/Pawansingh3889/sql-guard. IT can pin a specific commit
SHA and audit every rule before deployment.

### 6.3 Why the LLM cannot bypass `sql-guard`

`sql-guard` is a Python library invoked synchronously in the agent's
own process. It is not a network service that could be bypassed,
spoofed, or rate-limited. The LangGraph node that calls the LLM has
no path to the ODBC executor except through:

```
agent.sql_validator_node(query) ──▶ sql_guard.check(query)
                                         │
                            if any(f.severity == "error"):
                                raise SqlGuardDenied(findings)
                                         │
                                         ▼
                            sql_validator.validate(query)
                                         │
                                         ▼
                                  engine.execute(query)
```

A code change to remove the `sql_guard.check()` call would land as a
diff in a PR, fail review, and break the unit test suite (`tests/
unit/test_sql_validator.py`, 28 tests). The control is enforced by
both code structure and CI.

### 6.4 Logging and audit trail

Every query — accepted or rejected — appends to `/app/logs/queries.jsonl`:

```json
{
  "ts": "2026-05-24T10:42:11Z",
  "user": "OPSMIND\\jdoe",
  "nl_question": "what was Tuesday's yield on line 2",
  "generated_sql": "SELECT ...",
  "sql_guard": {"verdict": "allow", "findings": []},
  "sql_validator": {"verdict": "allow", "row_cap_added": 1000},
  "rows_returned": 47,
  "duration_ms": 312
}
```

Logs are bind-mounted to a host path the SIEM can tail. Retention is
the SIEM's responsibility; OpsMind does not delete its own logs.

---

## 7. Section 4 — Local data layer (DuckDB & dbt) `[scoped]`

> **Status note.** As of v0.3.1, OpsMind queries the source DB
> directly for every operator question. The DuckDB cache and dbt
> models described below are scoped for v0.4. This section documents
> the target architecture so IT can pre-approve the design.

### 7.1 Why a local analytical cache

Operator questions like "show waste by product over the last 30 days"
expand into JOINs across `production`, `waste`, and `products`
tables. Re-running these against the source DB is wasteful and adds
unnecessary load even on a replica. The v0.4 pattern offloads the
analytical work to an in-container DuckDB file:

```
03:00 nightly  ──▶ pg_dump / bcp ──▶ DuckDB COPY ──▶ /app/data/cache.duckdb
                                                          │
operator question ──▶ LangGraph ──▶ dbt model ──▶ DuckDB query
                                                          │
                                                          ▼
                                                    result set
```

### 7.2 Why dbt locally

dbt models in `models/` are version-controlled SQL transforms that
build narrow, query-shaped views on top of the cache. Effect:

- Audit-shaped queries (yield-by-product, waste-by-shift,
  changeover-compliance-rollup) are defined once, tested with
  dbt's `tests:` block, and called repeatedly. No LLM is invoked
  for these — they hit the dbt model directly.
- A BRC auditor can read the `.sql` files and verify the calculation
  matches the QA spec. The LLM does not generate audit calculations.
- New domains plug in by adding new `.yml` + `.sql` files. No code
  change to OpsMind core.

### 7.3 Zero load on production

Once the nightly snapshot completes, **zero query traffic** from
OpsMind reaches the source DB for the rest of the day. Operator
questions resolve entirely inside the container against the DuckDB
file. CPU and RAM usage stay within the resource caps from §4.3.

For sites that prefer the live-query model, the DuckDB layer is
optional — set `OPSMIND_CACHE=disabled` and queries route to the
replica as in v0.3.1.

---

## 8. Section 5 — AI layer (on-premises Ollama)

### 8.1 The egress contract

The Ollama container has **no internet egress** in factory deployment.
This is enforced by:

1. **Container network policy.** `opsmind-net` is a private Docker
   bridge. Ollama has no `ports:` published to the host (port 11434
   is reachable only via service DNS from opsmind-app).
2. **Host firewall.** IT applies an outbound deny rule for the
   container IP range; only the source DB port (1433/5432) is allowed
   out, and only to the named replica host.
3. **Image provenance.** The Ollama image is pulled once at install
   time from `ollama/ollama:latest` (or a SHA-pinned tag). The model
   binary (`gemma3:12b`) is pulled into the named volume
   `opsmind-ollama-models` on first startup. No further outbound
   traffic from Ollama after the model is resident.

The reviewer can verify the no-egress claim with a packet capture
on the host's vEthernet adapter or via Windows Defender Firewall
logs.

### 8.2 What the LLM sees and what it never sees

The LLM sees:

- The operator's natural-language question.
- The relevant schema fragment from `schema.yaml` (table and column
  names for the detected domain only).
- Up to 5 retrieved documentation snippets from ChromaDB.

The LLM never sees:

- Actual row values from the database. SQL generation happens before
  execution. The model has no read-back of query results into a
  follow-up prompt unless the operator copy-pastes them into a new
  question (which the audit log will capture).
- Customer PII, recipe IP, supplier pricing, or retailer-confidential
  data. These never enter the prompt because the schema fragment is
  filtered to the detected query domain.

### 8.3 IP and confidentiality posture for BRC / retailer clauses

Retailer Code of Practice clauses (Tesco TFMS, M&S Plan A, Aldi) and
BRC §3.8 require that supplier data not leave the supplier's control.
OpsMind's on-prem Ollama satisfies this by construction:

- No call to OpenAI, Anthropic, Google, or any third-party LLM API.
- No telemetry to model authors. The Ollama runtime is local; the
  Gemma model file is local.
- Prompts and completions stay on the container's volume. No
  network destination receives them.

For audit: the relevant evidence is the Docker network configuration
(this document), the firewall rule (IT-supplied), and the packet
capture (one-time verification).

### 8.4 Model choice rationale

`gemma3:12b` is selected for three reasons relevant to IT:

1. **Apache 2.0 weights** — the licence permits commercial on-prem
   use without per-seat fees or telemetry obligations.
2. **CPU-runnable** — runs on a 32 GB factory laptop without a GPU.
   No specialised hardware procurement.
3. **Determinism switch** — Ollama exposes `temperature=0` for
   reproducible SQL generation in audit-relevant queries.

---

## 9. Threat model

The following table walks each plausible failure mode against the
controls that block it.

| # | Threat | Plausible vector | Layer that blocks it | Residual risk |
|---|---|---|---|---|
| T1 | LLM hallucinates a DROP TABLE | Prompt injection in operator question | L3 `sql-guard` rejects DDL | None — DDL is unreachable |
| T2 | LLM emits an INSERT | Adversarial prompt | L3 `sql-guard` + L1 DENY at DB | None — DML blocked at two layers |
| T3 | LLM emits a SELECT that locks tables for hours | `WITH (TABLOCK)` hint, cartesian JOIN | L4 row-cap injection (1000 rows) + replica isolation | Replica reader may serialise; primary unaffected |
| T4 | Operator points OpsMind at production primary | Edits `OPSMIND_DB` env var | L2 `ApplicationIntent=ReadOnly` routed away from primary; L1 DENY blocks writes anyway | None — primary refuses ReadOnly intent at session establishment |
| T5 | Container escapes to Windows host | Kernel exploit in WSL2 | Microsoft's WSL2 isolation; `no-new-privileges`; non-root user | Patch cadence on Windows is IT's responsibility |
| T6 | Compromised Ollama model leaks IP | Model contains exfil logic | No network egress from Ollama container | None — packets cannot leave |
| T7 | sql-guard has a parser bug that lets a write through | Novel CTE syntax confuses the parser | L4 `sql_validator.py` (different parser) + L1 DENY at DB | None — three independent layers must all fail |
| T8 | Operator account is compromised | Stolen AD credentials | AD account lockout; SIEM picks up anomalous query patterns from JSONL log | Same as any AD-authenticated app |
| T9 | OpsMind starves the host of memory | Streamlit memory leak | §4.3 cgroup caps (scoped); host OOM-kills the container, not host processes | Scoped for v0.4 |
| T10 | Audit trail is tampered with | Operator edits `queries.jsonl` | Logs bind-mounted to SIEM-controlled host path; container user has no chmod over the mount source | SIEM retention is IT's responsibility |

---

## 10. Network egress posture

The minimal allow-list for a factory deployment:

| Direction | Source | Destination | Port | Reason |
|---|---|---|---|---|
| Outbound | opsmind-app container | `factorydb-ro.internal` | 1433 (MSSQL) or 5432 (PG) | ODBC read against replica |
| Outbound | opsmind-app container | AD KDC | 88 / 464 | Kerberos ticket renewal |
| Outbound | opsmind-app container | SIEM webhook (optional) | 443 to named SIEM host only | Push alerts |
| Inbound | Operator laptop browser | host:8501 | 8501 | Streamlit UI |
| Internal | opsmind-app | opsmind-ollama | 11434 | LLM RPC, container-net only |

**Everything else is denied.** Notably: no outbound 443 to the
public internet. No DNS to public resolvers. No NTP to public pool
(use the AD-controlled NTP source).

---

## 11. Change-management process

Production changes follow the existing IT change ticket workflow.
The artifacts relevant to a change board are:

| Change type | Artifact reviewers see | Approval gate |
|---|---|---|
| OpsMind version bump | `CHANGELOG.md` between the two tags | IT change board + QA sign-off if any L3/L4 rule changed |
| Schema map change (`schema.yaml`) | Diff of the YAML | Domain owner (production / compliance / etc.) |
| sql-guard rule change | sql-guard PR + new tests | IT security + sql-guard maintainer |
| DB grant change | DBA-issued SQL script | DBA + IT security |
| Network rule change | Firewall ticket | IT network team |

The Ollama image and the gemma3:12b weights are pinned to a SHA in
the deployment manifest. A model upgrade is a deliberate change
ticket, not an auto-update.

---

## 12. Reviewer checklist (what to verify before sign-off)

Hand this to the IT manager performing the deployment review.

- [ ] `docker-compose.yml` has `security_opt: no-new-privileges:true`
- [ ] `docker-compose.yml` removes the `ollama` `ports:` block in production (or binds to 127.0.0.1)
- [ ] `Dockerfile` runs as `USER opsmind` (UID 1000), not root
- [ ] Resource caps in `deploy.resources.limits` are set (CPU, memory)
- [ ] `OPSMIND_DB` points to the read-replica DSN, not the primary
- [ ] Connection string includes `ApplicationIntent=ReadOnly` (SQL Server)
- [ ] DB user has explicit `DENY INSERT/UPDATE/DELETE/EXEC/ALTER` grants
- [ ] Windows Authentication is used (no password in env / image / config)
- [ ] Firewall denies all outbound from the container range except: replica DB port, AD KDC, named SIEM webhook
- [ ] `tests/unit/test_sql_validator.py` passes against the deployed version
- [ ] sql-guard version pinned to a SHA in `requirements.txt`
- [ ] Audit log (`/app/logs/queries.jsonl`) bind-mounted to a SIEM-tailed path
- [ ] Backup / DR plan for the bind-mount target

When all twelve boxes are ticked, OpsMind meets the safety bar
described in this document.

---

## 13. Glossary

| Term | Meaning in this document |
|---|---|
| **Defence in depth** | More than one independent control blocks the same failure mode. |
| **Process isolation** | The container's PID namespace is separate from the host's. |
| **Compute offloading** | Analytical work runs in OpsMind's container, not on the source DB. |
| **Table lock** | A row, page, or table-level lock acquired by a SELECT statement that blocks writers. Avoided here by using a replica. |
| **Egress monitoring** | Outbound network packets are observed and rule-checked at the host firewall. |
| **Read-only replica** | A separate database instance that receives replication from the primary and refuses write statements. |
| **Kerberos / Windows Authentication** | Token-based AD authentication; no password is transmitted or stored. |
| **Snapshot isolation** | Database transactions read from a consistent point-in-time view without blocking writers. |
| **Application Intent (ReadOnly)** | A SQL Server connection-string flag that routes the session to a readable secondary. |

---

## 14. Related documents

- `docs/connect-to-production-database.md` — DBA-facing setup runbook for L1 + L2
- `docs/multi-plant-deployment.md` — extending the architecture to a second plant
- `SECURITY.md` — vulnerability disclosure policy
- `CHANGELOG.md` — version-by-version change log
- sql-guard repo: github.com/Pawansingh3889/sql-guard — L3 implementation
