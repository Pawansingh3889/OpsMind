"""Document search with pluggable backend: PostgreSQL+pgvector or ChromaDB.

Reads OPSMIND_VECTOR_DB from config to choose the backend.
Falls back to ChromaDB if PostgreSQL is unavailable.
"""
import os
import logging
import json
from datetime import datetime, timezone

from config import VECTOR_DB, VECTOR_PG_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend state
# ---------------------------------------------------------------------------
_backend = None          # "pgvector" or "chromadb"
_pg_engine = None
_pg_Session = None
_embedding_model = None

# ---------------------------------------------------------------------------
# Embedding helper (shared by both backends)
# ---------------------------------------------------------------------------

def _get_embedding_model():
    """Lazy-load the sentence-transformer model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _embed(texts):
    """Return a list of embedding vectors for the given texts."""
    model = _get_embedding_model()
    return model.encode(texts, show_progress_bar=False).tolist()


# ---------------------------------------------------------------------------
# PostgreSQL + pgvector backend
# ---------------------------------------------------------------------------
_PG_TABLE_CREATED = False


def _pg_engine_init():
    """Create the SQLAlchemy engine + sessionmaker for pgvector."""
    global _pg_engine, _pg_Session
    if _pg_engine is not None:
        return

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    _pg_engine = create_engine(VECTOR_PG_URL, pool_pre_ping=True)
    _pg_Session = sessionmaker(bind=_pg_engine)


def _pg_ensure_table():
    """Create the documents table (with pgvector extension) if it doesn't exist."""
    global _PG_TABLE_CREATED
    if _PG_TABLE_CREATED:
        return
    _pg_engine_init()
    from sqlalchemy import text
    with _pg_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS documents (
                id          TEXT PRIMARY KEY,
                text        TEXT NOT NULL,
                embedding   vector(384),
                metadata    JSONB DEFAULT '{}',
                created_at  TIMESTAMPTZ DEFAULT now()
            )
        """))
        # Index for fast cosine-similarity search
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
    _PG_TABLE_CREATED = True


def _pg_add_document(doc_id, text_content, metadata=None):
    _pg_ensure_table()
    vec = _embed([text_content])[0]
    meta_json = json.dumps(metadata or {})
    from sqlalchemy import text
    with _pg_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO documents (id, text, embedding, metadata)
                VALUES (:id, :text, :embedding, :metadata)
                ON CONFLICT (id) DO UPDATE
                SET text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
            """),
            {"id": doc_id, "text": text_content,
             "embedding": str(vec), "metadata": meta_json},
        )


def _pg_add_documents_batch(ids, texts, metadatas=None):
    _pg_ensure_table()
    vecs = _embed(texts)
    metas = metadatas or [{}] * len(ids)
    from sqlalchemy import text
    with _pg_engine.begin() as conn:
        for i, doc_id in enumerate(ids):
            conn.execute(
                text("""
                    INSERT INTO documents (id, text, embedding, metadata)
                    VALUES (:id, :text, :embedding, :metadata)
                    ON CONFLICT (id) DO UPDATE
                    SET text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata
                """),
                {"id": doc_id, "text": texts[i],
                 "embedding": str(vecs[i]),
                 "metadata": json.dumps(metas[i])},
            )


def _pg_search(query, n_results=5):
    _pg_ensure_table()
    vec = _embed([query])[0]
    from sqlalchemy import text
    with _pg_engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, text, metadata,
                       embedding <=> :vec AS distance
                FROM documents
                ORDER BY embedding <=> :vec
                LIMIT :n
            """),
            {"vec": str(vec), "n": n_results},
        ).fetchall()
    return [
        {"id": r[0], "text": r[1],
         "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
         "distance": float(r[3])}
        for r in rows
    ]


def _pg_get_doc_count():
    _pg_ensure_table()
    from sqlalchemy import text
    with _pg_engine.connect() as conn:
        row = conn.execute(text("SELECT count(*) FROM documents")).fetchone()
    return row[0]


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def _resolve_backend():
    """Choose pgvector or chromadb. Falls back to chromadb on PG errors."""
    global _backend

    if _backend is not None:
        return _backend

    if VECTOR_DB == "pgvector" and VECTOR_PG_URL:
        try:
            _pg_engine_init()
            # Quick connectivity check
            from sqlalchemy import text
            with _pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            _backend = "pgvector"
            logger.info("Vector backend: PostgreSQL + pgvector")
        except Exception as exc:
            logger.warning(
                "pgvector requested but PostgreSQL unavailable (%s). "
                "Falling back to ChromaDB.", exc
            )
            _backend = "chromadb"
    else:
        _backend = "chromadb"

    return _backend


# ---------------------------------------------------------------------------
# ChromaDB delegates (import the original module)
# ---------------------------------------------------------------------------

def _chroma():
    """Return the original ChromaDB module."""
    import modules.doc_search as _ds
    return _ds


# ---------------------------------------------------------------------------
# Public API -- mirrors modules/doc_search.py
# ---------------------------------------------------------------------------

def add_document(doc_id, text_content, metadata=None):
    """Add a single document chunk."""
    if _resolve_backend() == "pgvector":
        _pg_add_document(doc_id, text_content, metadata)
    else:
        _chroma().add_document(doc_id, text_content, metadata)


def add_documents_batch(ids, texts, metadatas=None):
    """Add multiple document chunks at once."""
    if _resolve_backend() == "pgvector":
        _pg_add_documents_batch(ids, texts, metadatas)
    else:
        _chroma().add_documents_batch(ids, texts, metadatas)


def search(query, n_results=5):
    """Search documents for relevant content."""
    if _resolve_backend() == "pgvector":
        return _pg_search(query, n_results)
    return _chroma().search(query, n_results)


def ingest_pdf(filepath):
    """Ingest a PDF file into the vector store."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return 0

    reader = PdfReader(filepath)
    filename = os.path.basename(filepath)
    chunks_added = 0

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or len(text.strip()) < 50:
            continue

        words = text.split()
        chunk_size = 100
        overlap = 20

        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i : i + chunk_size])
            if len(chunk.strip()) < 50:
                continue

            doc_id = f"{filename}_p{page_num + 1}_c{i}"
            add_document(
                doc_id,
                chunk,
                {
                    "source": filename,
                    "page": page_num + 1,
                    "category": _guess_category(filename),
                },
            )
            chunks_added += 1

    return chunks_added


def ingest_text(filename, text, category="general"):
    """Ingest raw text content as a document."""
    words = text.split()
    chunk_size = 100
    overlap = 20
    chunks_added = 0

    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if len(chunk.strip()) < 50:
            continue
        doc_id = f"{filename}_c{i}"
        add_document(doc_id, chunk, {"source": filename, "category": category})
        chunks_added += 1

    return chunks_added


def get_doc_count():
    """Return total number of document chunks in the store."""
    if _resolve_backend() == "pgvector":
        return _pg_get_doc_count()
    return _chroma().get_doc_count()


def _guess_category(filename):
    """Guess document category from filename."""
    fn = filename.lower()
    if "haccp" in fn:
        return "HACCP"
    if "brc" in fn or "audit" in fn:
        return "Audit"
    if "sop" in fn:
        return "SOP"
    if "spec" in fn:
        return "Customer Spec"
    if "staff" in fn or "handbook" in fn:
        return "HR"
    if "clean" in fn:
        return "SOP"
    return "General"
