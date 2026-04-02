"""Waste prediction and yield optimization."""
import pandas as pd
from modules.database import query as db_query
from modules.llm import get_response

def get_yield_trends(days=30, product_name=None):
    """Get yield trends over time."""
    from modules.sql_dialect import days_ago
    sql = f"""
    SELECT p.date, pr.name as product, p.yield_pct,
               p.raw_input_kg, p.finished_output_kg, p.waste_kg
    FROM production p
    JOIN products pr ON p.product_id = pr.id
    WHERE p.date >= {days_ago(days)}
    """
    if product_name:
        sql += f" AND pr.name LIKE '%{product_name}%'"
    sql += ' ORDER BY p.date'
    return db_query(sql)

def get_waste_summary(days=7):
    """Get waste breakdown by type and reason."""
    from modules.sql_dialect import days_ago
    return db_query(f"""
    SELECT w.waste_type, w.reason, SUM(w.quantity_kg) as total_kg,
               COUNT(*) as occurrences, pr.name as product
    FROM waste_log w
    JOIN production p ON w.production_id = p.id
    JOIN products pr ON p.product_id = pr.id
    WHERE w.date >= {days_ago(days)}
    GROUP BY w.waste_type, w.reason, pr.name
    ORDER BY total_kg DESC
    """)

def get_yield_by_product(days=30):
    """Get average yield by product."""
    from modules.sql_dialect import days_ago
    return db_query(f"""
    SELECT pr.name as product, pr.category,
               ROUND(AVG(p.yield_pct), 1) as avg_yield,
               ROUND(MIN(p.yield_pct), 1) as min_yield,
               ROUND(MAX(p.yield_pct), 1) as max_yield,
               ROUND(SUM(p.waste_kg), 1) as total_waste_kg,
               ROUND(SUM(p.waste_kg) * pr.unit_cost_per_kg, 2) as waste_cost_gbp,
               COUNT(*) as runs
    FROM production p
    JOIN products pr ON p.product_id = pr.id
    WHERE p.date >= {days_ago(days)}
    GROUP BY pr.name, pr.category, pr.unit_cost_per_kg
    ORDER BY avg_yield ASC
    """)

def predict_waste(product_name, input_kg):
    """Predict expected waste for a production run based on historical data."""
    from modules.sql_dialect import days_ago
    df = db_query(f'''
    SELECT AVG(p.yield_pct) as avg_yield,
               AVG(p.waste_kg / p.raw_input_kg) as avg_waste_ratio
    FROM production p
    JOIN products pr ON p.product_id = pr.id
    WHERE pr.name LIKE '%{product_name}%'
    AND p.date >= {days_ago(30)}
    ''')
    

    if df.empty or df.iloc[0]['avg_yield'] is None:
        return None

    avg_yield = df.iloc[0]['avg_yield'] / 100
    expected_output = round(input_kg * avg_yield, 1)
    expected_waste = round(input_kg - expected_output, 1)

    return {
        'input_kg': input_kg,
        'expected_output_kg': expected_output,
        'expected_waste_kg': expected_waste,
        'expected_yield_pct': round(avg_yield * 100, 1),
        'product': product_name
    }

def get_ai_waste_analysis(days=7):
    """Get AI-powered waste analysis and recommendations."""
    waste_df = get_waste_summary(days)
    yield_df = get_yield_by_product(days)

    if waste_df.empty:
        return "No waste data available for the selected period."

    prompt = f"""Analyse this factory waste data and provide actionable recommendations:

WASTE BREAKDOWN (last {days} days):
{waste_df.head(20).to_string()}

YIELD BY PRODUCT:
{yield_df.to_string()}

Provide:
1. Top 3 waste reduction opportunities with estimated savings in GBP
2. Products with concerning yield trends
3. Specific actionable steps the factory can take this week"""

    return get_response(prompt, system_prompt="You are a factory efficiency expert. Give practical, specific advice to reduce waste and improve yield in a fish processing factory. Always include estimated GBP savings.")
