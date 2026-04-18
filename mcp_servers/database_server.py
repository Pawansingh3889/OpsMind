"""MCP server exposing OpsMind database operations as tools.

Based on PyCon DE 2026: "Building Agentic Systems with LangGraph, MCP, and A2A" (Nosekabel).
Decouples data access from agent logic via Model Context Protocol.

Run: python -m mcp_servers.database_server
"""
from __future__ import annotations

import json
import logging
import os
import sys

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Ensure the project root is importable so ``modules.database`` resolves.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import MCP_DB_HOST, MCP_DB_PORT  # noqa: E402
from modules import (
    database,  # noqa: E402
    schema_registry,  # noqa: E402
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP application
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "OpsMind Database Server",
    description=(
        "Exposes the OpsMind manufacturing database as read-only MCP tools. "
        "Provides SQL execution, table/column discovery, and schema lookup "
        "scoped by business domain."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def query_database(sql: str) -> str:
    """Run a read-only SQL query against the factory ERP database and return rows as JSON.

    **Use this when** the user asks a factual operational question that needs
    data — e.g. "how much did we produce yesterday", "list orders for Customer A
    due this week", "which batch used supplier X". Always call
    ``get_schema_for_domain`` first if you don't already know the column names,
    otherwise the query will fail with a schema error.

    **Safety:** only ``SELECT`` and ``WITH`` statements are allowed. Any
    ``INSERT``/``UPDATE``/``DELETE``/``DROP``/``ALTER``/``TRUNCATE``/``EXEC``
    keyword is rejected before execution. The connection is read-only at the
    database layer as well, so a mistakenly-constructed write would also fail.

    Args:
        sql: A single SQL ``SELECT`` or ``WITH`` statement. SQLite dialect on
            the demo database (``date('now', '-7 days')`` for date arithmetic);
            T-SQL dialect on production SQL Server deployments.

    Returns:
        A JSON string containing the rows as a list of objects, one per row,
        with ISO-8601 date strings. On failure returns
        ``{"error": "<message>"}`` — inspect the error and retry with
        corrected SQL rather than asking the user what went wrong.

    Example:
        Input: ``SELECT customer, SUM(quantity_kg) AS total FROM orders
        WHERE status='pending' GROUP BY customer``
        Output: ``[{"customer": "Customer A", "total": 420.0}, ...]``
    """
    try:
        df = database.query(sql)
        return df.to_json(orient="records", date_format="iso")
    except Exception as exc:
        log.exception("query_database failed for: %s", sql[:200])
        return json.dumps({"error": str(exc)})


@mcp.tool()
def discover_tables() -> list[str]:
    """List every table name in the connected database.

    **Use this when** you don't know which tables exist — typically once at
    the start of a session, or when ``query_database`` fails with an
    unknown-table error. For day-to-day questions prefer
    ``get_schema_for_domain`` instead: it returns a smaller, curated set
    scoped to the business area so the LLM context stays focused.

    Returns:
        A list of table-name strings in alphabetical order. On the demo
        database this is roughly 20 tables; on a real factory ERP it may
        exceed 100.
    """
    try:
        return database.discover_tables()
    except Exception as exc:
        log.exception("discover_tables failed")
        return [f"error: {exc}"]


@mcp.tool()
def discover_columns(table_name: str) -> list[str]:
    """List every column in a specific table.

    **Use this when** you're writing SQL against a table whose exact column
    names you aren't sure about (especially common on the production ERP
    where columns use PascalCase, e.g. ``ProductionDate``, not
    ``production_date``). Call this instead of guessing; a wrong column name
    causes the query to fail.

    Args:
        table_name: Exact table name as returned by ``discover_tables`` or
            ``get_schema_for_domain``. Case-sensitive on some backends.

    Returns:
        A list of column-name strings in the table's defined order.
    """
    try:
        return database.discover_columns(table_name)
    except Exception as exc:
        log.exception("discover_columns failed for table: %s", table_name)
        return [f"error: {exc}"]


@mcp.tool()
def get_schema_for_domain(domain: str) -> str:
    """Return only the tables relevant to a business area, with their columns.

    **Use this when** you're about to write SQL and want to keep the LLM
    context tight. It's the preferred entry point for almost every question —
    ``discover_tables`` is a fallback for when the domain mapping has a gap.

    **Recognised domains** (pick the best match for the user's question):

    - ``production``   — output, yield, waste, production runs
    - ``orders``       — customer orders, delivery dates, shipped vs pending
    - ``traceability`` — batch lineage from raw material to dispatch
    - ``temperature``  — cold room / freezer / dispatch temperature logs
    - ``staff``        — employees, shift patterns, weekly hours, overtime
    - ``stock``        — raw materials, expiry dates, suppliers
    - ``compliance``   — allergens, non-conformance, certified batches

    Args:
        domain: One of the seven names above. Anything else returns an error.

    Returns:
        A JSON object mapping table name to a comma-separated column list.
        Example::

            {
              "products": "id, name, species, unit_cost_per_kg, ...",
              "production": "id, product_id, batch_code, date, ..."
            }

        On an unknown domain returns ``{"error": "Unknown domain: <name>"}``.
    """
    try:
        tables = schema_registry.get_tables_for_domain(domain)
        if not tables:
            return json.dumps({"error": f"Unknown domain: {domain}"})
        return json.dumps(tables, indent=2)
    except Exception as exc:
        log.exception("get_schema_for_domain failed for: %s", domain)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Health resource
# ---------------------------------------------------------------------------

@mcp.resource("health://status")
def health_status() -> str:
    """Return server health information."""
    try:
        tables = database.discover_tables()
        table_count = len(tables)
        status = "healthy"
    except Exception as exc:
        table_count = 0
        status = f"degraded: {exc}"

    return json.dumps({
        "server": "OpsMind Database MCP",
        "status": status,
        "table_count": table_count,
    })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the MCP database server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    host = os.getenv("MCP_DB_HOST", MCP_DB_HOST)
    port = int(os.getenv("MCP_DB_PORT", str(MCP_DB_PORT)))
    log.info("Starting OpsMind Database MCP server on %s:%s", host, port)
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
