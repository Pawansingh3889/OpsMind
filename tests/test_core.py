"""Tests for OpsMind core modules."""
import pytest
import os
import sys
import sqlite3
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Ensure demo database exists before tests
DEMO_DB = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'demo.db')


@pytest.fixture(autouse=True)
def ensure_demo_db():
    """Ensure demo database exists for all tests."""
    if not os.path.exists(DEMO_DB):
        from scripts.seed_demo_db import seed
        seed()


# ==================== CONFIG TESTS ====================

class TestConfig:
    def test_config_loads(self):
        from config import APP_NAME, VERSION, DATABASE_URL, DB_TYPE
        assert APP_NAME == "OpsMind"
        assert VERSION is not None
        assert DATABASE_URL is not None
        assert DB_TYPE in ("sqlite", "mssql")

    def test_default_is_sqlite(self):
        from config import DB_TYPE
        assert DB_TYPE == "sqlite"

    def test_thresholds_are_set(self):
        from config import YIELD_DROP_THRESHOLD, TEMP_MAX_COLD_ROOM, MAX_WEEKLY_HOURS
        assert YIELD_DROP_THRESHOLD == 5.0
        assert TEMP_MAX_COLD_ROOM == 5.0
        assert MAX_WEEKLY_HOURS == 48


# ==================== SQL DIALECT TESTS ====================

class TestSQLDialect:
    def test_date_now_sqlite(self):
        from modules.sql_dialect import date_now
        result = date_now()
        assert "date('now')" in result

    def test_days_ago_sqlite(self):
        from modules.sql_dialect import days_ago
        result = days_ago(7)
        assert "7" in result
        assert "date(" in result

    def test_days_ahead_sqlite(self):
        from modules.sql_dialect import days_ahead
        result = days_ahead(3)
        assert "3" in result

    def test_days_until_sqlite(self):
        from modules.sql_dialect import days_until
        result = days_until("expiry_date")
        assert "expiry_date" in result
        assert "julianday" in result

    def test_date_hints_sqlite(self):
        from modules.sql_dialect import date_hints
        result = date_hints()
        assert "SQLite" in result


# ==================== SCHEMA REGISTRY TESTS ====================

class TestSchemaRegistry:
    def test_load_default_schema(self):
        from modules.schema_registry import load_schema
        schema = load_schema()
        assert "traceability" in schema
        assert "production" in schema
        assert "orders" in schema
        assert "temperature" in schema
        assert "staff" in schema

    def test_detect_domain_traceability(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("trace batch PR-001") == "traceability"
        assert detect_domain("where did batch X come from") == "traceability"

    def test_detect_domain_production(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("how much did we produce today") == "production"
        assert detect_domain("show waste this week") == "production"

    def test_detect_domain_orders(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("pending orders for Lidl") == "orders"
        assert detect_domain("customer delivery schedule") == "orders"

    def test_detect_domain_temperature(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("cold room temperature") == "temperature"

    def test_detect_domain_staff(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("overtime hours this week") == "staff"

    def test_detect_domain_default(self):
        from modules.schema_registry import detect_domain
        assert detect_domain("random gibberish xyz") == "production"

    def test_get_tables_for_domain(self):
        from modules.schema_registry import get_tables_for_domain
        tables = get_tables_for_domain("traceability")
        assert "products" in tables
        assert "production" in tables
        assert "raw_materials" in tables

    def test_get_prompt_for_question(self):
        from modules.schema_registry import get_prompt_for_question
        prompt = get_prompt_for_question("show waste by product")
        assert "production" in prompt.lower() or "waste" in prompt.lower()
        assert "SQL" in prompt

    def test_get_all_table_names(self):
        from modules.schema_registry import get_all_table_names
        tables = get_all_table_names()
        assert len(tables) > 0
        assert "products" in tables


# ==================== DATABASE TESTS ====================

class TestDatabase:
    def test_query_returns_dataframe(self):
        from modules.database import query
        df = query("SELECT COUNT(*) as cnt FROM products")
        assert isinstance(df, pd.DataFrame)
        assert df.iloc[0]['cnt'] > 0

    def test_scalar_returns_value(self):
        from modules.database import scalar
        count = scalar("SELECT COUNT(*) FROM products")
        assert count is not None
        assert count > 0

    def test_discover_tables(self):
        from modules.database import discover_tables
        tables = discover_tables()
        assert "products" in tables
        assert "production" in tables

    def test_discover_columns(self):
        from modules.database import discover_columns
        cols = discover_columns("products")
        assert "name" in cols
        assert "id" in cols


# ==================== COMPLIANCE TESTS ====================

class TestCompliance:
    def test_trace_batch_returns_dict(self):
        from modules.compliance import trace_batch
        result = trace_batch("PR-")
        assert "batch_code" in result
        assert "raw_materials" in result
        assert "production" in result
        assert "orders" in result

    def test_allergen_matrix(self):
        from modules.compliance import get_allergen_matrix
        df = get_allergen_matrix()
        assert not df.empty
        assert "name" in df.columns
        assert "Fish" in df.columns

    def test_compliance_score(self):
        from modules.compliance import get_compliance_score
        scores = get_compliance_score()
        assert "Temperature Control" in scores
        assert "Traceability" in scores
        assert "Overall" in scores
        assert 0 <= scores["Overall"] <= 100

    def test_temperature_excursions(self):
        from modules.compliance import get_temperature_excursions
        df = get_temperature_excursions(60)
        assert isinstance(df, pd.DataFrame)
        if not df.empty:
            assert "location" in df.columns
            assert "temperature" in df.columns


# ==================== ALERTS TESTS ====================

class TestAlerts:
    def test_check_all_alerts_returns_list(self):
        from modules.alerts import check_all_alerts
        alerts = check_all_alerts()
        assert isinstance(alerts, list)

    def test_alert_structure(self):
        from modules.alerts import check_all_alerts
        alerts = check_all_alerts()
        if alerts:
            alert = alerts[0]
            assert "level" in alert
            assert "title" in alert
            assert "message" in alert
            assert "category" in alert
            assert alert["level"] in ("critical", "warning", "info")

    def test_overtime_detection(self):
        from modules.alerts import check_overtime
        alerts = check_overtime()
        assert isinstance(alerts, list)
        for a in alerts:
            assert "hours" in a["message"].lower() or "overtime" in a["title"].lower()


# ==================== WASTE PREDICTOR TESTS ====================

class TestWastePredictor:
    def test_yield_by_product(self):
        from modules.waste_predictor import get_yield_by_product
        df = get_yield_by_product(60)
        assert not df.empty
        assert "product" in df.columns
        assert "avg_yield" in df.columns
        assert "waste_cost_gbp" in df.columns

    def test_waste_summary(self):
        from modules.waste_predictor import get_waste_summary
        df = get_waste_summary(60)
        assert not df.empty
        assert "waste_type" in df.columns
        assert "total_kg" in df.columns

    def test_predict_waste(self):
        from modules.waste_predictor import predict_waste
        result = predict_waste("Salmon", 500)
        if result:
            assert "expected_output_kg" in result
            assert "expected_waste_kg" in result
            assert "expected_yield_pct" in result
            assert result["input_kg"] == 500
            assert result["expected_output_kg"] + result["expected_waste_kg"] == 500


# ==================== SQL AGENT SAFETY TESTS ====================

class TestSQLAgentSafety:
    def test_blocks_insert(self):
        from modules.sql_agent import run_query
        # Simulate what happens when LLM returns dangerous SQL
        # We test the safety check directly
        result = run_query("INSERT INTO products VALUES (99, 'hack', '', '', 0, 0, '')")
        assert result["error"] is True or "read-only" in result["explanation"].lower() or "blocked" in result["explanation"].lower()

    def test_blocks_drop(self):
        from modules.sql_agent import run_query
        result = run_query("DROP TABLE products")
        assert result["error"] is True


# ==================== DOC SEARCH TESTS ====================

class TestDocSearch:
    def test_get_doc_count(self):
        from modules.doc_search import get_doc_count
        count = get_doc_count()
        assert isinstance(count, int)
        assert count >= 0

    def test_search_returns_list(self):
        from modules.doc_search import search
        results = search("temperature procedure")
        assert isinstance(results, list)
