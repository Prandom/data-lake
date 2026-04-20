"""
Tests for app/indexing/embeddings.py

Covers:
- EmbeddingProvider interface
- LocalEmbeddings (sentence-transformers)
- Provider factory (get_provider)
- Embedding dimensions and normalization
"""

import pytest
import numpy as np
from app.indexing.embeddings import (
    LocalEmbeddings,
    EmbeddingProvider,
    get_provider,
    _provider_instance,
)
import app.indexing.embeddings as embeddings_module


@pytest.fixture(scope="module")
def local_provider():
    """Create a LocalEmbeddings provider (shared across tests for speed)."""
    return LocalEmbeddings()


class TestLocalEmbeddings:
    """Tests for the local sentence-transformers provider."""

    def test_is_embedding_provider(self, local_provider):
        assert isinstance(local_provider, EmbeddingProvider)

    def test_embed_returns_list_of_floats(self, local_provider):
        result = local_provider.embed("hello world")
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)

    def test_embed_dimension(self, local_provider):
        result = local_provider.embed("test text")
        assert len(result) == local_provider.get_dimension()
        assert local_provider.get_dimension() == 384  # MiniLM-L6-v2

    def test_embed_empty_string(self, local_provider):
        result = local_provider.embed("")
        assert len(result) == 384
        # Empty string should return zero vector
        assert all(x == 0.0 for x in result)

    def test_batch_embed(self, local_provider):
        texts = ["hello", "world", "test"]
        results = local_provider.batch_embed(texts)
        assert len(results) == 3
        assert all(len(r) == 384 for r in results)

    def test_batch_embed_empty_list(self, local_provider):
        results = local_provider.batch_embed([])
        assert results == []

    def test_similar_texts_have_similar_embeddings(self, local_provider):
        """Semantic similarity: related texts should be closer together."""
        emb_a = np.array(local_provider.embed("binary search tree algorithm"))
        emb_b = np.array(local_provider.embed("data structure for searching"))
        emb_c = np.array(local_provider.embed("chocolate cake recipe"))

        # Cosine similarity
        sim_ab = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
        sim_ac = np.dot(emb_a, emb_c) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_c))

        # "binary search" and "searching data structure" should be more similar
        # than "binary search" and "chocolate cake"
        assert sim_ab > sim_ac

    def test_normalized_embeddings(self, local_provider):
        """Embeddings should be L2-normalized (unit vectors)."""
        result = np.array(local_provider.embed("test text"))
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01  # Should be ~1.0


class TestGetProvider:
    """Tests for the provider factory."""

    def test_returns_provider_instance(self):
        # Reset singleton
        embeddings_module._provider_instance = None
        provider = get_provider()
        assert isinstance(provider, EmbeddingProvider)

    def test_singleton_pattern(self):
        # Reset singleton
        embeddings_module._provider_instance = None
        p1 = get_provider()
        p2 = get_provider()
        assert p1 is p2  # Same instance

    def test_default_is_local(self, monkeypatch):
        embeddings_module._provider_instance = None
        monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
        provider = get_provider()
        assert isinstance(provider, LocalEmbeddings)

    def test_explicit_local_config(self, monkeypatch):
        embeddings_module._provider_instance = None
        monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
        provider = get_provider()
        assert isinstance(provider, LocalEmbeddings)
