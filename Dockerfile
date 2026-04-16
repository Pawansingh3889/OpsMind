FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2, pyodbc, and ODBC drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    unixodbc-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user for security (Nezbeda pattern)
RUN useradd -m -u 1000 opsmind && \
    mkdir -p /app/data /app/logs && \
    chown -R opsmind:opsmind /app

USER opsmind

VOLUME ["/app/data", "/app/logs"]

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
