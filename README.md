# OpsMind — The AI Brain for Your Factory

On-premises AI assistant for food processing factories. Ask questions in plain English, get instant answers from your SQL database, documents, and spreadsheets. Zero cloud costs, zero data leakage.

## Demo

```bash
# 1. Install Ollama (https://ollama.com) and pull a model
ollama pull mistral

# 2. Clone and install
git clone https://github.com/Pawansingh3889/OpsMind.git
cd OpsMind
pip install -r requirements.txt

# 3. Seed demo data
python scripts/seed_demo_db.py
python scripts/ingest_documents.py

# 4. Run
streamlit run app.py
```

## What Can It Do?

**Ask in plain English:**
- "How much salmon did we process today?"
- "Show me top 5 products by waste this week"
- "What's the allergen procedure for cod?"
- "Trace batch PR-260329-1 from catch to customer"
- "Can we fulfil tomorrow's Lidl order?"

**Features:**
- SQL Agent — natural language to SQL queries on your production database
- Document Search — semantic search over SOPs, HACCP plans, customer specs
- Excel/CSV Analysis — upload and analyse production reports
- Waste Prediction — predict waste and optimise yields
- Compliance Dashboard — BRC/HACCP audit prep, traceability, allergen matrix
- Smart Alerts — yield drops, temperature excursions, overtime, expiring stock
- Multi-Language — workers ask in their language

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| LLM | Ollama (Mistral 7B) | Free |
| SQL Agent | LangChain + SQLAlchemy | Free |
| Document Search | ChromaDB + sentence-transformers | Free |
| UI | Streamlit | Free |
| Database | SQLite / PostgreSQL | Free |

**Total infrastructure cost: 0**

## Why OpsMind?

- **On-premises** — your data never leaves your building
- **Food-specific** — understands yield, waste, BRC, HACCP out of the box
- **Multilingual** — Polish, Lithuanian, Romanian, Hindi workers can ask in their language
- **Free** — no API costs, no subscriptions, no cloud

## Author

Built by a team that understands factory operations from the inside. MSc Data Analytics. Real factory floor experience.
