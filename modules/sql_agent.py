"""Natural language to SQL query agent. Uses schema registry + pre-built query library."""
import pandas as pd
from sqlalchemy import text
from modules.llm import get_response
from modules.database import get_engine
from modules.schema_registry import get_prompt_for_question
from modules.query_library import find_matching_query


EXPLAIN_PROMPT = """Explain these SQL results to a manager in 2-3 sentences. Use GBP and kg. Flag problems. Be concise."""


def run_query(question):
    """Convert natural language to SQL, execute, and explain results."""
    # Step 0: Check pre-built query library first (guaranteed correct SQL)
    prebuilt_sql, prebuilt_desc = find_matching_query(question)
    if prebuilt_sql:
        sql = prebuilt_sql.strip()
        try:
            engine = get_engine()
            df = pd.read_sql(sql, engine)
            if df.empty:
                explanation = f'{prebuilt_desc}. No data found for the current period.'
            else:
                data_summary = df.head(20).to_string()
                prompt = f"Question: {question}\n\nResults:\n{data_summary}\n\nExplain:"
                explanation = get_response(prompt, system_prompt=EXPLAIN_PROMPT)
            return {'sql': sql, 'data': df, 'explanation': explanation, 'error': False}
        except Exception as e:
            return {'sql': sql, 'data': None, 'explanation': f'Query error: {e}', 'error': True}

    # Step 1: No pre-built match — use LLM to generate SQL
    sql_prompt = get_prompt_for_question(question)
    sql = get_response(question, system_prompt=sql_prompt)

    # Clean markdown formatting
    sql = sql.strip()
    if sql.startswith('```'):
        sql = sql.split('\n', 1)[1] if '\n' in sql else sql[3:]
    if sql.endswith('```'):
        sql = sql[:-3]
    sql = sql.strip()
    if sql.lower().startswith('sql'):
        sql = sql[3:].strip()

    # Safety: only allow SELECT and WITH (CTEs)
    first_word = sql.upper().strip().split()[0] if sql.strip() else ''
    if first_word not in ('SELECT', 'WITH'):
        return {
            'sql': sql,
            'data': None,
            'explanation': 'For safety, OpsMind only runs read-only queries (SELECT). Please rephrase your question.',
            'error': True
        }

    # Block dangerous keywords
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE', 'xp_', 'sp_']
    sql_upper = sql.upper()
    for kw in dangerous:
        if kw in sql_upper:
            return {
                'sql': sql,
                'data': None,
                'explanation': f'Blocked: query contains "{kw}". OpsMind is read-only.',
                'error': True
            }

    # Step 3: Execute
    try:
        engine = get_engine()
        df = pd.read_sql(sql, engine)
    except Exception as e:
        return {
            'sql': sql,
            'data': None,
            'explanation': f'SQL error: {e}. Try rephrasing your question.',
            'error': True
        }

    # Step 4: Explain
    if df.empty:
        explanation = 'No data found. Try adjusting the date range or search terms.'
    else:
        data_summary = df.head(20).to_string()
        prompt = f"Question: {question}\n\nSQL: {sql}\n\nResults:\n{data_summary}\n\nExplain:"
        explanation = get_response(prompt, system_prompt=EXPLAIN_PROMPT)

    return {
        'sql': sql,
        'data': df,
        'explanation': explanation,
        'error': False
    }
