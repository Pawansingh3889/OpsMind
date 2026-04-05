<div align="center">

# OpsMind

**On-Premises AI Query Tool for Manufacturing Operations**

Query your database in plain English. Runs on your machine with Ollama.
No cloud, no API keys, no data leaves your network.

[![Website](https://img.shields.io/badge/Website-opsmind-0f172a?style=flat-square&logo=googlechrome&logoColor=white)](https://pawansingh3889.github.io/OpsMind/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)]()
[![Tests](https://img.shields.io/badge/Tests-36_passed-22c55e?style=flat-square&logo=pytest&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)]()
[![Ollama](https://img.shields.io/badge/LLM-Ollama-000000?style=flat-square)]()

</div>

---

## Why OpsMind?

Most manufacturing teams query data through Excel exports, IT requests, or expensive BI tools. OpsMind connects directly to your database and lets any operator ask questions in plain English — without sending data to the cloud.

| | OpsMind | Cloud AI Tools | Manual Reporting |
|---|---|---|---|
| Data stays on-premises | **Yes** | No | Yes |
| Natural language queries | **Yes** | Yes | No |
| API costs | **None** | Per-query billing | None |
| Setup time | **< 10 minutes** | Days/weeks | N/A |
| Works offline | **Yes** | No | Yes |
| SQL Server + SQLite | **Both** | Varies | N/A |

### Why direct Ollama — not MCP?

OpsMind calls Ollama's API directly rather than going through an MCP (Model Context Protocol) orchestration layer. This is a deliberate design choice:

- **Fewer moving parts.** The target environment is a factory floor with limited IT support. Direct integration means the dependency chain is just `pip install` + `ollama pull` — no agent framework, no orchestration server, no extra config.
- **Single-user, single-tool.** MCP shines when multiple agents need to share the same database connection or tool registry. OpsMind is a standalone app where one user asks one question at a time. MCP would add complexity without adding value here.
- **Latency.** Every extra hop between the user's question and the LLM adds response time. On 16GB hardware where queries already take 10–25 seconds, keeping the path short matters.

If OpsMind evolves into a multi-agent system (e.g. one agent for SQL, another for document search, another for alerts), MCP would become the right architecture. For now, simplicity wins.

---

## Demo

<div align="center">
<img src="docs/app-preview.png" alt="OpsMind dashboard" width="100%">
</div>

---

## Key Features

<table>
<tr>
<td width="33%" valign="top">

### Natural Language SQL
Type a question. The LLM converts it to SQL, executes it, and explains the result. Pre-built query library handles the 10 most common questions without LLM generation.

</td>
<td width="33%" valign="top">

### Document Search (RAG)
Upload PDFs. ChromaDB indexes them into vector embeddings. Ask questions like "What is the allergen procedure?" and get the relevant paragraph with source citation.

</td>
<td width="33%" valign="top">

### Production Dashboard
Output, waste, yield, and orders visualised with Plotly charts. KPIs update from live database queries. Waste cost shown in GBP.

</td>
</tr>
<tr>
<td width="33%" valign="top">

### Compliance & Traceability
Batch traceability by code. Temperature excursion detection. Allergen matrix generation. Compliance score calculation across all regulated parameters.

</td>
<td width="33%" valign="top">

### Smart Alerts
Checks for: yield drops vs 30-day average, temperature excursions, overtime breaches (Working Time Regulations), expiring stock, order shortfalls.

</td>
<td width="33%" valign="top">

### Excel/CSV Upload
Upload a spreadsheet and ask questions about it. Pandas handles the analysis, the LLM summarises the results. No data leaves your machine.

</td>
</tr>
</table>

---

## Architecture

```
User Question
      │
      ▼
┌─────────────┐     ┌──────────────────┐
│  Query       │────▶│  Pre-built SQL    │──── Match found ───▶ Execute
│  Library     │     │  (10 patterns)    │
└─────────────┘     └──────────────────┘
      │ No match
      ▼
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Schema      │────▶│  Select relevant  │────▶│  LLM (Ollama)│
│  Registry    │     │  tables (4 of 147)│     │  Phi3 / Mistral│
└─────────────┘     └──────────────────┘     └──────────────┘
                                                     │
                                                     ▼
                                              ┌──────────────┐
                                              │  SQLAlchemy   │
                                              │  Execute SQL  │
                                              └──────────────┘
                                                     │
                                              ┌──────┴──────┐
                                              ▼             ▼
                                         Result Table   Plotly Chart
                                              │
                                              ▼
                                         LLM Explains
                                         Result in
                                         Plain English
```

---

## Built With

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge)
![ChromaDB](https://img.shields.io/badge/ChromaDB-4A154B?style=for-the-badge)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)

</div>

| Layer | Tool | Purpose |
|---|---|---|
| LLM | Ollama (Phi3 Mini / Mistral 7B) | Natural language to SQL, result explanation |
| Database | SQLAlchemy | Supports SQLite (demo) and SQL Server (production) |
| Vector Search | ChromaDB + sentence-transformers | PDF document search (RAG) |
| UI | Streamlit | Dashboard, chat interface, charts |
| Charts | Plotly | Interactive production and waste visualisation |
| Data | Pandas | Excel/CSV analysis, data manipulation |
| Config | YAML | Schema registry for mapping business domains to tables |
| Tests | pytest | 36 unit and integration tests |

---

## Quick Start

```bash
# 1. Install Ollama and pull a model
curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3:mini

# 2. Clone, install, and seed
git clone https://github.com/Pawansingh3889/OpsMind.git
cd OpsMind
pip install -r requirements.txt
python scripts/seed_demo_db.py && python scripts/ingest_documents.py

# 3. Run
streamlit run app.py
```

Or use Make:

```bash
make setup    # Install deps + seed demo data
make run      # Start Streamlit app
make test     # Run 36 pytest tests
```

---

## Schema Registry

OpsMind handles large databases (100+ tables) by mapping business domains to specific tables. When you ask about "orders", only order-related tables are sent to the LLM — not all 147.

```yaml
# schema.yaml — 7 business domains
traceability:
  tables:
    ProductionBatch: BatchID, BatchNo, ProductCode, ProductionDate
    RawMaterialIntake: IntakeID, ProductCode, BatchNo, SupplierCode

production:
  tables:
    ProductionRuns: RunID, ProductCode, FinishedOutputKg, WasteKg

# Also: orders, temperature, staff, stock, compliance
```

---

## Demo Database

The seed script creates 60 days of synthetic manufacturing data:

| Table | Records | Content |
|---|---|---|
| Products | 10 | Fish and food products with allergen data |
| Production runs | 662 | Daily output, waste, yield percentages |
| Sales orders | 451 | Customer orders with delivery dates |
| Temperature logs | 3,600 | Cold chain monitoring (every 30 min) |
| Raw materials | 282 | Supplier intake with batch traceability |
| Staff records | 11 | Shift patterns and working hours |

---

## SQL Server Connection

```bash
# Connection string via environment variable
OPSMIND_DB=mssql+pyodbc://user:pass@server/database?driver=ODBC+Driver+17+for+SQL+Server

# Windows Authentication
OPSMIND_DB=mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
```

Edit `schema.yaml` to map your actual table names to OpsMind's 7 business domains.

---

## Tests

```
$ python -m pytest tests/test_core.py -v

tests/test_core.py::TestConfig::test_config_loads               PASSED
tests/test_core.py::TestSQLDialect::test_days_ago_sqlite         PASSED
tests/test_core.py::TestSchemaRegistry::test_detect_domain        PASSED
tests/test_core.py::TestDatabase::test_query_returns_dataframe    PASSED
tests/test_core.py::TestCompliance::test_trace_batch              PASSED
tests/test_core.py::TestAlerts::test_check_all_alerts             PASSED
tests/test_core.py::TestWastePredictor::test_predict_waste        PASSED
tests/test_core.py::TestSQLAgentSafety::test_blocks_insert        PASSED
tests/test_core.py::TestDocSearch::test_search_returns_list        PASSED
... 27 more tests

36 passed, 0 failed
```

Covers: configuration, SQL dialect abstraction, schema registry, database queries, compliance checks, alert detection, waste prediction, SQL injection prevention, document search.

---

## Project Structure

```
OpsMind/
├── app.py                        # Streamlit app (7 tabs)
├── config.py                     # Configuration and environment
├── schema.yaml                   # Business domain → table mapping
├── Makefile                      # setup, run, test, clean commands
├── requirements.txt              # Python dependencies
│
├── modules/
│   ├── sql_agent.py              # NL → SQL + pre-built query fallback
│   ├── query_library.py          # 10 tested SQL patterns
│   ├── schema_registry.py        # Domain detection (7 domains, 150 tables)
│   ├── sql_dialect.py            # SQLite / SQL Server abstraction layer
│   ├── database.py               # SQLAlchemy connection management
│   ├── doc_search.py             # ChromaDB RAG pipeline
│   ├── compliance.py             # Batch tracing, allergens, audit scoring
│   ├── alerts.py                 # 5 anomaly detection alert types
│   ├── waste_predictor.py        # Yield trends and waste forecasting
│   ├── excel_agent.py            # Spreadsheet upload and analysis
│   └── llm.py                    # Ollama LLM connection
│
├── tests/
│   └── test_core.py              # 36 pytest tests (unit + integration)
│
├── scripts/
│   ├── seed_demo_db.py           # Demo database generator (5,000+ records)
│   └── ingest_documents.py       # PDF document loader for RAG
│
├── docs/
│   ├── index.html                # Landing page (GitHub Pages)
│   └── app-preview.png           # Application screenshot
│
├── .github/
│   └── workflows/
│       └── tests.yml             # CI: pytest on push/PR
│
├── CONTRIBUTING.md
└── LICENSE
```

---

## Roadmap

- [x] Natural language to SQL with Ollama
- [x] Pre-built query library (10 patterns)
- [x] Schema registry for large databases
- [x] ChromaDB document search (RAG)
- [x] Production and waste dashboard
- [x] Compliance module (traceability, allergens, temperature)
- [x] Smart alerts (5 types)
- [x] Excel/CSV upload and analysis
- [x] SQLite and SQL Server support
- [x] 36 pytest tests
- [x] Password authentication (Streamlit secrets)
- [x] Query caching (5-minute TTL on SQL results + cached DB engine)
- [ ] Scheduled report generation
- [ ] Slack/Teams alert forwarding
- [ ] GPU-accelerated inference support
- [ ] Production database validation suite

---

## Known Limitations

| Area | Detail |
|---|---|
| LLM accuracy | ~60% on novel complex queries. Pre-built library handles the 10 most common questions reliably. |
| Response time | 10–25 seconds per query on 16GB RAM. The LLM is the bottleneck. |
| Authentication | Password-based via Streamlit secrets. Configure in `.streamlit/secrets.toml`. No multi-user roles. |
| Write protection | Read-only. Only SELECT queries are permitted — INSERT, UPDATE, DELETE are blocked. |
| Demo data | Ships with synthetic data. Not validated against production manufacturing databases. |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. Issues and pull requests are welcome.

---

<div align="center">

**[Documentation](https://pawansingh3889.github.io/OpsMind/)** · **[Report Bug](https://github.com/Pawansingh3889/OpsMind/issues)** · **[Request Feature](https://github.com/Pawansingh3889/OpsMind/issues)**

---

### Built by [Pawan Singh Kapkoti](https://pawansingh3889.github.io)

Data & Analytics Engineer · Available for freelance and full-time roles.

[![Hire Me](https://img.shields.io/badge/Hire_Me-22c55e?style=for-the-badge)](mailto:pawankapkoti3889@gmail.com) [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/pawan-singh-kapkoti-100176347) [![Upwork](https://img.shields.io/badge/Upwork-6fda44?style=for-the-badge&logo=upwork&logoColor=white)](https://www.upwork.com/freelancers/pawansingh3889) [![Blueprint](https://img.shields.io/badge/OpsMind_Blueprint-f59e0b?style=for-the-badge&logo=bookstack&logoColor=white)](https://pawankapko.gumroad.com/l/opsmind-blueprint-local-ai-manufacturing)

</div>
