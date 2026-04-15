"""LangGraph multi-step agent for structured NL-to-SQL query flow.

Implements a state graph with 6 nodes:
  1. detect_domain   -- identifies the business domain from the question
  2. check_library   -- checks pre-built query library for a fast-path match
  3. generate_sql    -- LLM generates SQL if no library match found
  4. validate_sql    -- schema-aware safety check via sql_validator
  5. execute_sql     -- runs the query via database.query()
  6. explain_results -- LLM explains results in plain business terms

Edge logic:
  - If library match found, skip generate_sql and go straight to execute_sql.
  - If validation fails, short-circuit to error state.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from modules import database
from modules.llm import get_response
from modules.query_library import find_matching_query
from modules.schema_registry import detect_domain, get_prompt_for_question
from modules.sql_validator import validate_sql

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    question: str
    domain: str
    sql: str
    results: object  # pandas DataFrame or None
    explanation: str
    error: str


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

EXPLAIN_PROMPT = (
    "Explain these SQL results to a manager in 2-3 sentences. "
    "Use GBP and kg. Flag problems. Be concise."
)

def detect_domain_node(state: AgentState) -> AgentState:
    """Node 1: Detect the business domain from the user question."""
    domain = detect_domain(state["question"])
    return {"domain": domain}


def check_library_node(state: AgentState) -> AgentState:
    """Node 2: Check the pre-built query library for a fast-path match."""
    sql, _desc = find_matching_query(state["question"])
    if sql:
        return {"sql": sql.strip()}
    return {}


def generate_sql_node(state: AgentState) -> AgentState:
    """Node 3: Generate SQL via the LLM when no library match exists."""
    sql_prompt = get_prompt_for_question(state["question"])
    sql = get_response(state["question"], system_prompt=sql_prompt)

    # Clean markdown fences the LLM sometimes wraps around SQL
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    sql = sql.strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()

    return {"sql": sql}


def validate_sql_node(state: AgentState) -> AgentState:
    """Node 4: Schema-aware safety gate using sql_validator.

    Checks statement type, injection patterns, table/column existence,
    and enforces a row limit.
    """
    sql = state.get("sql", "")

    try:
        known_tables = database.discover_tables()
    except Exception:
        log.warning("Could not discover tables; skipping schema validation")
        known_tables = None

    result = validate_sql(
        sql,
        known_tables=known_tables,
        column_resolver=database.discover_columns,
    )

    if result.warnings:
        log.warning("SQL validation warnings: %s", result.warnings)

    if not result.is_valid:
        return {"error": result.error_message}

    # Use the (possibly amended) SQL with row-limit enforced
    return {"sql": result.sql}


def execute_sql_node(state: AgentState) -> AgentState:
    """Node 5: Execute the validated SQL query."""
    try:
        df = database.query(state["sql"])
        return {"results": df}
    except Exception as exc:
        return {
            "results": None,
            "error": f"SQL error: {exc}. Try rephrasing your question.",
        }


def explain_results_node(state: AgentState) -> AgentState:
    """Node 6: LLM explains the query results in business terms."""
    df = state.get("results")
    if df is None or (hasattr(df, "empty") and df.empty):
        return {
            "explanation": "No data found. Try adjusting the date range or search terms.",
        }

    data_summary = df.head(20).to_string()
    prompt = (
        f"Question: {state['question']}\n\n"
        f"SQL: {state.get('sql', '')}\n\n"
        f"Results:\n{data_summary}\n\n"
        "Explain:"
    )
    explanation = get_response(prompt, system_prompt=EXPLAIN_PROMPT)
    return {"explanation": explanation}


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def _after_check_library(state: AgentState) -> str:
    """If the library returned SQL, skip LLM generation."""
    if state.get("sql"):
        return "validate_sql"
    return "generate_sql"


def _after_validate_sql(state: AgentState) -> str:
    """If validation set an error, stop. Otherwise execute."""
    if state.get("error"):
        return END
    return "execute_sql"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph():
    """Construct and compile the LangGraph state graph.

    Flow:
        detect_domain -> check_library
                            |
                    (match?) |--- yes ---> validate_sql
                            |--- no  ---> generate_sql -> validate_sql
                                                            |
                                                   (valid?) |--- no  ---> END (error)
                                                            |--- yes ---> execute_sql -> explain_results -> END
    """
    graph = StateGraph(AgentState)

    # -- nodes ---------------------------------------------------------------
    graph.add_node("detect_domain", detect_domain_node)
    graph.add_node("check_library", check_library_node)
    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("explain_results", explain_results_node)

    # -- edges ---------------------------------------------------------------
    graph.set_entry_point("detect_domain")
    graph.add_edge("detect_domain", "check_library")

    # Conditional: library hit skips LLM generation
    graph.add_conditional_edges("check_library", _after_check_library)

    graph.add_edge("generate_sql", "validate_sql")

    # Conditional: validation failure short-circuits to END
    graph.add_conditional_edges("validate_sql", _after_validate_sql)

    graph.add_edge("execute_sql", "explain_results")
    graph.add_edge("explain_results", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ask(question: str) -> dict:
    """Ask a production question using the LangGraph agent."""
    graph = build_graph()
    result = graph.invoke({"question": question})
    return result
