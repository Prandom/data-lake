"""
Test FastAPI Endpoints (Week 1 + Week 2).

Tests:
- Health check
- Status endpoint
- Query endpoint
- WebSocket endpoint
- Error handling
"""

import os
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check_success(self, client: TestClient):
        """Test that health check returns ok."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["service"] == "Personal Data Lake Agent"
    
    def test_health_check_is_fast(self, client: TestClient):
        """Test that health check responds quickly."""
        response = client.get("/health")
        
        # Health checks should be fast
        assert response.elapsed.total_seconds() < 1.0


class TestStatusEndpoint:
    """Tests for /api/status endpoint."""
    
    def test_status_endpoint_success(self, client: TestClient):
        """Test status endpoint returns operational status."""
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["version"] == "0.1.0"
    
    def test_status_includes_sources(self, client: TestClient):
        """Test that status includes all data sources."""
        response = client.get("/api/status")
        
        data = response.json()
        sources = data["sources"]
        
        expected_sources = ["filesystem", "google_drive", "notion", "github", "email"]
        for source in expected_sources:
            assert source in sources
            assert "connected" in sources[source]
            assert "last_synced" in sources[source]
    
    def test_filesystem_source_connected(self, client: TestClient):
        """Test that filesystem source is marked connected."""
        response = client.get("/api/status")
        
        data = response.json()
        assert data["sources"]["filesystem"]["connected"] is True


class TestQueryEndpoint:
    """Tests for /api/query endpoint."""
    
    def test_query_success(self, client: TestClient):
        """Test successful query."""
        response = client.post("/api/query?query=hello")
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "hello"
        assert "response" in data
        assert "timestamp" in data
    
    def test_query_too_long(self, client: TestClient):
        """Test query that exceeds max length."""
        long_query = "a" * 1001  # Max is 1000
        response = client.post(f"/api/query?query={long_query}")
        
        assert response.status_code == 422  # Validation error
    
    def test_query_empty(self, client: TestClient):
        """Test empty query (validation)."""
        response = client.post("/api/query?query=")
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["status_code"] == 422
        assert "details" in data

    def test_query_whitespace_only(self, client: TestClient):
        """Test whitespace-only query (handled by HTTPException)."""
        response = client.post("/api/query?query=%20%20%20")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "Query cannot be empty"
    
    def test_query_with_special_characters(self, client: TestClient):
        """Test query with special characters."""
        response = client.post("/api/query?query=what%20is%20%3F")
        
        assert response.status_code == 200
        data = response.json()
        assert "what is ?" in data["query"]
    
    def test_query_missing_parameter(self, client: TestClient):
        """Test query missing the query parameter."""
        response = client.post("/api/query")
        
        assert response.status_code == 422  # Validation error


class TestRootEndpoint:
    """Tests for / (root) endpoint."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "ok"
    
    def test_root_includes_endpoints(self, client: TestClient):
        """Test root endpoint lists available endpoints."""
        response = client.get("/")
        
        data = response.json()
        endpoints = data["endpoints"]
        
        expected_endpoints = ["health", "status", "query", "docs"]
        for endpoint in expected_endpoints:
            assert endpoint in endpoints


class TestFilesystemTestEndpoints:
    """Tests for filesystem test endpoints."""
    
    def test_list_files_endpoint(self, client: TestClient):
        """Test /api/test/filesystem/list endpoint."""
        response = client.get("/api/test/filesystem/list?path=.")
        
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "entries" in data
        assert "total" in data
    
    def test_list_files_nonexistent_path(self, client: TestClient):
        """Test listing files in non-existent path."""
        response = client.get("/api/test/filesystem/list?path=/nonexistent/path")
        
        assert response.status_code == 404


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_404_for_invalid_route(self, client: TestClient):
        """Test 404 for non-existent route."""
        response = client.get("/api/nonexistent")
        
        assert response.status_code == 404
    
    def test_error_response_format(self, client: TestClient):
        """Test that error responses are properly formatted."""
        response = client.post("/api/query")  # Missing required query param
        
        data = response.json()
        assert "error" in data
        assert "status_code" in data
        assert "timestamp" in data
    
    def test_method_not_allowed(self, client: TestClient):
        """Test 405 Method Not Allowed."""
        response = client.post("/health")  # Health is GET only
        
        assert response.status_code == 405


class TestCORS:
    """Tests for CORS headers."""
    
    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are included in responses."""
        origin = "http://example.com"
        response = client.get("/health", headers={"Origin": origin})
        
        # FastAPI's CORS middleware adds these headers
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] in ("*", origin)


class TestSyncEndpoints:
    """Tests for Week 2 sync endpoints."""

    def test_sync_status_never_run(self, client: TestClient):
        response = client.get("/api/sync/status")

        assert response.status_code == 200
        data = response.json()
        assert data["latest_sync"]["status"] == "never_run"

    def test_sync_trigger_requires_allowed_paths(self, client: TestClient, monkeypatch):
        monkeypatch.delenv("DATA_LAKE_ALLOWED_PATHS", raising=False)
        response = client.post("/api/sync/trigger")

        assert response.status_code == 400
        data = response.json()
        assert "DATA_LAKE_ALLOWED_PATHS" in data["error"]

    def test_sync_trigger_and_list_files(self, client: TestClient, temp_files, monkeypatch):
        temp_dir, _files = temp_files
        monkeypatch.setenv("DATA_LAKE_ALLOWED_PATHS", temp_dir)

        trigger = client.post("/api/sync/trigger")
        assert trigger.status_code == 200
        trigger_data = trigger.json()
        assert trigger_data["status"] == "completed"
        assert "sync_run_id" in trigger_data

        status = client.get("/api/sync/status")
        assert status.status_code == 200
        status_data = status.json()
        assert status_data["latest_sync"]["status"] == "completed"

        files = client.get("/api/files?limit=10&offset=0")
        assert files.status_code == 200
        files_data = files.json()
        assert "files" in files_data
        assert files_data["total"] >= 1
