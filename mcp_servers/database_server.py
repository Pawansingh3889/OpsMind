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
    """Execute a read-only SQL query and return results as JSON.

    Only SELECT and WITH statements are permitted. The underlying
    database module enforces read-only access.

    Args:
        sql: A valid SQL SELECT or WITH statement.

    Returns:
        A JSON string containing the query results as a list of row-dicts,
        or a JSON object with an ``error`` key on failure.
    """
    try:
        df = database.query(sql)
        return df.to_json(orient="records", date_format="iso")
    except Exception as exc:
        log.exception("query_database failed for: %s", sql[:200])
        return json.dumps({"error": str(exc)})


@mcp.tool()
def discover_tables() -> list[str]:
    """List all table names in the connected database.

    Returns:
        A list of table name strings.
    """
    try:
        return database.discover_tables()
    except Exception as exc:
        log.exception("discover_tables failed")
        return [f"error: {exc}"]


@mcp.tool()
def discover_columns(table_name: str) -> list[str]:
    """List column names for a specific table.

    Args:
        table_name: The exact table name as returned by ``discover_tables``.

    Returns:
        A list of column name strings.
    """
    try:
        return database.discover_columns(table_name)
    except Exception as exc:
        log.exception("discover_columns failed for table: %s", table_name)
        return [f"error: {exc}"]


@mcp.tool()
def get_schema_for_domain(domain: str) -> str:
    """Return the relevant tables and columns for a business domain.

    OpsMind organises its 19+ database tables into seven business domains
    (production, orders, compliance, traceability, temperature, staff,
    stock). This tool returns only the tables relevant to the requested
    domain, keeping LLM context focused and accurate.

    Args:
        domain: One of the recognised domain names (e.g. ``"production"``,
            ``"compliance"``).

    Returns:
        A formatted string listing tables and their columns for the domain,
        or a JSON object with an ``error`` key if the domain is unknown.
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
