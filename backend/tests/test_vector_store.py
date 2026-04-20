"""
Tests for app/indexing/vector_store.py

Covers:
- VectorStore initialization (fresh + from disk)
- Adding chunks (single, batch)
- Semantic search (with threshold filtering)
- Deleting chunks by path
- Persistence (save/load FAISS index)
- Stats
"""

import os
import shutil
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, ChunkMetadata
from app.indexing.vector_store import VectorStore
from app.indexing.embeddings import LocalEmbeddings


@pytest.fixture(scope="module")
def embedding_provider():
    """Shared embedding provider (avoids reloading model per test)."""
    return LocalEmbeddings()


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def faiss_dir(tmp_path):
    """Temporary directory for FAISS index files."""
    d = tmp_path / "faiss_test"
    d.mkdir()
    return str(d)


@pytest.fixture
def vector_store(db_session, faiss_dir, embedding_provider):
    """VectorStore with fresh DB and temp FAISS directory."""
    return VectorStore(
        db=db_session,
        persist_directory=faiss_dir,
        embedding_provider=embedding_provider,
    )


def make_chunks(texts, path="test/file.txt"):
    """Helper to create chunk dicts."""
    return [
        {"content": text, "path": path, "chunk_id": i, "tokens": len(text) // 4}
        for i, text in enumerate(texts)
    ]


class TestVectorStoreInit:
    """Tests for initialization."""

    def test_creates_empty_index(self, vector_store):
        assert vector_store.index.ntotal == 0

    def test_creates_persist_directory(self, db_session, tmp_path, embedding_provider):
        new_dir = str(tmp_path / "new_faiss_dir")
        vs = VectorStore(db=db_session, persist_directory=new_dir, embedding_provider=embedding_provider)
        assert Path(new_dir).exists()

    def test_loads_existing_index(self, db_session, faiss_dir, embedding_provider):
        # Create and populate a store
        vs1 = VectorStore(db=db_session, persist_directory=faiss_dir, embedding_provider=embedding_provider)
        vs1.add_chunks(make_chunks(["hello world"]))
        assert vs1.index.ntotal == 1

        # Create a new store pointing at same directory — should load the index
        vs2 = VectorStore(db=db_session, persist_directory=faiss_dir, embedding_provider=embedding_provider)
        assert vs2.index.ntotal == 1


class TestAddChunks:
    """Tests for adding chunks."""

    def test_add_single_chunk(self, vector_store, db_session):
        chunks = make_chunks(["Binary search is a divide and conquer algorithm."])
        vector_store.add_chunks(chunks)
        assert vector_store.index.ntotal == 1

        # Check metadata in SQLite
        meta = db_session.query(ChunkMetadata).first()
        assert meta is not None
        assert meta.faiss_id == 0
        assert meta.chunk_id == 0
        assert "Binary search" in meta.content

    def test_add_multiple_chunks(self, vector_store, db_session):
        chunks = make_chunks([
            "Binary search trees store data in sorted order.",
            "Hash tables provide O(1) average lookup time.",
            "Linked lists allow efficient insertion and deletion.",
        ])
        vector_store.add_chunks(chunks)
        assert vector_store.index.ntotal == 3
        assert db_session.query(ChunkMetadata).count() == 3

    def test_add_empty_list(self, vector_store):
        vector_store.add_chunks([])
        assert vector_store.index.ntotal == 0

    def test_faiss_ids_are_sequential(self, vector_store, db_session):
        chunks = make_chunks(["first", "second", "third"])
        vector_store.add_chunks(chunks)
        metas = db_session.query(ChunkMetadata).order_by(ChunkMetadata.faiss_id).all()
        assert [m.faiss_id for m in metas] == [0, 1, 2]

    def test_add_chunks_from_multiple_files(self, vector_store, db_session):
        chunks_a = make_chunks(["Content from file A"], path="fileA.txt")
        chunks_b = make_chunks(["Content from file B"], path="fileB.txt")
        vector_store.add_chunks(chunks_a)
        vector_store.add_chunks(chunks_b)
        assert vector_store.index.ntotal == 2
        assert db_session.query(ChunkMetadata).count() == 2


class TestSearch:
    """Tests for semantic search."""

    def test_search_returns_results(self, vector_store):
        chunks = make_chunks([
            "Binary search is a fundamental algorithm in computer science.",
            "Pancakes are made with flour, eggs, and milk.",
            "Trees are hierarchical data structures with nodes.",
        ])
        vector_store.add_chunks(chunks)

        results = vector_store.search("algorithm for searching in sorted arrays")
        assert len(results) > 0
        # First result should be about binary search
        assert "Binary search" in results[0]["content"] or "algorithm" in results[0]["content"]

    def test_search_empty_index(self, vector_store):
        results = vector_store.search("anything")
        assert results == []

    def test_search_respects_n_results(self, vector_store):
        chunks = make_chunks([f"Topic {i} discussion." for i in range(10)])
        vector_store.add_chunks(chunks)
        results = vector_store.search("topic", n_results=3, threshold=0.0)
        assert len(results) <= 3

    def test_search_respects_threshold(self, vector_store):
        chunks = make_chunks([
            "Deep learning neural networks.",
            "Chocolate cake recipe with vanilla frosting.",
        ])
        vector_store.add_chunks(chunks)
        # Very high threshold should filter most results
        results = vector_store.search("recipe", threshold=0.99)
        assert len(results) == 0

    def test_search_result_has_required_keys(self, vector_store):
        chunks = make_chunks(["Some content for testing."])
        vector_store.add_chunks(chunks)
        results = vector_store.search("testing", threshold=0.0)
        assert len(results) > 0
        required_keys = {"content", "path", "chunk_id", "similarity"}
        assert set(results[0].keys()) == required_keys

    def test_search_similarity_is_float(self, vector_store):
        chunks = make_chunks(["Hello world."])
        vector_store.add_chunks(chunks)
        results = vector_store.search("hello", threshold=0.0)
        assert isinstance(results[0]["similarity"], float)


class TestDeleteByPath:
    """Tests for deleting chunks by file path."""

    def test_delete_removes_from_sqlite(self, vector_store, db_session):
        chunks_a = make_chunks(["Content A"], path="a.txt")
        chunks_b = make_chunks(["Content B"], path="b.txt")
        vector_store.add_chunks(chunks_a)
        vector_store.add_chunks(chunks_b)

        vector_store.delete_by_path("a.txt")

        remaining = db_session.query(ChunkMetadata).all()
        assert len(remaining) == 1
        assert remaining[0].path == "b.txt"

    def test_delete_rebuilds_faiss_index(self, vector_store, db_session):
        chunks_a = make_chunks(["Content A"], path="a.txt")
        chunks_b = make_chunks(["Content B"], path="b.txt")
        vector_store.add_chunks(chunks_a)
        vector_store.add_chunks(chunks_b)
        assert vector_store.index.ntotal == 2

        vector_store.delete_by_path("a.txt")
        assert vector_store.index.ntotal == 1

    def test_delete_nonexistent_path(self, vector_store, db_session):
        chunks = make_chunks(["Some content"], path="exists.txt")
        vector_store.add_chunks(chunks)
        vector_store.delete_by_path("nonexistent.txt")
        assert vector_store.index.ntotal == 1  # Unchanged

    def test_delete_all_paths(self, vector_store, db_session):
        chunks = make_chunks(["Only content"], path="only.txt")
        vector_store.add_chunks(chunks)
        vector_store.delete_by_path("only.txt")
        assert vector_store.index.ntotal == 0
        assert db_session.query(ChunkMetadata).count() == 0


class TestGetStats:
    """Tests for stats reporting."""

    def test_stats_empty(self, vector_store):
        stats = vector_store.get_stats()
        assert stats["total_vectors"] == 0
        assert stats["dimension"] == 384

    def test_stats_after_add(self, vector_store):
        vector_store.add_chunks(make_chunks(["chunk1", "chunk2"]))
        stats = vector_store.get_stats()
        assert stats["total_vectors"] == 2
        assert stats["index_size_bytes"] > 0
