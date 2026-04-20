"""
Week 3: Search API endpoints.

POST /api/search/       — semantic search across indexed files
POST /api/search/index  — index files marked needs_sync=True
GET  /api/search/stats  — vector store statistics
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.session import get_db
from ..db.models import FileMetadata
from ..indexing.vector_store import VectorStore
from ..indexing.chunker import chunk_file
from ..indexing.embeddings import get_provider


router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5
    threshold: float = 0.3


@router.post("/")
async def search_files(
    request: SearchRequest,
    db: Session = Depends(get_db),
):
    """
    Semantic search across indexed files.

    Example:
      POST /api/search/ {"query": "binary search tree"}
    """
    provider = get_provider()
    vector_store = VectorStore(db=db, embedding_provider=provider)

    results = vector_store.search(
        request.query,
        n_results=request.n_results,
        threshold=request.threshold,
    )

    return {
        "query": request.query,
        "results": results,
        "total": len(results),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/index")
async def index_pending_files(db: Session = Depends(get_db)):
    """
    Index files marked needs_sync=True.

    Chunks each pending file, embeds, stores in FAISS + SQLite,
    then marks the file as synced.
    """
    pending = (
        db.query(FileMetadata)
        .filter(FileMetadata.needs_sync == True)
        .limit(100)  # Batch to avoid memory issues
        .all()
    )

    provider = get_provider()
    vector_store = VectorStore(db=db, embedding_provider=provider)

    indexed = 0
    skipped = 0
    errors = []

    for file in pending:
        try:
            chunks = chunk_file(Path(file.path))
            if not chunks:
                skipped += 1
                file.needs_sync = False
                continue

            # Remove old chunks for this file before re-indexing
            vector_store.delete_by_path(file.path)
            vector_store.add_chunks(chunks)
            file.needs_sync = False
            indexed += 1
        except Exception as e:
            errors.append({"path": file.path, "error": str(e)})

    db.commit()

    return {
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "vector_store": vector_store.get_stats(),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/stats")
async def search_stats(db: Session = Depends(get_db)):
    """Get vector store and embedding provider statistics."""
    provider = get_provider()
    vector_store = VectorStore(db=db, embedding_provider=provider)
    return {
        "vector_store": vector_store.get_stats(),
        "embedding_provider": provider.__class__.__name__,
        "embedding_dimensions": provider.get_dimension(),
        "timestamp": datetime.now().isoformat(),
    }
