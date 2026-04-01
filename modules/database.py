"""Shared database connection for OpsMind. Supports SQLite and SQL Server."""
import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URL

_engine = None


def get_engine():
    """Get or create cached SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False)
    return _engine


def query(sql, params=None):
    """Run a read-only SQL query and return a DataFrame."""
    engine = get_engine()
    return pd.read_sql(sql, engine, params=params)


def scalar(sql, params=None):
    """Run a query and return a single value."""
    df = query(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]
