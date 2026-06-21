"""
Week 3: Text embeddings — pluggable provider pattern.

Default: local sentence-transformers (all-MiniLM-L6-v2).
Swap to OpenAI or any other provider by changing get_provider().

Local model:
  - 384 dimensions
  - ~80MB download (one-time)
  - Runs on CPU, no API key needed
"""

import os
from abc import ABC, abstractmethod
from typing import List, Optional


class EmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single text string."""
        ...

    @abstractmethod
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple text strings."""
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the embedding dimension for this provider."""
        ...


class LocalEmbeddings(EmbeddingProvider):
    """
    Local embeddings via sentence-transformers.

    Uses all-MiniLM-L6-v2 by default:
      - 384 dimensions
      - Fast on CPU
      - No API key, no cost, works offline

    First call downloads the model (~80MB). Cached after that.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> List[float]:
        """Embed a single text."""
        if not text.strip():
            return [0.0] * self._dimension
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in one batch (more efficient)."""
        if not texts:
            return []
        embeddings = self.model.encode(texts, normalize_embeddings=True, batch_size=32)
        return embeddings.tolist()

    def get_dimension(self) -> int:
        return self._dimension


class OpenAIEmbeddings(EmbeddingProvider):
    """
    OpenAI embeddings via text-embedding-3-small.

    Requires OPENAI_API_KEY in .env.
    Swap in later when you have an API key.

    Usage:
        provider = OpenAIEmbeddings()
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package required for OpenAIEmbeddings. "
                "Install with: pip install openai"
            )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment / .env")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._dimension = 1536

    def embed(self, text: str) -> List[float]:
        if not text.strip():
            return [0.0] * self._dimension
        response = self.client.embeddings.create(
            input=text.strip(),
            model=self.model,
        )
        return response.data[0].embedding

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            input=texts,
            model=self.model,
        )
        return [data.embedding for data in response.data]

    def get_dimension(self) -> int:
        return self._dimension


# ---- Provider factory -------------------------------------------------------

_provider_instance: Optional[EmbeddingProvider] = None


def get_provider() -> EmbeddingProvider:
    """
    Return the configured embedding provider (singleton).

    Set EMBEDDING_PROVIDER=openai in .env to switch to OpenAI.
    Default: local (sentence-transformers).
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = os.getenv("EMBEDDING_PROVIDER", "local").lower()

    if provider_name == "openai":
        _provider_instance = OpenAIEmbeddings()
    else:
        _provider_instance = LocalEmbeddings()

    print(f"Embedding provider: {_provider_instance.__class__.__name__} "
          f"({_provider_instance.get_dimension()} dims)")

    return _provider_instance
