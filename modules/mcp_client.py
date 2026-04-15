"""MCP client with graceful fallback to direct module calls.

If MCP servers are running, uses them via the protocol. If not, falls back
to direct imports of modules/database.py and modules/doc_search.py.
This ensures OpsMind works both with and without MCP infrastructure.

Usage::

    from modules.mcp_client import get_db_client, get_doc_client

    db = get_db_client()
    tables = db.discover_tables()
    results = db.query_database("SELECT * FROM products LIMIT 5")

    docs = get_doc_client()
    hits = docs.search_documents("allergen cleaning protocol")
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from config import (
    MCP_DB_HOST,
    MCP_DB_PORT,
    MCP_DOC_HOST,
    MCP_DOC_PORT,
    MCP_ENABLED,
)

log = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 3.0   # seconds
_REQUEST_TIMEOUT = 30.0   # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mcp_url(host: str, port: int, path: str) -> str:
    """Build the full SSE/HTTP URL for an MCP server endpoint."""
    return f"http://{host}:{port}{path}"


def _call_tool(host: str, port: int, tool_name: str, arguments: dict) -> dict:
    """Invoke an MCP tool over HTTP and return the parsed response.

    Raises ``ConnectionError`` if the server is unreachable so callers
    can fall back to direct module calls.
    """
    url = _mcp_url(host, port, "/call-tool")
    payload = {"name": tool_name, "arguments": arguments}
    try:
        resp = httpx.post(
            url,
            json=payload,
            timeout=httpx.Timeout(_REQUEST_TIMEOUT, connect=_CONNECT_TIMEOUT),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError as exc:
        raise ConnectionError(f"MCP server at {host}:{port} unreachable") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"MCP tool {tool_name} returned {exc.response.status_code}"
        ) from exc


def _extract_text(response: dict) -> str:
    """Pull the text content out of an MCP tool response envelope."""
    content = response.get("content", response)
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return "".join(parts)
    if isinstance(content, str):
        return content
    return json.dumps(content)


# ---------------------------------------------------------------------------
# Database client
# ---------------------------------------------------------------------------

@dataclass
class DatabaseClient:
    """Unified database client -- MCP or direct, same API."""

    _use_mcp: Optional[bool] = field(default=None, init=False)

    def _should_use_mcp(self) -> bool:
        """Check once whether the MCP database server is reachable."""
        if self._use_mcp is not None:
            return self._use_mcp

        if not MCP_ENABLED:
            self._use_mcp = False
            return False

        try:
            httpx.get(
                _mcp_url(MCP_DB_HOST, MCP_DB_PORT, "/health"),
                timeout=httpx.Timeout(_CONNECT_TIMEOUT),
            )
            self._use_mcp = True
            log.info("MCP database server detected at %s:%s", MCP_DB_HOST, MCP_DB_PORT)
        except Exception:
            self._use_mcp = False
            log.info(
                "MCP database server not available; using direct module calls"
            )
        return self._use_mcp

    # -- Tools ---------------------------------------------------------------

    def query_database(self, sql: str) -> str:
        """Execute a read-only SQL query and return JSON results."""
        if self._should_use_mcp():
            resp = _call_tool(MCP_DB_HOST, MCP_DB_PORT, "query_database", {"sql": sql})
            return _extract_text(resp)

        from modules import database
        df = database.query(sql)
        return df.to_json(orient="records", date_format="iso")

    def discover_tables(self) -> List[str]:
        """List all table names in the connected database."""
        if self._should_use_mcp():
            resp = _call_tool(MCP_DB_HOST, MCP_DB_PORT, "discover_tables", {})
            text = _extract_text(resp)
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []

        from modules import database
        return database.discover_tables()

    def discover_columns(self, table_name: str) -> List[str]:
        """List column names for a specific table."""
        if self._should_use_mcp():
            resp = _call_tool(
                MCP_DB_HOST, MCP_DB_PORT, "discover_columns",
                {"table_name": table_name},
            )
            text = _extract_text(resp)
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else []

        from modules import database
        return database.discover_columns(table_name)

    def get_schema_for_domain(self, domain: str) -> str:
        """Return relevant tables/columns for a business domain."""
        if self._should_use_mcp():
            resp = _call_tool(
                MCP_DB_HOST, MCP_DB_PORT, "get_schema_for_domain",
                {"domain": domain},
            )
            return _extract_text(resp)

        from modules import schema_registry
        tables = schema_registry.get_tables_for_domain(domain)
        return json.dumps(tables, indent=2) if tables else json.dumps(
            {"error": f"Unknown domain: {domain}"}
        )


# ---------------------------------------------------------------------------
# Document search client
# ---------------------------------------------------------------------------

@dataclass
class DocSearchClient:
    """Unified document search client -- MCP or direct, same API."""

    _use_mcp: Optional[bool] = field(default=None, init=False)

    def _should_use_mcp(self) -> bool:
        """Check once whether the MCP doc-search server is reachable."""
        if self._use_mcp is not None:
            return self._use_mcp

        if not MCP_ENABLED:
            self._use_mcp = False
            return False

        try:
            httpx.get(
                _mcp_url(MCP_DOC_HOST, MCP_DOC_PORT, "/health"),
                timeout=httpx.Timeout(_CONNECT_TIMEOUT),
            )
            self._use_mcp = True
            log.info(
                "MCP doc-search server detected at %s:%s", MCP_DOC_HOST, MCP_DOC_PORT
            )
        except Exception:
            self._use_mcp = False
            log.info(
                "MCP doc-search server not available; using direct module calls"
            )
        return self._use_mcp

    # -- Tools ---------------------------------------------------------------

    def search_documents(self, query: str, top_k: int = 5) -> str:
        """Semantic search over factory documents."""
        if self._should_use_mcp():
            resp = _call_tool(
                MCP_DOC_HOST, MCP_DOC_PORT, "search_documents",
                {"query": query, "top_k": top_k},
            )
            return _extract_text(resp)

        from modules import doc_search_pg as doc_search
        results = doc_search.search(query, n_results=top_k)
        return json.dumps(results, default=str)

    def get_document_count(self) -> int:
        """Return the total number of document chunks in the vector store."""
        if self._should_use_mcp():
            resp = _call_tool(MCP_DOC_HOST, MCP_DOC_PORT, "get_document_count", {})
            text = _extract_text(resp)
            try:
                return int(text)
            except (ValueError, TypeError):
                return -1

        from modules import doc_search_pg as doc_search
        return doc_search.get_doc_count()

    def get_domain_context(self, domain: str) -> str:
        """Load domain-specific documentation for LLM context injection."""
        if self._should_use_mcp():
            resp = _call_tool(
                MCP_DOC_HOST, MCP_DOC_PORT, "get_domain_context",
                {"domain": domain},
            )
            return _extract_text(resp)

        from modules import domain_docs
        section = domain_docs.get_domain_prompt_section(domain)
        return section or ""


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_db_client: Optional[DatabaseClient] = None
_doc_client: Optional[DocSearchClient] = None


def get_db_client() -> DatabaseClient:
    """Return the shared database client (created on first call)."""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client


def get_doc_client() -> DocSearchClient:
    """Return the shared document-search client (created on first call)."""
    global _doc_client
    if _doc_client is None:
        _doc_client = DocSearchClient()
    return _doc_client
