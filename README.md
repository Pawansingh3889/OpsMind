# OpsMind

On-premises tool that connects to a SQL database and lets you ask questions in plain English. Uses a local LLM via Ollama. No cloud, no API costs, no data leaves your machine.

**[Documentation](https://pawansingh3889.github.io/OpsMind)**

## What it does

- **Natural language SQL** — type a question, get a query result and explanation
- **Document search (RAG)** — upload PDFs, search by meaning using ChromaDB
- **Dashboard** — production, waste, yield, and order charts (Plotly)
- **Compliance** — batch traceability, temperature excursions, allergen matrix
- **Smart alerts** — yield drops, overtime breaches, expiring stock, order shortfalls
- **Excel/CSV analysis** — upload a spreadsheet, ask questions about it
- **Schema registry** — maps business domains to tables (handles 100+ table databases)
- **Pre-built query library** — 10 common questions mapped to tested SQL

## Tech stack

| Component | Tool |
|---|---|
| LLM | Ollama (Phi3 Mini / Mistral 7B) |
| Database | SQLAlchemy (SQLite or SQL Server) |
| Vector Search | ChromaDB + sentence-transformers |
| UI | Streamlit |
| Charts | Plotly |
| Data | Pandas |
| Tests | pytest (36 tests) |

## Setup

```bash
# Install Ollama from https://ollama.com
ollama pull phi3:mini

# Clone and install
git clone https://github.com/Pawansingh3889/OpsMind.git
cd OpsMind
pip install -r requirements.txt

# Create demo database
python scripts/seed_demo_db.py
python scripts/ingest_documents.py

# Run
streamlit run app.py
```

## Demo database

The seed script creates 60 days of synthetic data:

| Table | Records |
|---|---|
| Products | 10 |
| Production runs | 662 |
| Orders | 451 |
| Temperature logs | 3,600 |
| Raw materials | 282 |
| Staff | 11 |

## SQL Server connection

```bash
# Set environment variable
OPSMIND_DB=mssql+pyodbc://user:pass@server/database?driver=ODBC+Driver+17+for+SQL+Server

# Or Windows Auth
OPSMIND_DB=mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

Edit `schema.yaml` to map your table names to OpsMind's 7 business domains.

## Tests

```
$ python -m pytest tests/test_core.py -v
36 passed, 0 failed
```

Covers: config, SQL dialect, schema registry, database queries, compliance, alerts, waste predictor, SQL safety checks, document search.

## Project structure

```
OpsMind/
├── app.py                    # Streamlit app (7 tabs)
├── config.py                 # Configuration
├── schema.yaml               # Table mapping for large databases
├── modules/
│   ├── sql_agent.py          # NL to SQL + pre-built query fallback
│   ├── query_library.py      # 10 tested SQL patterns
│   ├── schema_registry.py    # Domain-to-table mapping
│   ├── sql_dialect.py        # SQLite / SQL Server abstraction
│   ├── database.py           # SQLAlchemy connection
│   ├── doc_search.py         # ChromaDB RAG
│   ├── compliance.py         # Traceability, allergens, audit
│   ├── alerts.py             # 5 alert types
│   ├── waste_predictor.py    # Yield and waste analysis
│   └── llm.py                # Ollama connection
├── tests/
│   └── test_core.py          # 36 pytest tests
├── scripts/
│   ├── seed_demo_db.py       # Demo database generator
│   └── ingest_documents.py   # Sample document loader
└── requirements.txt
```

## Known limitations

- LLM generates incorrect SQL for complex queries (~40% error rate on novel questions)
- 10-25 second response time on 16GB RAM
- No authentication (single-user / trusted network)
- Read-only (SELECT queries only)
- Demo data is synthetic, not tested on production databases
