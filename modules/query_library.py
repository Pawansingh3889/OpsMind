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
        "sql": lambda: """
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
            # Word-bounded "product" so we don't greedily match "production"
            # and steal questions meant for the per-line yield pattern
            # further down. Caught by tests/eval/ (library/wrong-pattern).
            r"(yield|yields).*\b(product|by\s+product|trend|average)\b",
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
    # --- Production ERP queries ---
    {
        "patterns": [
            r"yield.*(line|production line)",
            r"(line|production line).*yield",
            r"(line|production).*output",
        ],
        "sql": lambda: f"""
            SELECT r.production_date, pl.line_name, pl.line_type,
                   COUNT(*) as runs,
                   ROUND(SUM(r.target_qty_kg), 0) as target_kg,
                   ROUND(SUM(r.actual_qty_kg), 0) as actual_kg,
                   ROUND(SUM(r.waste_kg), 0) as waste_kg,
                   ROUND(AVG(r.yield_pct), 1) as avg_yield_pct
            FROM prod_runs r
            JOIN prod_lines pl ON r.prod_line = pl.line_id
            WHERE r.status = 'complete'
              AND r.production_date >= {days_ago(7)}
            GROUP BY r.production_date, pl.line_name, pl.line_type
            ORDER BY r.production_date DESC, avg_yield_pct ASC
        """,
        "description": "Yield by production line (last 7 days)",
    },
    {
        "patterns": [
            r"trace.*(batch|BC-)",
            r"where.*(fish|cod|salmon|haddock).*(come|from|origin)",
            r"(batch|trace).*lookup",
            r"(vessel|catch area|supplier).*batch",
        ],
        "sql": lambda: """
            SELECT r.run_number, r.production_date,
                   pp.description as product, pp.customer,
                   t.batch_code, t.supplier, t.species,
                   t.catch_area, t.catch_method, t.vessel_name,
                   t.landing_date, t.country_origin, t.certified
            FROM prod_runs r
            JOIN prod_products pp ON r.product_code = pp.product_code
            JOIN prod_traceability t ON r.trace_id = t.trace_id
            ORDER BY r.production_date DESC
            LIMIT 20
        """,
        "description": "Traceability chain: run to catch vessel",
    },
    {
        "patterns": [
            r"(temp|temperature).*(breach|excursion|out of range|alert)",
            r"(chiller|freezer).*(breach|alert|problem)",
            r"breach.*(temp|temperature)",
        ],
        "sql": lambda: f"""
            SELECT tl.reading_time, tl.location,
                   tl.temp_celsius, tl.target_max,
                   ROUND(tl.temp_celsius - tl.target_max, 1) as degrees_over,
                   tl.recorded_by
            FROM prod_temperature_logs tl
            WHERE tl.in_range = 0
              AND tl.reading_time >= {days_ago(7)}
            ORDER BY tl.reading_time DESC
        """,
        "description": "Temperature breaches (last 7 days)",
    },
    {
        "patterns": [
            r"allergen.*(line|changeover|clear)",
            r"line clear",
            r"(wheat|egg|milk|mustard).*(line|product)",
        ],
        "sql": lambda: f"""
            SELECT r.run_number, r.production_date,
                   pl.line_name, pp.description, pp.allergens,
                   r.created_by as operator
            FROM prod_runs r
            JOIN prod_products pp ON r.product_code = pp.product_code
            JOIN prod_lines pl ON r.prod_line = pl.line_id
            WHERE r.production_date >= {days_ago(3)}
            ORDER BY r.prod_line, r.created_date
        """,
        "description": "Allergen changeover sequence (last 3 days)",
    },
    {
        "patterns": [
            r"(shift|day|night).*(productivity|kg per head|output)",
            r"(productivity|kg per head).*(shift|day|night)",
            r"day.*vs.*night",
        ],
        "sql": lambda: f"""
            SELECT s.shift_code,
                   COUNT(*) as total_shifts,
                   ROUND(AVG(s.headcount), 0) as avg_headcount,
                   ROUND(AVG(s.output_kg), 0) as avg_output_kg,
                   ROUND(AVG(s.kg_per_head), 1) as avg_kg_per_head,
                   ROUND(AVG(s.overtime_hours), 1) as avg_overtime_hrs
            FROM prod_shifts s
            WHERE s.shift_date >= {days_ago(14)}
            GROUP BY s.shift_code
        """,
        "description": "Shift productivity comparison (last 14 days)",
    },
    {
        "patterns": [
            r"giveaway",
            r"overweight.*(product|analysis)",
            r"(product|plu).*waste",
        ],
        "sql": lambda: f"""
            SELECT pp.description, pp.customer, pp.pack_size_g,
                   COUNT(*) as total_runs,
                   ROUND(SUM(r.actual_qty_kg), 0) as produced_kg,
                   ROUND(SUM(r.waste_kg), 0) as waste_kg,
                   ROUND(AVG(rt.giveaway_pct), 1) as avg_giveaway_pct
            FROM prod_runs r
            JOIN prod_products pp ON r.product_code = pp.product_code
            LEFT JOIN prod_run_totals rt ON r.run_number = rt.run_number
            WHERE r.status = 'complete'
              AND r.production_date >= {days_ago(14)}
            GROUP BY pp.description, pp.customer, pp.pack_size_g
            ORDER BY avg_giveaway_pct DESC
        """,
        "description": "Giveaway analysis by product (last 14 days)",
    },
    {
        "patterns": [
            r"(open|critical).*(NC|non.conformance)",
            r"non.conformance.*(open|critical|outstanding)",
            r"foreign body",
        ],
        "sql": lambda: """
            SELECT nc.nc_id, nc.nc_date, nc.nc_type, nc.severity,
                   nc.description, nc.raised_by, nc.status,
                   pp.description as product
            FROM prod_non_conformance nc
            LEFT JOIN prod_products pp ON nc.product_code = pp.product_code
            WHERE nc.status != 'closed'
            ORDER BY
                CASE nc.severity WHEN 'critical' THEN 1 WHEN 'major' THEN 2 ELSE 3 END,
                nc.nc_date
        """,
        "description": "Open non-conformances by severity",
    },
    {
        "patterns": [
            r"(MSC|ASC).*(certified|certification|status)",
            r"sustainable.*(fish|source)",
            r"certified.*(batch|supplier)",
        ],
        "sql": lambda: """
            SELECT t.trace_id, t.batch_code, t.supplier,
                   t.species, t.catch_area, t.certified,
                   t.country_origin, t.vessel_name
            FROM prod_traceability t
            ORDER BY t.received_date DESC
        """,
        "description": "MSC/ASC certification status by batch",
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
