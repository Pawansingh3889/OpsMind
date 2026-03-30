"""Natural language to SQL query agent."""
import sqlite3
import pandas as pd
from modules.llm import get_response
from config import DATABASE_URL


SQL_SYSTEM_PROMPT = """Convert questions to SQLite SQL. Return ONLY the SQL, nothing else.

TABLES:
products(id,name,species,category,unit_cost_per_kg,sell_price_per_kg,allergens)
raw_materials(id,product_id,batch_code,supplier,quantity_kg,received_date,expiry_date,temperature_on_arrival)
production(id,product_id,batch_code,date,raw_input_kg,finished_output_kg,waste_kg,yield_pct,line_number,shift,operator)
orders(id,customer,product_id,quantity_kg,order_date,delivery_date,status,price_per_kg)
waste_log(id,production_id,waste_type,quantity_kg,reason,date)
temp_logs(id,location,temperature,recorded_at,recorded_by)
staff(id,name,role,shift_pattern,hours_this_week,hourly_rate)

RULES: SQLite syntax. JOIN products for names. today=date('now'). this week=date('now','-7 days'). Add ORDER BY+LIMIT. ONLY return SQL."""


EXPLAIN_SYSTEM_PROMPT = """Explain these SQL results to a factory manager in 2-3 sentences. Use GBP and kg. Flag problems. Be concise."""


def get_db_path():
    """Extract SQLite path from DATABASE_URL."""
    url = DATABASE_URL
    if url.startswith('sqlite:///'):
        return url.replace('sqlite:///', '')
    return 'data/demo.db'


def run_query(question):
    """Convert natural language to SQL, execute, and explain results."""
    # Step 1: Generate SQL
    sql = get_response(question, system_prompt=SQL_SYSTEM_PROMPT)

    # Clean the SQL (remove markdown formatting if present)
    sql = sql.strip()
    if sql.startswith('```'):
        sql = sql.split('\n', 1)[1] if '\n' in sql else sql[3:]
    if sql.endswith('```'):
        sql = sql[:-3]
    sql = sql.strip()
    if sql.lower().startswith('sql'):
        sql = sql[3:].strip()

    # Safety check — only allow SELECT
    if not sql.upper().strip().startswith('SELECT'):
        return {
            'sql': sql,
            'data': None,
            'explanation': 'For safety, OpsMind only runs SELECT queries. Please rephrase your question.',
            'error': True
        }

    # Step 2: Execute SQL
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql, conn)
        conn.close()
    except Exception as e:
        return {
            'sql': sql,
            'data': None,
            'explanation': f'SQL error: {e}. The AI may have generated incorrect SQL. Try rephrasing your question.',
            'error': True
        }

    # Step 3: Explain results
    if df.empty:
        explanation = 'No data found for your query. Try adjusting the date range or product name.'
    else:
        data_summary = df.head(20).to_string()
        explain_prompt = f"Question: {question}\n\nSQL Query: {sql}\n\nResults:\n{data_summary}\n\nExplain these results to a factory manager:"
        explanation = get_response(explain_prompt, system_prompt=EXPLAIN_SYSTEM_PROMPT)

    return {
        'sql': sql,
        'data': df,
        'explanation': explanation,
        'error': False
    }
