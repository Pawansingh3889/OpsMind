# Connecting OpsMind to a production database

Step-by-step setup for pointing OpsMind at a real ERP (SI Integreater,
SAP, or any SQL Server / PostgreSQL database) instead of the bundled
SQLite demo. Written for the moment a Hull-plant deployment goes live
and stays useful for plant-2 onboarding under the AKT 6 scope.

> **TL;DR.** Three independent layers of read-only enforcement:
> Layer 1 (DB grants), Layer 2 (connection string flag), Layer 3
> (OpsMind's app-layer validator, already shipped). Set up the first
> two, verify all three with the test commands at the end of this doc.

---

## What this guide covers

- Creating a read-only DB user (SQL Server, PostgreSQL)
- Configuring `OPSMIND_DB` for production
- Verifying all three safety layers behave as documented
- Production hardening recommendations
- A ready-to-send IT / DBA request

## What this guide doesn't cover

- Network configuration (firewalls, VPN, jump hosts) — talk to IT.
- Schema mapping for the new database — see
  [`multi-plant-deployment.md`](multi-plant-deployment.md) § Step 3.
- Initial OpsMind install / Ollama setup — see the main `README.md`.

## Hard non-negotiables

- **The DB user must be read-only.** OpsMind's own validator blocks
  writes (Layer 3), but Layers 1-2 are independent defence in depth.
- **No queries about real-time temperature data.** Temperature is not
  in OpsMind's NL query surface — see the README scope note.
  Temperature batch-traceability columns (e.g. `temperature_on_arrival`,
  `received_temp_c`) stay accessible via the compliance domain for
  audit-trail reconstruction; real-time monitoring belongs in the
  formal SCADA / compliance dashboard.

---

## Layer 1 — Create a read-only database user

This is the DBA conversation. Grant `SELECT` only, then explicitly
`DENY` everything else so a future grant cannot silently widen access.

### SQL Server (SI Integreater and similar)

```sql
-- Run on the production database as a DBA.
USE [ProductionDB];
GO

-- 1. Login at the server level.
CREATE LOGIN opsmind_ro WITH PASSWORD = 'change-me-strong-password';
GO

-- 2. Map the login into the database.
CREATE USER opsmind_ro FOR LOGIN opsmind_ro;
GO

-- 3. Grant SELECT on the schemas OpsMind needs.
GRANT SELECT ON SCHEMA::dbo TO opsmind_ro;
-- If SI Integreater uses other schemas, add them explicitly:
-- GRANT SELECT ON SCHEMA::production TO opsmind_ro;
-- GRANT SELECT ON SCHEMA::compliance TO opsmind_ro;

-- 4. Explicit DENY — defence against a future inherited grant.
DENY INSERT, UPDATE, DELETE, ALTER, CREATE, DROP, EXECUTE
  ON SCHEMA::dbo TO opsmind_ro;
GO

-- 5. Verify as the new user.
EXECUTE AS USER = 'opsmind_ro';
SELECT TOP 1 * FROM dbo.ProductionBatch;   -- should succeed
-- INSERT INTO dbo.ProductionBatch (...) VALUES (...);  -- should fail
REVERT;
GO
```

### PostgreSQL

```sql
-- Run as a DB owner.
CREATE USER opsmind_ro WITH PASSWORD 'change-me-strong-password';

GRANT CONNECT ON DATABASE production TO opsmind_ro;
GRANT USAGE ON SCHEMA public TO opsmind_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO opsmind_ro;

-- New tables added later should also be SELECT-able by opsmind_ro.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO opsmind_ro;

-- Verify
SET ROLE opsmind_ro;
SELECT * FROM production LIMIT 1;          -- should succeed
-- DELETE FROM production WHERE id = 1;    -- should fail
RESET ROLE;
```

### Why explicit `DENY` matters (SQL Server specifically)

SQL Server resolves grants additively. If `opsmind_ro` is later added
to a role that has `INSERT` on the same schema (say a generic
"datateam" role), the SELECT-only restriction silently disappears.
An explicit `DENY` overrides any later grant — including role
inheritance. That is the difference between "we forgot to grant it"
and "we cannot grant it" from an audit perspective.

---

## Layer 2 — Configure OpsMind's connection string

OpsMind reads the DB connection from the `OPSMIND_DB` environment
variable (defaults to `sqlite:///data/demo.db` for the demo). Point
it at the production database with one of the patterns below.

### SQL Server — SQL authentication

```bash
export OPSMIND_DB="mssql+pyodbc://opsmind_ro:PASSWORD@PROD-SQL-HOST/ProductionDB?driver=ODBC+Driver+18+for+SQL+Server&readonly=true"
```

### SQL Server — Windows authentication (preferred)

```bash
export OPSMIND_DB="mssql+pyodbc://PROD-SQL-HOST/ProductionDB?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&readonly=true"
```

Windows auth means no password in environment variables (visible
via `ps`, in service definitions, in logs). The connecting Windows
account on the OpsMind host must already be an authorised user on
the SQL Server.

### SQL Server — Always On secondary (best for production)

```bash
export OPSMIND_DB="mssql+pyodbc://PROD-SQL-AG-LISTENER/ProductionDB?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&ApplicationIntent=ReadOnly&readonly=true"
```

`ApplicationIntent=ReadOnly` routes the connection to a read-only
secondary in an Always On Availability Group. No contention with
the production write workload, no risk of accidental write.

### PostgreSQL

```bash
export OPSMIND_DB="postgresql://opsmind_ro:PASSWORD@prod-pg-host/production?options=-c%20default_transaction_read_only%3Don"
```

The `default_transaction_read_only=on` flag is enforced by the
Postgres backend at session level — every statement runs in a
read-only transaction even if the user is somehow granted write
privilege.

### Where to set `OPSMIND_DB` in production

| Platform | How |
|---|---|
| **Linux service** | `Environment=` line in the systemd unit file |
| **Windows service** | Set as a system environment variable via Control Panel, then restart the service |
| **Docker** | `-e OPSMIND_DB="..."` on `docker run`, or `environment:` in `docker-compose.yml` |
| **Local dev** | `export` in your shell, or a `.env` file (gitignored) |

For Windows services running OpsMind under a domain account, the
domain account becomes the connecting principal — no password
needed if Windows auth is configured at the SQL Server.

---

## Layer 3 — App-layer validator (already shipped)

No action required. OpsMind enforces the following at the application
level in `modules/sql_agent.py`, regardless of DB user grants:

- Only `SELECT` and `WITH` statements allowed through.
- Blocked keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
  `TRUNCATE`, `EXEC`, `EXECUTE`, `xp_`, `sp_`.
- Stripped before matching: string literals, single-line comments,
  block comments — so a write hidden in `-- /* INSERT */ DROP TABLE`
  cannot smuggle through.
- Schema scoping: only tables listed in `schema.yaml` (or the default
  schema) are visible to the LLM. The LLM cannot generate SQL for
  tables it cannot see.

Coverage of this layer is in `tests/unit/test_sql_validator.py`
(28 tests, including injection patterns and edge cases) and the
`tests/eval/` golden set.

---

## Verifying all three layers end to end

After Layers 1 and 2 are in place, run these checks from the OpsMind
host:

```bash
# 1. Connection works (Layer 2)
python -c "from modules.database import query; print(query('SELECT TOP 5 BatchID FROM dbo.ProductionBatch'))"

# 2. App-layer block works (Layer 3) — should print a safety error,
# not execute the DELETE.
python -c "from modules.sql_agent import run_query; print(run_query('DELETE FROM dbo.ProductionBatch'))"

# 3. DB-layer block works (Layer 1) — bypass the app layer by going
# direct via SQLAlchemy. Should raise a permission-denied error.
python <<'PYEOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["OPSMIND_DB"])
with engine.connect() as conn:
    try:
        conn.execute(text("INSERT INTO dbo.ProductionBatch DEFAULT VALUES"))
        conn.commit()
        print("FAIL: DB allowed an INSERT — the user has too many grants.")
    except Exception as exc:
        print(f"OK: DB rejected the write ({exc.__class__.__name__}).")
PYEOF
```

**Expected outcome:** check 1 prints rows; check 2 prints a safety
error and runs nothing; check 3 prints "OK: DB rejected the write."

If check 3 fails (DB allowed the INSERT), the DBA over-granted. Go
back to Layer 1 and tighten before going live.

---

## Production hardening

Once the three layers verify clean, these are the hardening steps
worth doing before declaring the deployment ready for a BRC audit.

### 1. Use a read-replica, not the primary

SQL Server Always On secondaries are read-only by design. OpsMind
running against a secondary removes any contention concern on the
primary. Use the `ApplicationIntent=ReadOnly` connection string
pattern above. Worth a conversation with IT.

### 2. Vault the password

Don't put the password in a shell environment variable visible to
`ps`. Options:

- **Windows auth** — no password to vault.
- **Windows Credential Manager** — store credentials per service
  account, retrieve via DPAPI.
- **Restrictive `.env` file** — `chmod 600`, owned by the service
  account, never committed.

### 3. Enable DB-side audit logging

SQL Server Audit can record every statement issued by `opsmind_ro`,
including the connecting Windows account and timestamp. This is the
evidence trail an auditor will want to see if they ask "what did
this tool look at?" The audit data lives in the DB, not in OpsMind
— defence against tampering on the OpsMind side.

### 4. Network isolation

The OpsMind host should:

- Only allow outbound traffic to the production DB host (firewall).
- Block outbound internet traffic — Ollama runs locally; no
  telemetry needed.
- Be on the production network segment, not a corporate LAN with
  internet access.

### 5. Systemd / Windows service with restart policy

OpsMind is a Streamlit app. Run it under a process supervisor so a
crash auto-restarts and logs go to a rotating file. Example
`systemd` unit:

```ini
[Unit]
Description=OpsMind
After=network.target

[Service]
Type=simple
User=opsmind
WorkingDirectory=/opt/opsmind
Environment="OPSMIND_DB=mssql+pyodbc://..."
ExecStart=/opt/opsmind/.venv/bin/streamlit run app.py
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/opsmind/app.log
StandardError=append:/var/log/opsmind/app.log

[Install]
WantedBy=multi-user.target
```

### 6. Schema mapping before go-live

Edit `schema.yaml` for the production schema before pointing OpsMind
at the real DB. See [`multi-plant-deployment.md`](multi-plant-deployment.md)
§ Step 3 for the pattern.

---

## Sample IT / DBA request

Copy, fill in the bracketed bits, send.

```
Subject: Read-only DB user request for OpsMind production deployment

Hi [DBA name],

I need a read-only SQL Server login created on the [ProductionDB] database
for an internal data tool (OpsMind — natural-language query assistant for
the production data, runs entirely on-prem). Minimum scope:

  - Login name:   opsmind_ro
  - Authentication: [Windows auth preferred / SQL auth if needed]
  - Grants:       SELECT on the schemas OpsMind needs ([dbo] and any
                  SI Integreater app schemas the tool will query)
  - Explicit DENY on INSERT, UPDATE, DELETE, ALTER, CREATE, DROP, EXECUTE
                  on the same schemas
  - No EXECUTE on any stored procedures or extended stored procedures
  - Always On routing: ApplicationIntent=ReadOnly to the secondary
                  replica if available

Suggested SQL is below (taken from OpsMind's production-database setup
guide):

  [paste the SQL block from Layer 1 of this doc]

Network access required:
  - OpsMind host:  [hostname / IP]
  - Destination:   [PROD-SQL-HOST:1433]
  - Direction:     outbound from OpsMind host only

I can verify the user behaves as expected once it's provisioned — the
verification commands are in our setup guide.

Thanks,
[Your name]
```

The framing matters. "AI tool that queries the DB" sets off alarm
bells; "read-only user for an internal data tool, with explicit DENY
on all writes" reads as a routine grant request.

---

## Troubleshooting

### `Login failed for user 'opsmind_ro'`

- Password mismatch — re-set with `ALTER LOGIN opsmind_ro WITH PASSWORD = '...'`
- Login exists at server level but user not created in the database —
  re-run `CREATE USER opsmind_ro FOR LOGIN opsmind_ro;` inside the
  target DB
- Windows auth: the connecting Windows account isn't authorised on
  the SQL Server. DBA needs to add it.

### `[ODBC Driver Manager] Data source name not found and no default driver specified`

- ODBC Driver 17/18 for SQL Server isn't installed on the OpsMind
  host. Download from Microsoft and install.
- On Linux: `sudo apt install msodbcsql18 unixodbc-dev`
- Connection-string driver name must match exactly — `ODBC+Driver+18+for+SQL+Server`
  (URL-encoded spaces).

### `Permission denied for relation X` (Postgres)

- `GRANT SELECT` not applied to that specific table. Add it, or use
  the `ALTER DEFAULT PRIVILEGES` pattern from Layer 1.

### `permission was denied on object 'sp_executesql'` (SQL Server)

- SQL Server requires `EXECUTE` on a few system procedures even for
  pure SELECT workloads. If you've issued a blanket `DENY EXECUTE`,
  selectively re-grant: `GRANT EXECUTE ON sys.sp_executesql TO opsmind_ro;`
  (or use the connection-string approach which doesn't trigger this).

### "BRC auditor is asking about the AI tool"

- Point them at: this doc + the README scope note + the SQL audit
  log on the DB side. The audit trail lives at the DB, not in
  OpsMind.
- Temperature data is not in the NL query surface (see README scope
  note) — formal monitoring is via SCADA and the compliance
  dashboard.

---

## Related documentation

- [`README.md`](../README.md) § Scope — what OpsMind does and
  deliberately doesn't query
- [`multi-plant-deployment.md`](multi-plant-deployment.md) § Steps 2-3
  — connection string and schema mapping in context of a multi-plant
  rollout
- [`tests/eval/AKT6-extension.md`](../tests/eval/AKT6-extension.md) —
  validation methodology for production deployments
- `AGENTS.md` (project root) — architecture and safety stack overview
