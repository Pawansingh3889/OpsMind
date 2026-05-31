# 2. Four independent layers enforce read-only access

Status: Accepted

## Context

OpsMind generates SQL from natural language and runs it against a
production database that sits alongside systems the factory cannot
afford to disturb — OCM scan-back, SI weighing scales, the ERP. The
failure that must never happen is a generated statement that writes to,
locks, or corrupts that data.

A single guard is not enough to make that promise credibly. An LLM can
be prompt-injected into emitting a `DELETE`; a regex validator can have
a parser gap; a connection flag can be misconfigured. Any one control,
alone, is one bug away from failure — and "we have a validator" is not
an answer an auditor accepts.

## Decision

Enforce read-only access with **four independent layers**, each of
which alone blocks a write. A write would have to defeat all four
simultaneously.

| Layer | Control | Enforced by |
|---|---|---|
| L1 | DB user with explicit `DENY INSERT/UPDATE/DELETE/EXEC/ALTER` | the database engine |
| L2 | `ApplicationIntent=ReadOnly` / read-replica DSN | the DB listener / topology |
| L3 | `sql-guard` static analysis before execution | OpsMind (regex + sqlparse) |
| L4 | `modules/sql_validator.py` second-pass parse + row cap | OpsMind (different parser) |

The independence is the point. L1 lives in the database, L2 in the
connection topology, L3 and L4 in OpsMind's own code using *different*
parsers — so a parsing bug in one validator does not pass through the
other.

## Consequences

- **Good:** the safety claim is defensible to an auditor as
  defence-in-depth, not a single point of trust. Each layer is
  independently verifiable (a write-attempt test per layer).
- **Good:** OpsMind reads from a replica, sharing no lock manager with
  the production primary — so it cannot add latency to OCM/SI writes
  by construction, not just by policy.
- **Bad:** four layers are more to configure and document (hence
  `docs/connect-to-production-database.md`). The DBA must set up L1+L2;
  they are not OpsMind's to enforce.
- **Bad:** L4's row cap (default 1000) can truncate a legitimately
  large result. Accepted: an ask-a-question tool should return a
  summarisable answer, not a full table dump.
- **Trade-off:** redundancy over simplicity. For a tool that touches
  production food-safety data, redundancy wins.
