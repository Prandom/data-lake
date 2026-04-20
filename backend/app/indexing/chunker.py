"""
Week 3: Document chunking.

Splits large files into 512-token chunks for embedding.
"""

import re
from typing import List
from pathlib import Path


CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars/token)."""
    return len(text.encode("utf-8")) // 4 + 1


def simple_chunk(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Simple fixed-size chunking with overlap.

    Keeps sentences intact where possible.
    """
    if estimate_tokens(text) <= chunk_size:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        test_chunk = current_chunk + " " + sentence if current_chunk else sentence

        if estimate_tokens(test_chunk) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk = test_chunk

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add overlap between chunks
    overlapped = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            overlapped.append(chunks[i - 1][-overlap:] + " " + chunk)
        else:
            overlapped.append(chunk)

    return overlapped


def chunk_file(filepath: Path, max_file_size: int = 10_000_000) -> List[dict]:
    """
    Chunk a single file into searchable pieces.

    Returns: [{"content": "...", "path": "...", "chunk_id": 0}, ...]
    """
    if filepath.stat().st_size > max_file_size:
        return []

    try:
        text = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    if not text.strip():
        return []

    chunks = simple_chunk(text)

    return [
        {
            "content": chunk,
            "path": str(filepath),
            "chunk_id": i,
            "tokens": estimate_tokens(chunk),
        }
        for i, chunk in enumerate(chunks)
    ]
