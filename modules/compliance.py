"""Compliance and audit report generator."""
from datetime import datetime

import pandas as pd

from config import TEMP_MAX_COLD_ROOM, TEMP_MIN_COLD_ROOM
from modules.database import query
from modules.sql_dialect import days_ago


def trace_batch(batch_code):
    """Full traceability for a batch — from raw material to customer."""
    rm = query(f"""
        SELECT rm.*, pr.name as product_name
        FROM raw_materials rm
        JOIN products pr ON rm.product_id = pr.id
        WHERE rm.batch_code LIKE '%{batch_code}%'
    """)

    prod = query(f"""
        SELECT p.*, pr.name as product_name
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE p.batch_code LIKE '%{batch_code}%'
    """)

    orders = pd.DataFrame()
    if not prod.empty:
        product_id = prod.iloc[0]['product_id']
        prod_date = prod.iloc[0]['date']
        orders = query(f"""
            SELECT * FROM orders
            WHERE product_id = {product_id} AND order_date >= '{prod_date}'
            ORDER BY order_date
        """)

    return {
        'batch_code': batch_code,
        'raw_materials': rm,
        'production': prod,
        'orders': orders
    }


def get_temperature_excursions(days=7):
    """Find temperature readings outside acceptable range."""
    return query(f"""
        SELECT location, temperature, recorded_at, recorded_by
        FROM temp_logs
        WHERE recorded_at >= {days_ago(days)}
        AND (
            (location LIKE '%Cold Room%' AND (temperature > {TEMP_MAX_COLD_ROOM} OR temperature < {TEMP_MIN_COLD_ROOM}))
            OR (location LIKE '%Freezer%' AND temperature > -15)
            OR (location LIKE '%Dispatch%' AND temperature > 8)
        )
        ORDER BY recorded_at DESC
    """)


def get_allergen_matrix():
    """Generate allergen matrix for all products."""
    df = query("SELECT name, species, category, allergens FROM products ORDER BY name")

    all_allergens = set()
    for row in df['allergens']:
        if row:
            for a in row.split(','):
                all_allergens.add(a.strip())

    for allergen in sorted(all_allergens):
        df[allergen] = df['allergens'].apply(
            lambda x: 'Y' if x and allergen in x else ''
        )
    return df


def get_compliance_score():
    """Calculate overall compliance score based on key indicators."""
    scores = {}

    excursions = get_temperature_excursions(30)
    total_readings = query(f"""
        SELECT COUNT(*) as cnt FROM temp_logs
        WHERE recorded_at >= {days_ago(30)}
    """).iloc[0]['cnt']

    if total_readings > 0:
        temp_compliance = round((1 - len(excursions) / total_readings) * 100, 1)
    else:
        temp_compliance = 100
    scores['Temperature Control'] = temp_compliance

    trace_df = query(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN batch_code IS NOT NULL AND batch_code != '' THEN 1 ELSE 0 END) as with_batch
        FROM production WHERE date >= {days_ago(30)}
    """)
    if trace_df.iloc[0]['total'] > 0:
        scores['Traceability'] = round(trace_df.iloc[0]['with_batch'] / trace_df.iloc[0]['total'] * 100, 1)
    else:
        scores['Traceability'] = 100

    scores['Overall'] = round(sum(scores.values()) / len(scores), 1)
    return scores


def generate_audit_summary(days=30):
    """Generate a summary report for BRC/HACCP audit preparation."""
    excursions = get_temperature_excursions(days)
    allergen_matrix = get_allergen_matrix()
    compliance = get_compliance_score()

    production_summary = query(f"""
        SELECT pr.name, COUNT(*) as runs,
               ROUND(SUM(p.raw_input_kg), 0) as total_input_kg,
               ROUND(SUM(p.finished_output_kg), 0) as total_output_kg,
               ROUND(AVG(p.yield_pct), 1) as avg_yield
        FROM production p
        JOIN products pr ON p.product_id = pr.id
        WHERE p.date >= {days_ago(days)}
        GROUP BY pr.name ORDER BY total_input_kg DESC
    """)

    return {
        'period_days': days,
        'compliance_scores': compliance,
        'temperature_excursions': excursions,
        'allergen_matrix': allergen_matrix,
        'production_summary': production_summary,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
