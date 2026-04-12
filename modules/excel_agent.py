"""Excel/CSV upload and analysis with Pandas."""
import pandas as pd

from modules.llm import get_response

EXCEL_SYSTEM_PROMPT = """You are a data analyst for a fish processing factory. The user has uploaded a spreadsheet and asked a question about it. Analyse the data and provide a clear, actionable answer.

RULES:
- Be concise and specific with numbers
- Use GBP for money, kg for weight
- Highlight trends, anomalies, or concerns
- Suggest actions if data shows problems
- Reference specific rows, columns, or values when relevant"""


def analyse_file(file_path, question, file_type='csv'):
    """Load a spreadsheet and answer questions about it."""
    try:
        if file_type in ('xlsx', 'xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        return {'answer': f'Could not read file: {e}', 'data': None}

    # Build data summary for the LLM
    summary = f"""SPREADSHEET DATA:
Columns: {', '.join(df.columns.tolist())}
Shape: {df.shape[0]} rows x {df.shape[1]} columns
Data types: {df.dtypes.to_string()}

First 10 rows:
{df.head(10).to_string()}

Basic stats:
{df.describe().to_string()}
"""

    prompt = f"{summary}\n\nQUESTION: {question}"
    answer = get_response(prompt, system_prompt=EXCEL_SYSTEM_PROMPT)

    return {'answer': answer, 'data': df}


def get_summary(df):
    """Generate a quick summary of a dataframe."""
    return {
        'rows': len(df),
        'columns': list(df.columns),
        'dtypes': df.dtypes.to_dict(),
        'numeric_summary': df.describe().to_dict() if not df.select_dtypes(include='number').empty else {},
    }
