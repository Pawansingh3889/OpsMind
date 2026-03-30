"""OpsMind configuration."""
import os

# LLM
OLLAMA_MODEL = os.getenv("OPSMIND_MODEL", "mistral")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Database
DATABASE_URL = os.getenv("OPSMIND_DB", "sqlite:///data/demo.db")

# ChromaDB
CHROMA_DIR = os.getenv("OPSMIND_CHROMA_DIR", "data/chroma_store")

# App
APP_NAME = "OpsMind"
APP_TAGLINE = "The AI Brain for Your Factory"
VERSION = "0.1.0"

# Alerts
YIELD_DROP_THRESHOLD = 5.0  # Alert if yield drops more than 5% vs average
TEMP_MAX_COLD_ROOM = 5.0    # Alert above 5°C
TEMP_MIN_COLD_ROOM = -2.0   # Alert below -2°C
MAX_WEEKLY_HOURS = 48        # Working Time Regulations
