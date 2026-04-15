"""Runtime-loaded domain documentation for LLM context injection.

Reads markdown files from ``docs/domains/`` and makes their content
available to the SQL-generation prompt so the LLM understands business
rules, thresholds, and terminology without hardcoding them in Python.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

import streamlit as st

from config import DOMAIN_DOCS_DIR

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping from schema-registry domain names to doc filenames (without .md)
# ---------------------------------------------------------------------------

_DOMAIN_TO_DOC: Dict[str, str] = {
    "production": "production",
    "compliance": "compliance",
    "temperature": "compliance",  # temperature rules live in compliance doc
    "traceability": "compliance",
    "orders": "production",       # order context uses production thresholds
    "staff": "production",        # staffing context uses shift patterns
    "stock": "waste",             # stock/expiry relates to waste management
}


# ---------------------------------------------------------------------------
# Loader (cached in Streamlit)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_domain_file(file_path: str) -> str:
    """Read a single domain doc from disk. Cached across Streamlit reruns."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("Domain doc not found: %s", file_path)
        return ""
    except Exception as exc:
        log.warning("Failed to read domain doc %s: %s", file_path, exc)
        return ""


def _docs_dir() -> Path:
    """Resolve the docs/domains/ directory, relative to project root."""
    return Path(DOMAIN_DOCS_DIR)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_domain_context(domain: str) -> str:
    """Return the domain-knowledge markdown for the given domain name.

    Args:
        domain: One of the domain keys used by
            ``schema_registry.detect_domain`` (e.g. ``"production"``,
            ``"compliance"``).

    Returns:
        The full markdown text, or an empty string if no doc exists.
    """
    doc_name = _DOMAIN_TO_DOC.get(domain, domain)
    doc_path = _docs_dir() / f"{doc_name}.md"
    return _load_domain_file(str(doc_path))


def load_all_domain_docs() -> Dict[str, str]:
    """Load every ``.md`` file in the domains directory.

    Returns:
        Dict mapping filename stems (e.g. ``"production"``) to their
        markdown content.
    """
    docs_path = _docs_dir()
    result: Dict[str, str] = {}
    if not docs_path.is_dir():
        log.warning("Domain docs directory does not exist: %s", docs_path)
        return result

    for md_file in sorted(docs_path.glob("*.md")):
        result[md_file.stem] = _load_domain_file(str(md_file))
    return result


def get_domain_prompt_section(domain: str) -> Optional[str]:
    """Build a prompt section with domain knowledge for the LLM.

    Returns ``None`` if no domain documentation is available, so callers
    can skip injection without an extra ``if`` check.
    """
    content = load_domain_context(domain)
    if not content:
        return None
    return (
        "\n\n--- DOMAIN KNOWLEDGE ---\n"
        f"{content}\n"
        "--- END DOMAIN KNOWLEDGE ---\n"
    )
