"""Schema registry — maps business domains to actual table/column names.

For 147+ table databases, the LLM cannot hold all tables in its prompt.
This registry tells OpsMind which tables matter for each type of question,
so the LLM only sees 4-10 relevant tables instead of all 147.

Configure by editing schema.yaml or setting SCHEMA_CONFIG env var.
"""
import os
import yaml
from config import DB_TYPE

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
        "description": "Allergens, temperature, batch codes",
        "tables": {
            "products": "id, name, allergens",
            "temp_logs": "id, location, temperature, recorded_at, recorded_by",
            "production": "id, product_id, batch_code, date",
        },
    },
}

# Keywords that map questions to domains
DOMAIN_KEYWORDS = {
    "traceability": ["trace", "batch", "track", "where did", "origin", "source", "supplier", "recall"],
    "production": ["production", "produce", "processed", "output", "yield", "waste", "line", "shift"],
    "orders": ["order", "customer", "delivery", "pending", "lidl", "iceland", "tesco", "aldi", "morrisons"],
    "temperature": ["temperature", "temp", "cold room", "freezer", "excursion", "degrees"],
    "staff": ["staff", "overtime", "hours", "shift", "worker", "employee", "radu", "marek"],
    "stock": ["stock", "expir", "raw material", "inventory", "available", "shortage"],
    "compliance": ["allergen", "compliance", "audit", "haccp", "brc", "food safety"],
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
    """Generate the optimal SQL prompt for a question — only relevant tables."""
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

    return f"""Convert this question to SQL. Return ONLY the SQL query, nothing else.

TABLES:
{tables_str}

RULES: {hints} JOIN tables for names. Add ORDER BY. ONLY return SQL."""


def get_all_table_names():
    """Get all unique table names across all domains."""
    schema = load_schema()
    tables = set()
    for domain_data in schema.values():
        if isinstance(domain_data, dict) and "tables" in domain_data:
            tables.update(domain_data["tables"].keys())
    return sorted(tables)
