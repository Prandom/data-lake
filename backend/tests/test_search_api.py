"""
Tests for app/api/search.py (search API endpoints)

Covers:
- POST /api/search/ (semantic search)
- POST /api/search/index (index pending files)
- GET /api/search/stats
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.db.models import FileMetadata


class TestSearchEndpoint:
    """Tests for POST /api/search/"""

    def test_search_empty_index(self, client):
        response = client.post("/api/search/", json={"query": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["results"] == []
        assert data["total"] == 0
        assert "timestamp" in data

    def test_search_with_custom_params(self, client):
        response = client.post("/api/search/", json={
            "query": "algorithm",
            "n_results": 3,
            "threshold": 0.5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0  # Empty index

    def test_search_missing_query(self, client):
        response = client.post("/api/search/", json={})
        assert response.status_code == 422  # Validation error


class TestIndexEndpoint:
    """Tests for POST /api/search/index"""

    def test_index_no_pending_files(self, client):
        response = client.post("/api/search/index")
        assert response.status_code == 200
        data = response.json()
        assert data["indexed"] == 0
        assert data["skipped"] == 0
        assert "vector_store" in data

    def test_index_with_pending_files(self, client, test_db, temp_dir):
        # Create a real text file
        filepath = os.path.join(temp_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("Binary search trees are hierarchical data structures. "
                    "They allow efficient searching, insertion, and deletion.")

        # Add to database as needing sync
        from datetime import datetime
        file_meta = FileMetadata(
            path=filepath,
            size=os.path.getsize(filepath),
            modified=datetime.fromtimestamp(os.path.getmtime(filepath)),
            needs_sync=True,
        )
        test_db.add(file_meta)
        test_db.commit()

        # Trigger indexing
        response = client.post("/api/search/index")
        assert response.status_code == 200
        data = response.json()
        assert data["indexed"] == 1
        assert data["skipped"] == 0
        assert data["vector_store"]["total_vectors"] > 0

    def test_index_skips_binary_files(self, client, test_db, temp_dir):
        # Create a binary file
        filepath = os.path.join(temp_dir, "binary.bin")
        with open(filepath, "wb") as f:
            f.write(b"\x00\x01\x02\xff\xfe\xfd" * 100)

        from datetime import datetime
        file_meta = FileMetadata(
            path=filepath,
            size=os.path.getsize(filepath),
            modified=datetime.fromtimestamp(os.path.getmtime(filepath)),
            needs_sync=True,
        )
        test_db.add(file_meta)
        test_db.commit()

        response = client.post("/api/search/index")
        data = response.json()
        assert data["indexed"] == 0
        assert data["skipped"] == 1


class TestSearchAfterIndex:
    """Integration test: index files then search."""

    def test_index_then_search(self, client, test_db, temp_dir):
        # Create files with distinct content
        for name, content in [
            ("algorithms.txt", "Binary search is a divide and conquer algorithm used for sorted arrays. "
                               "It has O(log n) time complexity and is very efficient."),
            ("recipes.txt", "Chocolate cake requires flour, sugar, cocoa powder, eggs, and butter. "
                            "Bake at 350 degrees for 30 minutes."),
        ]:
            filepath = os.path.join(temp_dir, name)
            with open(filepath, "w") as f:
                f.write(content)

            from datetime import datetime
            file_meta = FileMetadata(
                path=filepath,
                size=os.path.getsize(filepath),
                modified=datetime.fromtimestamp(os.path.getmtime(filepath)),
                needs_sync=True,
            )
            test_db.add(file_meta)

        test_db.commit()

        # Index
        idx_response = client.post("/api/search/index")
        assert idx_response.json()["indexed"] == 2

        # Search for algorithms
        search_response = client.post("/api/search/", json={
            "query": "searching algorithm",
            "threshold": 0.0,
        })
        data = search_response.json()
        assert data["total"] > 0
        # The algorithm file should rank higher
        assert any("algorithm" in r["content"].lower() or "search" in r["content"].lower()
                    for r in data["results"])


class TestStatsEndpoint:
    """Tests for GET /api/search/stats"""

    def test_stats(self, client):
        response = client.get("/api/search/stats")
        assert response.status_code == 200
        data = response.json()
        assert "vector_store" in data
        assert "embedding_provider" in data
        assert data["embedding_dimensions"] == 384
        assert "timestamp" in data
