# OpsMind Agent Graph Specification

## Overview

OpsMind uses a 6-node LangGraph state graph to convert natural language questions into validated SQL queries against a manufacturing database. The graph prioritises pre-built queries for speed and correctness, falling back to LLM-generated SQL when no match exists.

## State

```python
class AgentState(TypedDict, total=False):
    question: str
    domain: str
    sql: str
    results: object       # pandas DataFrame or None
    explanation: str
    error: str
```

## Nodes

### 1. detect_domain
- **Purpose**: Identify which business domain the question belongs to
- **Input**: `question`
- **Output**: `domain` (one of: production, waste, orders, compliance, staff, stock, traceability)
- **Logic**: Scores the question against keyword lists in `schema_registry.DOMAIN_KEYWORDS`
- **Error handling**: Returns "general" if no domain scores above threshold

### 2. check_library
- **Purpose**: Check pre-built query library for a fast-path match
- **Input**: `question`
- **Output**: `sql` (if match found) or empty dict
- **Logic**: Regex pattern matching against 20 pre-built queries
- **Edge condition**: If SQL is returned, route skips `generate_sql` and goes directly to `validate_sql`

### 3. generate_sql
- **Purpose**: Use LLM to generate SQL from natural language
- **Input**: `question`, `domain`
- **Output**: `sql`
- **Logic**: Builds a domain-scoped prompt via `schema_registry.get_prompt_for_question()`, sends to Ollama, cleans markdown fences from response
- **Only reached**: When `check_library` returns no match

### 4. validate_sql
- **Purpose**: Safety gate before execution
- **Input**: `sql`
- **Output**: `error` (if validation fails) or amended `sql` (with LIMIT added)
- **Logic**: Calls `sql_validator.validate_sql()` which checks:
  - Statement type (SELECT/WITH only)
  - Injection patterns (tautologies, UNION, comments, stacked queries)
  - Table existence against live schema
  - Column existence against live schema
  - Adds LIMIT if missing
- **Edge condition**: If error is set, route goes to END (short-circuit)

### 5. execute_sql
- **Purpose**: Run the validated query
- **Input**: `sql`
- **Output**: `results` (DataFrame) or `error`
- **Logic**: Calls `database.query(sql)`
- **Error handling**: Catches all exceptions, returns user-friendly error message

### 6. explain_results
- **Purpose**: LLM explains query results in business terms
- **Input**: `question`, `sql`, `results`
- **Output**: `explanation`
- **Logic**: Sends top 20 rows to LLM with the EXPLAIN_PROMPT (concise, GBP/kg units, flag problems)

## Routing

```
detect_domain -> check_library
                    |
            (match?) |--- yes --> validate_sql
                    |--- no  --> generate_sql -> validate_sql
                                                    |
                                           (valid?) |--- no  --> END (error)
                                                    |--- yes --> execute_sql -> explain_results -> END
```
