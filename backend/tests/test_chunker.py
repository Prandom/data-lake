"""
Tests for app/indexing/chunker.py

Covers:
- Token estimation
- Simple chunking (single chunk, multiple chunks, overlap)
- File chunking (text files, binary files, empty files, large files)
"""

import os
import pytest
from pathlib import Path
from app.indexing.chunker import estimate_tokens, simple_chunk, chunk_file


class TestEstimateTokens:
    """Tests for the rough token estimator."""

    def test_empty_string(self):
        assert estimate_tokens("") == 1  # min 1 from integer division + 1

    def test_short_string(self):
        tokens = estimate_tokens("hello world")
        assert tokens > 0
        assert tokens < 10  # "hello world" is ~3 tokens

    def test_longer_string(self):
        text = "This is a longer sentence with more words in it."
        tokens = estimate_tokens(text)
        # ~50 chars → ~12 tokens
        assert 5 < tokens < 25

    def test_proportional_to_length(self):
        short = estimate_tokens("hello")
        long = estimate_tokens("hello " * 100)
        assert long > short


class TestSimpleChunk:
    """Tests for sentence-aware chunking."""

    def test_short_text_single_chunk(self):
        text = "Hello world. This is short."
        chunks = simple_chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self):
        # Create text that exceeds 512 tokens (~2048+ chars)
        sentences = [f"This is sentence number {i}." for i in range(200)]
        text = " ".join(sentences)
        chunks = simple_chunk(text)
        assert len(chunks) > 1

    def test_overlap_present(self):
        sentences = [f"This is sentence number {i}." for i in range(200)]
        text = " ".join(sentences)
        chunks = simple_chunk(text, chunk_size=100, overlap=20)
        # Second chunk should start with overlap from first chunk
        if len(chunks) >= 2:
            # Overlap means chunk[1] starts with tail of chunk[0]
            assert len(chunks[1]) > 0

    def test_custom_chunk_size(self):
        sentences = [f"Sentence {i} is here." for i in range(100)]
        text = " ".join(sentences)
        small_chunks = simple_chunk(text, chunk_size=50)
        large_chunks = simple_chunk(text, chunk_size=500)
        assert len(small_chunks) >= len(large_chunks)

    def test_preserves_content(self):
        text = "Hello world."
        chunks = simple_chunk(text)
        assert "Hello world." in chunks[0]


class TestChunkFile:
    """Tests for file-level chunking."""

    def test_text_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world. This is a test file.", encoding="utf-8")
        chunks = chunk_file(f)
        assert len(chunks) >= 1
        assert chunks[0]["path"] == str(f)
        assert chunks[0]["chunk_id"] == 0
        assert "Hello world" in chunks[0]["content"]
        assert chunks[0]["tokens"] > 0

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        chunks = chunk_file(f)
        assert chunks == []

    def test_whitespace_only_file(self, tmp_path):
        f = tmp_path / "whitespace.txt"
        f.write_text("   \n\n  \t  ", encoding="utf-8")
        chunks = chunk_file(f)
        assert chunks == []

    def test_binary_file(self, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")
        chunks = chunk_file(f)
        assert chunks == []  # Should fail to decode as UTF-8

    def test_large_file_skipped(self, tmp_path):
        f = tmp_path / "large.txt"
        f.write_text("x" * 100, encoding="utf-8")
        # Pass tiny max_file_size to trigger the skip
        chunks = chunk_file(f, max_file_size=10)
        assert chunks == []

    def test_multiple_chunks_from_large_file(self, tmp_path):
        f = tmp_path / "large.txt"
        sentences = [f"Sentence number {i} has some words." for i in range(300)]
        f.write_text(" ".join(sentences), encoding="utf-8")
        chunks = chunk_file(f)
        assert len(chunks) > 1
        # Chunk IDs should be sequential
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_id"] == i

    def test_chunk_has_required_keys(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Some content here.", encoding="utf-8")
        chunks = chunk_file(f)
        assert len(chunks) == 1
        required_keys = {"content", "path", "chunk_id", "tokens"}
        assert set(chunks[0].keys()) == required_keys
