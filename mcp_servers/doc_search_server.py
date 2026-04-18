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
    """Semantic-search factory SOPs, audit reports, product specs, and
    compliance procedures.

    **Use this when** the question is about *how we do something* rather than
    *what the data says* — cleaning protocols, allergen changeovers, audit
    requirements, product specifications, supplier approval steps. For
    numeric answers ("how many", "what was yesterday's yield") use
    ``query_database`` instead.

    Matches are ranked by cosine distance of sentence-transformer
    embeddings, so the query doesn't need exact keywords — phrase it the
    way an operator would ask. Results are chunks of the original documents
    with enough surrounding context to answer, not just bare sentences.

    Args:
        query: A natural-language question or topic. Examples that work
            well: "allergen cleaning procedure between Line 2 runs", "what
            certifications do MSC suppliers need", "cold-chain rules for
            dispatch". 3–15 words is the sweet spot.
        top_k: Maximum chunks to return. Defaults to 5. Increase to 10
            when you need breadth (survey-style questions); keep at 3 for
            a single focused answer.

    Returns:
        A JSON array of result objects::

            [
              {
                "id": "sop_allergen_v3.pdf#chunk_4",
                "text": "When changing over from a cereal line to a...",
                "metadata": {"source": "sop_allergen_v3.pdf", "page": 8},
                "distance": 0.187
              },
              ...
            ]

        Lower ``distance`` means a closer semantic match. On error returns
        ``{"error": "<message>"}``.
    """
    try:
        results = doc_search.search(query, n_results=top_k)
        return json.dumps(results, default=str)
    except Exception as exc:
        log.exception("search_documents failed for query: %s", query[:200])
        return json.dumps({"error": str(exc)})


@mcp.tool()
def get_document_count() -> int:
    """Return how many document chunks are currently indexed.

    **Use this when** the user asks "do you have the X procedure" or when
    you want to sanity-check the knowledge base before telling the user no
    documents were found (zero chunks means ingestion hasn't run, not that
    the answer is unknown).

    Returns:
        An integer count of indexed chunks, or ``-1`` if the vector store
        is unreachable.
    """
    try:
        return doc_search.get_doc_count()
    except Exception:
        log.exception("get_document_count failed")
        return -1


@mcp.tool()
def get_domain_context(domain: str) -> str:
    """Load hand-curated business rules for one domain, as LLM prompt context.

    **Use this when** you're about to write SQL or interpret a result and
    want domain-specific thresholds or definitions — e.g. "what counts as a
    temperature breach", "what yield is considered low", "BRCGS clauses
    relevant to traceability". These are short authoritative notes, not
    searched SOPs; call ``search_documents`` for longer procedural text.

    **Available domains** (only these three have curated rules today):

    - ``production`` — yield thresholds, shift definitions, waste targets
    - ``compliance`` — BRCGS clauses, allergen handling, audit trail rules
    - ``waste``      — waste-type categories and cost assumptions

    Any other domain name returns an empty string — this is not an error,
    just "no curated rules for that domain yet". In that case fall back to
    ``search_documents`` with a relevant query.

    Args:
        domain: One of ``"production"``, ``"compliance"``, ``"waste"``.

    Returns:
        A markdown-formatted prompt section ready to prepend to a system
        prompt, or an empty string if the domain has no curated rules.
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
