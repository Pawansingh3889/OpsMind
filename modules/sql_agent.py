"""Natural language to SQL query agent. Supports SQLite and SQL Server."""
import pandas as pd
from sqlalchemy import create_engine, text
from modules.llm import get_response
from config import DATABASE_URL, DB_TYPE


# Dynamic system prompt based on database type
def _get_sql_prompt():
    if DB_TYPE == "mssql":
        return """Convert questions to T-SQL (SQL Server). Return ONLY the SQL, nothing else.

RULES: T-SQL syntax. JOIN tables for names. today=CAST(GETDATE() AS DATE). this week=DATEADD(day,-7,GETDATE()). Add ORDER BY. Use TOP instead of LIMIT. ONLY return the SQL query.

If you do not know the table names, start with: SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"""
    else:
        return """Convert questions to SQLite SQL. Return ONLY the SQL, nothing else.

TABLES:
products(id,name,species,category,unit_cost_per_kg,sell_price_per_kg,allergens)
raw_materials(id,product_id,batch_code,supplier,quantity_kg,received_date,expiry_date,temperature_on_arrival)
production(id,product_id,batch_code,date,raw_input_kg,finished_output_kg,waste_kg,yield_pct,line_number,shift,operator)
orders(id,customer,product_id,quantity_kg,order_date,delivery_date,status,price_per_kg)
waste_log(id,production_id,waste_type,quantity_kg,reason,date)
temp_logs(id,location,temperature,recorded_at,recorded_by)
staff(id,name,role,shift_pattern,hours_this_week,hourly_rate)

RULES: SQLite syntax. JOIN products for names. today=date('now'). this week=date('now','-7 days'). Add ORDER BY+LIMIT. ONLY return SQL."""


EXPLAIN_SYSTEM_PROMPT = """Explain these SQL results to a manager in 2-3 sentences. Use GBP and kg. Flag problems. Be concise."""


# Database engine (cached)
_engine = None


def _get_engine():
    """Get or create SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False)
    return _engine


def get_tables():
    """List all tables in the connected database."""
    engine = _get_engine()
    if DB_TYPE == "mssql":
        query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
    else:
        query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    try:
        df = pd.read_sql(query, engine)
        return df.iloc[:, 0].tolist()
    except Exception:
        return []


def run_query(question):
    """Convert natural language to SQL, execute, and explain results."""
    # Step 1: Generate SQL
    prompt = _get_sql_prompt()

    # For SQL Server, include actual table names in the prompt
    if DB_TYPE == "mssql":
        tables = get_tables()
        if tables:
            prompt += f"\n\nAVAILABLE TABLES: {', '.join(tables)}"

    sql = get_response(question, system_prompt=prompt)

    # Clean the SQL (remove markdown formatting if present)
    sql = sql.strip()
    if sql.startswith('```'):
        sql = sql.split('\n', 1)[1] if '\n' in sql else sql[3:]
    if sql.endswith('```'):
        sql = sql[:-3]
    sql = sql.strip()
    if sql.lower().startswith('sql'):
        sql = sql[3:].strip()

    # Safety check — only allow SELECT and WITH (CTEs)
    first_word = sql.upper().strip().split()[0] if sql.strip() else ''
    if first_word not in ('SELECT', 'WITH'):
        return {
            'sql': sql,
            'data': None,
            'explanation': 'For safety, OpsMind only runs read-only queries (SELECT). Please rephrase your question.',
            'error': True
        }

    # Block dangerous keywords even inside SELECT
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 'EXEC', 'EXECUTE', 'xp_', 'sp_']
    sql_upper = sql.upper()
    for kw in dangerous:
        if kw in sql_upper:
            return {
                'sql': sql,
                'data': None,
                'explanation': f'Blocked: query contains "{kw}". OpsMind is read-only for safety.',
                'error': True
            }

    # Step 2: Execute SQL
    try:
        engine = _get_engine()
        df = pd.read_sql(sql, engine)
    except Exception as e:
        return {
            'sql': sql,
            'data': None,
            'explanation': f'SQL error: {e}. Try rephrasing your question.',
            'error': True
        }

    # Step 3: Explain results
    if df.empty:
        explanation = 'No data found for your query. Try adjusting the date range or search terms.'
    else:
        data_summary = df.head(20).to_string()
        explain_prompt = f"Question: {question}\n\nSQL Query: {sql}\n\nResults:\n{data_summary}\n\nExplain these results:"
        explanation = get_response(explain_prompt, system_prompt=EXPLAIN_SYSTEM_PROMPT)

    return {
        'sql': sql,
        'data': df,
        'explanation': explanation,
        'error': False
    }
