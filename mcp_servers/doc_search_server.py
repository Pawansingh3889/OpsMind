"""MCP server exposing OpsMind document search as tools.

Supports ChromaDB and pgvector backends via config.VECTOR_DB setting.
The backend selection is handled transparently by the underlying
doc_search_pg module, which falls back to ChromaDB when PostgreSQL
is unavailable.

Run: python -m mcp_servers.doc_search_server
"""
from __future__ import annotations

import json
import logging
import os
import sys

from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Ensure the project root is importable.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config import MCP_DOC_HOST, MCP_DOC_PORT, VECTOR_DB  # noqa: E402
from modules import doc_search_pg as doc_search  # noqa: E402
from modules import domain_docs  # noqa: E402

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP application
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "OpsMind Document Search Server",
    description=(
        "Exposes semantic document search over factory SOPs, compliance "
        "documents, and operational procedures. Supports ChromaDB and "
        "pgvector backends."
    ),
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_documents(query: str, top_k: int = 5) -> str:
    """Semantic search over factory documents (SOPs, audit reports, specs).

    Uses sentence-transformer embeddings to find the most relevant
    document chunks for a natural-language query.

    Args:
        query: A natural-language search query (e.g. "allergen cleaning
            protocol for Line 2").
        top_k: Maximum number of results to return. Defaults to 5.

    Returns:
        A JSON string containing a list of result objects, each with
        ``id``, ``text``, ``metadata``, and ``distance`` keys.
    """
    try:
        results = doc_search.search(query, n_results=top_k)
        return json.dumps(results, default=str)
    except Exception as exc:
        log.exception("search_documents failed for query: %s", query[:200])
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_document_count() -> int:
    """Return the total number of document chunks in the vector store.

    Returns:
        An integer count of indexed document chunks.
    """
    try:
        return doc_search.get_doc_count()
    except Exception:
        log.exception("get_document_count failed")
        return -1


@mcp.tool()
def get_domain_context(domain: str) -> str:
    """Load domain-specific documentation for LLM context injection.

    Reads the markdown knowledge file for a business domain (e.g.
    production thresholds, compliance rules, waste targets) and returns
    it as a formatted prompt section.

    Args:
        domain: One of the recognised domain names (e.g. ``"production"``,
            ``"compliance"``, ``"waste"``).

    Returns:
        A formatted markdown string with domain knowledge, or an empty
        string if no documentation exists for the domain.
    """
    try:
        section = domain_docs.get_domain_prompt_section(domain)
        return section or ""
    except Exception as exc:
        log.exception("get_domain_context failed for: %s", domain)
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Health resource
# ---------------------------------------------------------------------------

@mcp.resource("health://status")
def health_status() -> str:
    """Return server health information."""
    try:
        count = doc_search.get_doc_count()
        status = "healthy"
    except Exception as exc:
        count = 0
        status = f"degraded: {exc}"

    return json.dumps({
        "server": "OpsMind Document Search MCP",
        "status": status,
        "backend": VECTOR_DB,
        "document_count": count,
    })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Start the MCP document search server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    host = os.getenv("MCP_DOC_HOST", MCP_DOC_HOST)
    port = int(os.getenv("MCP_DOC_PORT", str(MCP_DOC_PORT)))
    log.info(
        "Starting OpsMind Document Search MCP server on %s:%s (backend=%s)",
        host, port, VECTOR_DB,
    )
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
