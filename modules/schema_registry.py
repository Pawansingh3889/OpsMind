"""Schema registry — maps business domains to actual table/column names.

For 147+ table databases, the LLM cannot hold all tables in its prompt.
This registry tells OpsMind which tables matter for each type of question,
so the LLM only sees 4-10 relevant tables instead of all 147.

Configure by editing schema.yaml or setting SCHEMA_CONFIG env var.
"""
import os

import yaml

_schema = None


# Default schema for the demo SQLite database
DEFAULT_SCHEMA = {
    "traceability": {
        "description": "Batch traceability from raw material to customer",
        "tables": {
            "products": "id, name, species, category, unit_cost_per_kg, sell_price_per_kg, allergens",
            "raw_materials": "id, product_id, batch_code, supplier, quantity_kg, received_date, expiry_date, temperature_on_arrival",
            "production": "id, product_id, batch_code, date, raw_input_kg, finished_output_kg, waste_kg, yield_pct, line_number, shift, operator",
            "orders": "id, customer, product_id, quantity_kg, order_date, delivery_date, status, price_per_kg",
        },
    },
    "production": {
        "description": "Production output, yield, and waste",
        "tables": {
            "products": "id, name, species, category, unit_cost_per_kg, sell_price_per_kg",
            "production": "id, product_id, batch_code, date, raw_input_kg, finished_output_kg, waste_kg, yield_pct, line_number, shift, operator",
            "waste_log": "id, production_id, waste_type, quantity_kg, reason, date",
        },
    },
    "orders": {
        "description": "Customer orders and delivery",
        "tables": {
            "products": "id, name, species, category, sell_price_per_kg",
            "orders": "id, customer, product_id, quantity_kg, order_date, delivery_date, status, price_per_kg",
        },
    },
    "temperature": {
        "description": "Temperature monitoring and excursions",
        "tables": {
            "temp_logs": "id, location, temperature, recorded_at, recorded_by",
        },
    },
    "staff": {
        "description": "Staff hours, shifts, and overtime",
        "tables": {
            "staff": "id, name, role, shift_pattern, hours_this_week, hourly_rate",
        },
    },
    "stock": {
        "description": "Raw material stock and expiry",
        "tables": {
            "products": "id, name, species",
            "raw_materials": "id, product_id, batch_code, supplier, quantity_kg, received_date, expiry_date",
        },
    },
    "compliance": {
        "description": "Allergens, temperature, batch codes, non-conformance",
        "tables": {
            "products": "id, name, allergens",
            "temp_logs": "id, location, temperature, recorded_at, recorded_by",
            "production": "id, product_id, batch_code, date",
            "prod_products": "product_code, description, species, customer, allergens, hazard_class",
            "prod_traceability": "trace_id, batch_code, supplier, species, catch_area, vessel_name, certified, country_origin",
            "prod_temperature_logs": "log_id, location, reading_time, temp_celsius, target_min, target_max, in_range",
            "prod_non_conformance": "nc_id, nc_date, run_number, product_code, nc_type, severity, description, root_cause, corrective_action, status",
            "prod_case_verification": "verify_id, run_number, expected_plu, scanned_plu, match, scan_time",
        },
    },
}

# Production ERP tables — extend existing domains
DEFAULT_SCHEMA["traceability"]["tables"].update({
    "prod_runs": "run_number, production_date, product_code, trace_id, kill_date, status, created_by",
    "prod_products": "product_code, description, species, customer, allergens",
    "prod_traceability": "trace_id, batch_code, supplier, species, catch_area, catch_method, vessel_name, landing_date, kill_date, received_date, received_temp_c, use_by_date, country_origin, certified",
})
DEFAULT_SCHEMA["production"]["tables"].update({
    "prod_lines": "line_id, line_name, line_type, area, max_capacity_kg",
    "prod_products": "product_code, description, category, species, customer, pack_size_g",
    "prod_runs": "run_number, production_date, shift_code, prod_line, product_code, target_qty_kg, actual_qty_kg, waste_kg, yield_pct, status, trace_id, created_by",
    "prod_transactions": "trans_id, run_number, weight_g, target_weight_g, tare_g, net_weight_g, overweight_g, prod_line",
    "prod_run_totals": "run_number, total_packs, total_weight_kg, avg_weight_g, giveaway_kg, giveaway_pct, reject_count, downtime_mins",
    "prod_non_conformance": "nc_id, nc_date, run_number, product_code, nc_type, severity, status",
})
DEFAULT_SCHEMA["orders"]["tables"].update({
    "prod_despatch": "despatch_id, order_number, customer, product_code, qty_cases, qty_kg, despatch_date, delivery_date, vehicle_temp_c, status",
    "prod_products": "product_code, description, species, customer",
})
DEFAULT_SCHEMA["temperature"]["tables"].update({
    "prod_temperature_logs": "log_id, location, reading_time, temp_celsius, target_min, target_max, in_range, recorded_by",
})
DEFAULT_SCHEMA["staff"]["tables"].update({
    "prod_shifts": "shift_id, shift_date, shift_code, line_id, headcount, planned_hours, actual_hours, overtime_hours, output_kg, kg_per_head",
})
DEFAULT_SCHEMA["stock"]["tables"].update({
    "prod_traceability": "trace_id, batch_code, supplier, species, received_date, use_by_date, country_origin, certified",
})

# Keywords that map questions to domains
DOMAIN_KEYWORDS = {
    "traceability": ["trace", "batch", "track", "where did", "origin", "source", "supplier", "recall",
                     "catch area", "vessel", "MSC", "ASC", "landing", "kill date", "certified", "country of origin", "catch method"],
    "production": ["production", "produce", "processed", "output", "yield", "waste", "line", "shift",
                   "run number", "giveaway", "tare", "overweight", "filleting", "packing", "smoking",
                   "PLU", "product code", "run total", "downtime", "reject", "target weight", "net weight", "capacity"],
    "orders": ["order", "customer", "delivery", "pending", "lidl", "iceland", "tesco", "aldi", "morrisons",
               "despatch", "dispatch", "vehicle temp", "loaded", "cases"],
    "temperature": ["temperature", "temp", "cold room", "freezer", "excursion", "degrees",
                    "chiller", "blast freezer", "goods in", "breach", "CCP", "target temp", "in range"],
    "staff": ["staff", "overtime", "hours", "shift", "worker", "employee", "radu", "marek",
              "headcount", "kg per head", "productivity", "planned hours", "actual hours", "day shift", "night shift"],
    "stock": ["stock", "expir", "raw material", "inventory", "available", "shortage",
              "use by", "shelf life", "received"],
    "compliance": ["allergen", "compliance", "audit", "haccp", "brc", "food safety",
                   "non conformance", "NC", "corrective action", "root cause", "foreign body",
                   "critical NC", "case verification", "scanner", "label", "line clear", "allergen changeover"],
}


def load_schema():
    """Load schema from YAML file or use defaults."""
    global _schema
    if _schema is not None:
        return _schema

    config_path = os.getenv("SCHEMA_CONFIG", "schema.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                custom = yaml.safe_load(f)
            if custom:
                _schema = custom
                return _schema
        except Exception as e:
            print(f"Schema config error: {e}, using defaults")

    _schema = DEFAULT_SCHEMA
    return _schema


def detect_domain(question):
    """Detect which domain a question belongs to based on keywords."""
    q = question.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scores[domain] = score

    if not scores:
        return "production"  # default domain

    return max(scores, key=scores.get)


def get_tables_for_domain(domain):
    """Get table definitions for a specific domain."""
    schema = load_schema()
    if domain in schema:
        return schema[domain].get("tables", {})
    return schema.get("production", {}).get("tables", {})


def get_prompt_for_question(question):
    """Generate the optimal SQL prompt for a question — only relevant tables.

    Injects runtime domain documentation when available so the LLM
    understands business thresholds, shift patterns, and compliance rules.
    """
    from modules.domain_docs import get_domain_prompt_section
    from modules.sql_dialect import date_hints

    domain = detect_domain(question)
    tables = get_tables_for_domain(domain)

    if not tables:
        return "No schema available. Ask the user to configure schema.yaml."

    # Build compact table list
    table_lines = []
    for table_name, columns in tables.items():
        table_lines.append(f"{table_name}({columns})")

    tables_str = "\n".join(table_lines)
    hints = date_hints()

    # Inject domain knowledge when a doc exists for this domain
    domain_section = get_domain_prompt_section(domain) or ""

    return f"""Convert this question to SQL. Return ONLY the SQL query, nothing else.

TABLES:
{tables_str}
{domain_section}
RULES: {hints} JOIN tables for names. Add ORDER BY. ONLY return SQL."""


def get_all_table_names():
    """Get all unique table names across all domains."""
    schema = load_schema()
    tables = set()
    for domain_data in schema.values():
        if isinstance(domain_data, dict) and "tables" in domain_data:
            tables.update(domain_data["tables"].keys())
    return sorted(tables)
