# OpsMind — architecture at a glance

A single-screen view of how an operator question becomes an answer,
fully on-premises. GitHub renders the Mermaid below; for the full
detail see [`architecture.md`](architecture.md) and the decision
records in [`adr/`](adr/).

## Query flow

```mermaid
flowchart TD
    OP["Operator question<br/>(natural language)"] --> UI["Streamlit UI"]
    UI --> AGENT

    subgraph HOST["Factory laptop — Windows host"]
        subgraph DOCKER["Docker / WSL2 (Linux, isolated)"]
            subgraph AGENT["LangGraph agent (6 nodes)"]
                DOMAIN["1. detect domain"] --> LIB["2. library match?"]
                LIB -->|hit| VAL
                LIB -->|miss| GEN["3. generate SQL"]
                GEN --> VAL["4. validate SQL"]
                VAL --> EXEC["5. execute"]
                EXEC --> EXPLAIN["6. explain"]
            end
            OLLAMA["Ollama + Gemma 3 12B<br/>(no internet egress)"]
            GUARD["sql-guard + validator<br/>(4-layer read-only)"]
            RAG["ChromaDB / pgvector<br/>(SOP & HACCP docs)"]
        end
    end

    GEN -.->|prompt| OLLAMA
    EXPLAIN -.->|summarise| OLLAMA
    VAL -.->|static analysis| GUARD
    DOMAIN -.->|context| RAG

    EXEC -->|SELECT only| REPLICA["Read-only replica<br/>(SQL Server / PostgreSQL)"]
    REPLICA -.->|async replication| PRIMARY["Production primary<br/>OCM · SI scales · ERP<br/>(OpsMind never connects here)"]

    EXPLAIN --> ANSWER["Answer to operator"]

    style PRIMARY fill:#fee,stroke:#c00,stroke-width:2px
    style OLLAMA fill:#eef,stroke:#33c
    style GUARD fill:#efe,stroke:#3a3
    style REPLICA fill:#ffe,stroke:#aa0
```

## The four read-only layers

```mermaid
flowchart LR
    SQL["Generated SQL"] --> L3
    L3["L3 · sql-guard<br/>static analysis"] --> L4
    L4["L4 · validator<br/>2nd parser + row cap"] --> L2
    L2["L2 · ApplicationIntent<br/>ReadOnly / replica DSN"] --> L1
    L1["L1 · DB grants<br/>DENY write verbs"] --> DB[("Read-only<br/>replica")]

    style L1 fill:#efe,stroke:#3a3
    style L2 fill:#efe,stroke:#3a3
    style L3 fill:#efe,stroke:#3a3
    style L4 fill:#efe,stroke:#3a3
```

Any one layer alone blocks a write; a write would have to defeat all
four. L1 is enforced by the database engine, L2 by the connection
topology, L3 and L4 by OpsMind using two different parsers — so a
parsing gap in one cannot pass through the other. See
[ADR 0002](adr/0002-four-layer-read-only.md) for the reasoning.
