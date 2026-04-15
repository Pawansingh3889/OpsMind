# MCP Server Architecture

## Overview

OpsMind exposes database operations and document search as MCP (Model Context Protocol) servers. This decouples data access from agent logic, allowing tools to be shared across agents and replaced independently.

Based on patterns from PyCon DE 2026: "Building Agentic Systems with LangGraph, MCP, and A2A" (Nosekabel).

## Servers

### Database Server (port 9000)

**Module**: `mcp_servers/database_server.py`
**Config**: `MCP_DB_HOST`, `MCP_DB_PORT`

| Tool | Parameters | Returns |
|------|-----------|---------|
| `query_database` | `sql: str` | Query results as JSON |
| `discover_tables` | none | List of table names |
| `discover_columns` | `table_name: str` | List of column names |
| `get_schema_for_domain` | `domain: str` | Tables and columns for the domain |

All queries are read-only. The server delegates to `modules/database.py` internally.

### Document Search Server (port 9001)

**Module**: `mcp_servers/doc_search_server.py`
**Config**: `MCP_DOC_HOST`, `MCP_DOC_PORT`

| Tool | Parameters | Returns |
|------|-----------|---------|
| `search_documents` | `query: str, top_k: int` | Matching document chunks |
| `get_document_count` | none | Total chunks in vector store |
| `get_domain_context` | `domain: str` | Domain-specific documentation |

Supports both ChromaDB and pgvector backends via `config.VECTOR_DB` setting.

## Fallback Behaviour

When `MCP_ENABLED=false` (default), OpsMind calls modules directly. When `MCP_ENABLED=true`, the client in `modules/mcp_client.py` connects to the MCP servers. If a server is unreachable, the client falls back to direct module calls and logs a warning.

This means OpsMind works identically with or without MCP infrastructure.

## Running

```bash
# Start servers
python -m mcp_servers.database_server
python -m mcp_servers.doc_search_server

# Enable MCP in OpsMind
MCP_ENABLED=true streamlit run app.py
```
