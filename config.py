"""OpsMind configuration."""
import os

# LLM
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "opsmind")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Database
# Supports SQLite (demo) and SQL Server (production)
#
# SQLite (default demo):
#   OPSMIND_DB=sqlite:///data/demo.db
#
# SQL Server (read-only):
#   OPSMIND_DB=mssql+pyodbc://readonly_user:password@SERVER/DATABASE?driver=ODBC+Driver+17+for+SQL+Server
#
# SQL Server with Windows Auth:
#   OPSMIND_DB=mssql+pyodbc://SERVER/DATABASE?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes
#
DATABASE_URL = os.getenv("OPSMIND_DB", "sqlite:///data/demo.db")

# Database type detection
DB_TYPE = "mssql" if "mssql" in DATABASE_URL else "sqlite"

# ChromaDB
CHROMA_DIR = os.getenv("OPSMIND_CHROMA_DIR", "data/chroma_store")

# App
APP_NAME = "OpsMind"
APP_TAGLINE = "The AI Brain for Your Operations"
VERSION = "0.3.0"

# Schema
SCHEMA_CONFIG = os.getenv("SCHEMA_CONFIG", "schema.yaml")
SCHEMA_MODE = os.getenv("SCHEMA_MODE", "auto")  # "auto" or "mapped"

# Alerts
YIELD_DROP_THRESHOLD = 5.0  # Alert if yield drops more than 5% vs average
TEMP_MAX_COLD_ROOM = 5.0    # Alert above 5°C
TEMP_MIN_COLD_ROOM = -2.0   # Alert below -2°C
MAX_WEEKLY_HOURS = 48        # Working Time Regulations

# Production alerts
PROD_YIELD_MIN = 90.0        # Alert if run yield below 90%
GIVEAWAY_PCT_THRESHOLD = 3.0 # Alert if giveaway exceeds 3%
NC_CRITICAL_OPEN_DAYS = 2    # Alert if critical NC open > 2 days
