"""
Week 3: FAISS + SQLite vector store.

FAISS handles high-performance vector similarity search.
SQLite (via ChunkMetadata) stores the actual text + metadata.

Architecture:
  - FAISS IndexFlatIP for cosine similarity on normalized vectors
  - ChunkMetadata table maps FAISS integer IDs → text content + file paths
  - Index persisted to disk as faiss_index.bin
"""

import os
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from .embeddings import EmbeddingProvider, get_provider


class VectorStore:
    """
    Local FAISS vector store with SQLite metadata.

    Uses a pluggable EmbeddingProvider for consistent embedding
    across both indexing and search operations.
    """

    def __init__(
        self,
        db: Session,
        persist_directory: str = "faiss_data",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.db = db
        self.provider = embedding_provider or get_provider()
        self.dimension = self.provider.get_dimension()
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(exist_ok=True)
        self.index_path = self.persist_dir / "faiss_index.bin"

        # Load existing index or create new
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
        else:
            # IndexFlatIP = Inner Product (cosine similarity on normalized vectors)
            self.index = faiss.IndexFlatIP(self.dimension)

    def _save_index(self):
        """Persist the FAISS index to disk."""
        faiss.write_index(self.index, str(self.index_path))

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ):
        """
        Add file chunks to the vector store.

        chunks: [{"content": "...", "path": "...", "chunk_id": 0, "tokens": N}, ...]

        Steps:
          1. Embed all chunk texts via the provider
          2. Add vectors to FAISS index
          3. Store metadata in SQLite ChunkMetadata table
        """
        from ..db.models import ChunkMetadata

        if not chunks:
            return

        texts = [c["content"] for c in chunks]

        # Embed and normalize for cosine similarity
        embeddings = self.provider.batch_embed(texts)
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        # Starting FAISS ID = current index size
        start_id = self.index.ntotal

        # Add to FAISS
        self.index.add(vectors)

        # Store metadata in SQLite
        for i, chunk in enumerate(chunks):
            meta = ChunkMetadata(
                faiss_id=start_id + i,
                path=chunk["path"],
                chunk_id=chunk["chunk_id"],
                content=chunk["content"],
                tokens=chunk.get("tokens"),
            )
            self.db.add(meta)

        self.db.flush()
        self._save_index()

    def search(
        self,
        query: str,
        n_results: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search.

        Returns top matches above similarity threshold.

        Flow:
          1. Embed query text
          2. FAISS search → top-N (faiss_ids, similarity scores)
          3. SQLite lookup → content + metadata for those IDs
          4. Filter by threshold, return merged results
        """
        from ..db.models import ChunkMetadata

        if self.index.ntotal == 0:
            return []

        # Embed and normalize query
        query_embedding = self.provider.embed(query)
        query_vector = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vector)

        # Search FAISS (returns distances and indices)
        k = min(n_results, self.index.ntotal)
        scores, indices = self.index.search(query_vector, k)

        hits = []
        for score, faiss_id in zip(scores[0], indices[0]):
            if faiss_id == -1:  # FAISS returns -1 for unfilled slots
                continue

            similarity = float(score)  # Already cosine similarity (IP on normalized)
            if similarity < threshold:
                continue

            # Look up metadata in SQLite
            meta = (
                self.db.query(ChunkMetadata)
                .filter(ChunkMetadata.faiss_id == int(faiss_id))
                .first()
            )

            if meta:
                hits.append({
                    "content": meta.content,
                    "path": meta.path,
                    "chunk_id": meta.chunk_id,
                    "similarity": round(similarity, 4),
                })

        return hits

    def delete_by_path(self, path: str):
        """
        Delete all chunks for a given file path.

        Since FAISS doesn't support in-place deletion, we:
          1. Get all chunks NOT matching this path from SQLite
          2. Rebuild the FAISS index from those remaining chunks
          3. Update faiss_id references in SQLite
        """
        from ..db.models import ChunkMetadata

        # Get chunks to keep
        keep_chunks = (
            self.db.query(ChunkMetadata)
            .filter(ChunkMetadata.path != path)
            .order_by(ChunkMetadata.faiss_id)
            .all()
        )

        # Delete all chunk_metadata for this path
        self.db.query(ChunkMetadata).filter(
            ChunkMetadata.path == path
        ).delete()

        # Rebuild FAISS index if there are remaining chunks
        if keep_chunks:
            texts = [c.content for c in keep_chunks]
            embeddings = self.provider.batch_embed(texts)
            vectors = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(vectors)

            # Create fresh index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vectors)

            # Update faiss_ids in SQLite
            for i, chunk in enumerate(keep_chunks):
                chunk.faiss_id = i
        else:
            # No chunks left, create empty index
            self.index = faiss.IndexFlatIP(self.dimension)

        self.db.flush()
        self._save_index()

    def get_stats(self) -> Dict[str, Any]:
        """Return basic stats about the vector store."""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_path": str(self.index_path),
            "index_size_bytes": (
                self.index_path.stat().st_size
                if self.index_path.exists()
                else 0
            ),
        }
