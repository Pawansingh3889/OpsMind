"""Document search using ChromaDB for semantic search over factory PDFs."""
import os
import chromadb
from chromadb.config import Settings
from config import CHROMA_DIR

# Initialize ChromaDB
_client = None
_collection = None


def _get_collection():
    """Get or create the ChromaDB collection."""
    global _client, _collection
    if _collection is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = _client.get_or_create_collection(
            name="factory_docs",
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def add_document(doc_id, text, metadata=None):
    """Add a document chunk to the vector store."""
    collection = _get_collection()
    collection.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[metadata or {}]
    )


def add_documents_batch(ids, texts, metadatas=None):
    """Add multiple document chunks at once."""
    collection = _get_collection()
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas or [{}] * len(ids)
    )


def search(query, n_results=5):
    """Search documents for relevant content."""
    collection = _get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )

    output = []
    for i in range(len(results['ids'][0])):
        output.append({
            'id': results['ids'][0][i],
            'text': results['documents'][0][i],
            'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
            'distance': results['distances'][0][i] if results['distances'] else 0
        })
    return output


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

        # Split into chunks of ~500 chars with overlap
        words = text.split()
        chunk_size = 100  # words
        overlap = 20

        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) < 50:
                continue

            doc_id = f"{filename}_p{page_num + 1}_c{i}"
            add_document(doc_id, chunk, {
                'source': filename,
                'page': page_num + 1,
                'category': _guess_category(filename)
            })
            chunks_added += 1

    return chunks_added


def ingest_text(filename, text, category='general'):
    """Ingest raw text content as a document."""
    words = text.split()
    chunk_size = 100
    overlap = 20
    chunks_added = 0

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if len(chunk.strip()) < 50:
            continue
        doc_id = f"{filename}_c{i}"
        add_document(doc_id, chunk, {
            'source': filename,
            'category': category
        })
        chunks_added += 1

    return chunks_added


def _guess_category(filename):
    """Guess document category from filename."""
    fn = filename.lower()
    if 'haccp' in fn:
        return 'HACCP'
    if 'brc' in fn or 'audit' in fn:
        return 'Audit'
    if 'sop' in fn:
        return 'SOP'
    if 'spec' in fn:
        return 'Customer Spec'
    if 'staff' in fn or 'handbook' in fn:
        return 'HR'
    if 'clean' in fn:
        return 'SOP'
    return 'General'


def get_doc_count():
    """Return total number of document chunks in the store."""
    collection = _get_collection()
    return collection.count()
