"""
Shared fixtures and configuration for all tests.

Provides:
- In-memory SQLite database
- FastAPI test client
- Temporary file system
"""

import pytest
import os
import shutil
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

os.environ["DATA_LAKE_TESTING"] = "1"

from app.main import app, get_db
from app.db.models import Base
from app.mcp.servers import FileSystemMCPServer


@pytest.fixture(scope="function")
def test_db() -> Session:
    """
    Create an in-memory SQLite database for testing.
    
    Each test gets a fresh, isolated database.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(test_db: Session) -> TestClient:
    """
    FastAPI test client with overridden database dependency.
    
    Ensures tests use the in-memory database, not production db.
    """
    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Don't close, fixture manages it
    
    app.dependency_overrides[get_db] = override_get_db
    
    test_client = TestClient(app)
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def temp_dir():
    """
    Create a temporary directory for file tests.
    
    Automatically cleaned up after test.
    """
    backend_dir = Path(__file__).resolve().parents[1]  # backend/
    base_dir = backend_dir / ".tmp" / "tests"
    base_dir.mkdir(parents=True, exist_ok=True)

    tmpdir = base_dir / uuid.uuid4().hex
    tmpdir.mkdir(parents=True, exist_ok=False)

    try:
        yield str(tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="function")
def temp_files(temp_dir: str):
    """
    Create temporary test files.
    
    Returns: (tmpdir, list of file paths)
    """
    files = []
    
    # Create sample files
    for i in range(3):
        filepath = os.path.join(temp_dir, f"file_{i}.txt")
        with open(filepath, "w") as f:
            f.write(f"content {i}\n" * 10)
        files.append(filepath)
    
    # Create subdirectory with files
    subdir = os.path.join(temp_dir, "subdir")
    os.makedirs(subdir, exist_ok=True)
    subfile = os.path.join(subdir, "nested.txt")
    with open(subfile, "w") as f:
        f.write("nested content")
    files.append(subfile)
    
    yield temp_dir, files


@pytest.fixture(scope="function")
def mcp_server(temp_dir: str) -> FileSystemMCPServer:
    """
    Create an MCP server restricted to temp directory.
    """
    server = FileSystemMCPServer(allowed_paths=[temp_dir])
    return server
