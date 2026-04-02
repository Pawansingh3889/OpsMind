"""SQL dialect abstraction. Generates correct SQL for SQLite or SQL Server."""
from config import DB_TYPE


def date_now():
    """Current date."""
    if DB_TYPE == "mssql":
        return "CAST(GETDATE() AS DATE)"
    return "date('now')"


def days_ago(n):
    """Date N days in the past."""
    if DB_TYPE == "mssql":
        return f"DATEADD(day, -{n}, GETDATE())"
    return f"date('now', '-{n} days')"


def days_ahead(n):
    """Date N days in the future."""
    if DB_TYPE == "mssql":
        return f"DATEADD(day, {n}, GETDATE())"
    return f"date('now', '+{n} days')"


def days_until(column):
    """Integer days between now and a date column."""
    if DB_TYPE == "mssql":
        return f"DATEDIFF(day, GETDATE(), {column})"
    return f"CAST(julianday({column}) - julianday('now') AS INTEGER)"


def limit_clause(n):
    """LIMIT or TOP clause. For MSSQL, returns empty (use TOP in SELECT)."""
    if DB_TYPE == "mssql":
        return ""
    return f"LIMIT {n}"


def top_clause(n):
    """TOP clause for SELECT. For SQLite, returns empty (use LIMIT)."""
    if DB_TYPE == "mssql":
        return f"TOP {n}"
    return ""


def date_hints():
    """Return date syntax hints for LLM prompts."""
    if DB_TYPE == "mssql":
        return "T-SQL syntax. today=CAST(GETDATE() AS DATE). Use DATEADD(day,-N,GETDATE()) for past dates. Use TOP instead of LIMIT."
    return "SQLite syntax. today=date('now'). this week=date('now','-7 days'). Use LIMIT."
