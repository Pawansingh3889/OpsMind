# OpsMind

On-premises AI assistant for food manufacturing. Natural language to SQL, RAG document search, compliance dashboards.

Runs entirely on Ollama. No data leaves the building.

\`\`\`
stack     = ["Python", "Ollama", "ChromaDB", "LangChain", "Streamlit", "SQLAlchemy", "Kafka"]
tests     = 36
ai_model  = "local"
\`\`\`

[Documentation](https://pawansingh3889.github.io/OpsMind/)

---

## What it does

**NL-to-SQL** — ask questions in plain English, get SQL executed against your production database

**RAG Search** — upload SOPs and HACCP plans, search with natural language via ChromaDB

**Kafka Streaming** — real-time sensor data consumer with threshold-based alerting

---

## Quick start

\`\`\`bash
pip install -r requirements.txt
ollama pull llama3.1
streamlit run app.py
\`\`\`

## Why on-prem?

Food manufacturing is regulated. Sending production data to cloud APIs is a compliance risk. Ollama runs locally.
