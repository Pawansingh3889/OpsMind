"""Pre-built query library for reliable answers to common questions.

When a question matches a known pattern, use tested SQL instead of
asking the LLM to generate it. This guarantees correct results for
the most common operational questions.

LLM generation is used only for questions that don't match any pattern.
"""
import re
from modules.sql_dialect import days_ago, days_ahead, days_until


# Each entry: (pattern_regex, sql_template, description)
# SQL templates use {days_ago_N} placeholders replaced at runtime
QUERY_LIBRARY = [
    {
        "patterns": [
            r"today.*(production|output|summary)",
            r"(production|output).*(today|summary)",
            r"how much.*(produce|process).*(today)",
            r"what did we.*(produce|process|make).*(today)",
        ],
        "sql": lambda: f"""
            SELECT pr.name as product,
                   COUNT(*) as runs,
                   ROUND(SUM(p.raw_input_kg), 0) as input_kg,
                   ROUND(SUM(p.finished_output_kg), 0) as output_kg,
                   ROUND(SUM(p.waste_kg), 0) as waste_kg,
                   ROUND(AVG(p.yield_pct), 1) as avg_yield_pct,
                   ROUND(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) as waste_cost_gbp
            FROM production p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.date >= {days_ago(1)}
            GROUP BY pr.name
            ORDER BY output_kg DESC
        """,
        "description": "Today's production summary by product",
    },
    {
        "patterns": [
            r"(top|worst|most).*(waste|wasteful)",
            r"waste.*(product|by product)",
            r"which product.*(waste|wasting)",
        ],
        "sql": lambda: f"""
            SELECT pr.name as product,
                   ROUND(SUM(p.waste_kg), 0) as total_waste_kg,
                   ROUND(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) as waste_cost_gbp,
                   ROUND(AVG(p.yield_pct), 1) as avg_yield_pct,
                   COUNT(*) as production_runs
            FROM production p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.date >= {days_ago(7)}
            GROUP BY pr.name, pr.unit_cost_per_kg
            ORDER BY total_waste_kg DESC
        """,
        "description": "Top products by waste this week",
    },
    {
        "patterns": [
            r"pending.*(order|orders)",
            r"order.*(pending|outstanding|open)",
            r"what.*orders.*(this week|pending|due)",
        ],
        "sql": lambda: f"""
            SELECT o.customer,
                   pr.name as product,
                   ROUND(SUM(o.quantity_kg), 0) as total_kg,
                   COUNT(*) as num_orders,
                   MIN(o.delivery_date) as earliest_delivery
            FROM orders o
            JOIN products pr ON o.product_id = pr.id
            WHERE o.status = 'pending'
            GROUP BY o.customer, pr.name
            ORDER BY earliest_delivery
        """,
        "description": "All pending orders by customer",
    },
    {
        "patterns": [
            r"temperature.*(excursion|issue|problem|breach)",
            r"(cold room|freezer).*(temperature|temp)",
            r"any.*temp.*(excursion|issue|today|this week)",
        ],
        "sql": lambda: f"""
            SELECT location, temperature, recorded_at, recorded_by
            FROM temp_logs
            WHERE recorded_at >= {days_ago(7)}
            AND (
                (location LIKE '%Cold Room%' AND temperature > 5)
                OR (location LIKE '%Freezer%' AND temperature > -15)
                OR (location LIKE '%Dispatch%' AND temperature > 8)
            )
            ORDER BY recorded_at DESC
        """,
        "description": "Temperature excursions in the last 7 days",
    },
    {
        "patterns": [
            r"(yield|yields).*(product|by product|trend|average)",
            r"average.*yield",
            r"(best|worst).*yield",
        ],
        "sql": lambda: f"""
            SELECT pr.name as product,
                   ROUND(AVG(p.yield_pct), 1) as avg_yield_pct,
                   ROUND(MIN(p.yield_pct), 1) as min_yield,
                   ROUND(MAX(p.yield_pct), 1) as max_yield,
                   COUNT(*) as runs,
                   ROUND(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) as waste_cost_gbp
            FROM production p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.date >= {days_ago(30)}
            GROUP BY pr.name, pr.unit_cost_per_kg
            ORDER BY avg_yield_pct ASC
        """,
        "description": "Average yield by product (last 30 days)",
    },
    {
        "patterns": [
            r"overtime|over.?time|hours.*(breach|violation|exceed)",
            r"who.*(working|worked).*(too much|over)",
            r"staff.*(hours|overtime)",
        ],
        "sql": lambda: """
            SELECT name, role, shift_pattern, hours_this_week, hourly_rate,
                   CASE WHEN hours_this_week >= 48 THEN 'BREACH' ELSE 'OK' END as status
            FROM staff
            WHERE hours_this_week > 44
            ORDER BY hours_this_week DESC
        """,
        "description": "Staff overtime status",
    },
    {
        "patterns": [
            r"expir.*(stock|material|raw|soon)",
            r"(stock|material).*(expir|expire|expiring)",
            r"what.*(expiring|expires).*(soon|today|tomorrow)",
        ],
        "sql": lambda: f"""
            SELECT rm.batch_code, pr.name as product,
                   rm.quantity_kg, rm.expiry_date,
                   rm.supplier,
                   {days_until('rm.expiry_date')} as days_left
            FROM raw_materials rm
            JOIN products pr ON rm.product_id = pr.id
            WHERE rm.expiry_date <= {days_ahead(3)}
            AND rm.expiry_date >= {days_ago(0)}
            ORDER BY rm.expiry_date
        """,
        "description": "Raw materials expiring within 3 days",
    },
    {
        "patterns": [
            r"(how much|total).*(money|cost|lost|waste cost|gbp)",
            r"waste.*(cost|money|gbp|spend)",
            r"money.*lost.*(waste|this|week|month)",
        ],
        "sql": lambda: f"""
            SELECT
                ROUND(SUM(CASE WHEN p.date >= {days_ago(7)} THEN p.waste_kg * pr.unit_cost_per_kg END), 0) as week_cost_gbp,
                ROUND(SUM(CASE WHEN p.date >= {days_ago(30)} THEN p.waste_kg * pr.unit_cost_per_kg END), 0) as month_cost_gbp,
                ROUND(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) as total_cost_gbp,
                ROUND(SUM(CASE WHEN p.date >= {days_ago(7)} THEN p.waste_kg END), 0) as week_waste_kg,
                ROUND(SUM(CASE WHEN p.date >= {days_ago(30)} THEN p.waste_kg END), 0) as month_waste_kg
            FROM production p
            JOIN products pr ON p.product_id = pr.id
            WHERE p.date >= {days_ago(60)}
        """,
        "description": "Total waste cost breakdown",
    },
    {
        "patterns": [
            r"(customer|who).*(order|buy|buying|ordered).*(most|biggest)",
            r"(biggest|largest|top).*(customer|buyer)",
            r"order.*(by customer|customer breakdown)",
        ],
        "sql": lambda: f"""
            SELECT customer,
                   COUNT(*) as total_orders,
                   ROUND(SUM(quantity_kg), 0) as total_kg,
                   ROUND(SUM(quantity_kg * price_per_kg), 0) as revenue_gbp
            FROM orders
            WHERE order_date >= {days_ago(30)}
            GROUP BY customer
            ORDER BY total_kg DESC
        """,
        "description": "Customer orders breakdown (last 30 days)",
    },
    {
        "patterns": [
            r"(supplier|who).*(supply|supplies|delivered)",
            r"raw.*(material|intake).*(supplier|source)",
        ],
        "sql": lambda: f"""
            SELECT rm.supplier,
                   COUNT(*) as deliveries,
                   ROUND(SUM(rm.quantity_kg), 0) as total_kg,
                   ROUND(AVG(rm.temperature_on_arrival), 1) as avg_temp_on_arrival
            FROM raw_materials rm
            WHERE rm.received_date >= {days_ago(30)}
            GROUP BY rm.supplier
            ORDER BY total_kg DESC
        """,
        "description": "Supplier deliveries (last 30 days)",
    },
]


def find_matching_query(question):
    """Check if a question matches any pre-built query pattern.

    Returns (sql, description) if matched, (None, None) if not.
    """
    q = question.lower().strip()
    for entry in QUERY_LIBRARY:
        for pattern in entry["patterns"]:
            if re.search(pattern, q):
                return entry["sql"](), entry["description"]
    return None, None
