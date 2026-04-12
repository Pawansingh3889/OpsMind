"""Shared database connection for OpsMind. Supports SQLite and SQL Server."""
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from config import DATABASE_URL, DB_TYPE


@st.cache_resource
def get_engine():
    """Get or create cached SQLAlchemy engine (cached across Streamlit reruns)."""
    return create_engine(DATABASE_URL, echo=False)


def query(sql, params=None):
    """Run a read-only SQL query and return a DataFrame."""
    engine = get_engine()
    if params:
        return pd.read_sql(text(sql), engine, params=dict(enumerate(params)) if isinstance(params, list) else params)
    return pd.read_sql(sql, engine)


def scalar(sql, params=None):
    """Run a query and return a single value."""
    df = query(sql, params)
    if df.empty:
        return None
    return df.iloc[0, 0]


def discover_tables():
    """List all tables in the connected database."""
    if DB_TYPE == "mssql":
        return query("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME").iloc[:, 0].tolist()
    else:
        return query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").iloc[:, 0].tolist()


def discover_columns(table_name):
    """Get column names for a specific table."""
    if DB_TYPE == "mssql":
        df = query(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table_name}' ORDER BY ORDINAL_POSITION")
    else:
        df = query(f"PRAGMA table_info({table_name})")
        if not df.empty:
            return df['name'].tolist()
        return []
    return df.iloc[:, 0].tolist() if not df.empty else []
