# Personal Data Lake Backend

Multi-source data aggregation agent with FastAPI + SQLite + Claude AI (in progress).

## Quick Start

### Prerequisites
- Python 3.10+
- Git

### Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Server

```bash
# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Server runs at: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/test_endpoints.py -v

# Run only sync job tests
pytest tests/test_sync_job.py -v
```

## Project Structure

```
backend/
├─ app/
│  ├─ main.py                 # FastAPI app
│  ├─ mcp/
│  │  └─ servers.py           # FileSystem MCP server
│  ├─ db/
│  │  ├─ models.py            # SQLAlchemy models (FileMetadata, SyncRun)
│  │  └─ session.py           # Database setup
│  └─ jobs/
│     └─ sync.py              # Filesystem sync job
├─ tests/
│  ├─ conftest.py             # Shared pytest fixtures
│  ├─ test_endpoints.py       # FastAPI endpoint tests
│  ├─ test_mcp_server.py      # FileSystem server tests
│  ├─ test_models.py          # Database model tests
│  └─ test_sync_job.py        # Sync job tests
├─ requirements.txt           # Python dependencies
├─ data_lake.db               # SQLite database (auto-created)
└─ README.md                  # This file
```

## API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /api/status` - Operational status + data source state

### Query
- `POST /api/query?query=<text>` - Query the agent (placeholder)
- `ws://localhost:8000/ws/query` - WebSocket for streaming responses

### Filesystem Testing
- `GET /api/test/filesystem/list?path=.` - List files in directory
- `GET /api/test/filesystem/read?path=<file>` - Read file contents

### Documentation
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc (disabled due to CDN issues)

## Database

- **Engine**: SQLite
- **ORM**: SQLAlchemy
- **Auto-creation**: Tables created on startup via `Base.metadata.create_all()`

### Tables

**FileMetadata** — Discovered files
```
- id (primary key)
- path (unique, indexed)
- size, modified (change detection)
- hash_value (SHA256, optional)
- last_synced, needs_sync (sync state)
- created_at, updated_at (audit)
```

**SyncRun** — Sync operation history
```
- id (primary key)
- started_at, completed_at, duration_ms
- files_scanned, files_new, files_changed, files_deleted, files_unchanged
- status (running|completed|failed)
- error_message
- created_at
```

## Sync Job

The sync job scans the filesystem, detects changes, and updates the database.

```python
from app.jobs.sync import run_sync
from app.db.session import SessionLocal

db = SessionLocal()
result = run_sync(db, allowed_paths=["/home/user"])
# Returns: {sync_run_id, status, duration_ms, stats}
```

**Change Detection**:
- **New file**: Not in database -> create record
- **Changed file**: Size or modified timestamp differ -> update record
- **Unchanged**: No change -> stats only
- **Deleted**: In database but not found -> mark for sync

### API Trigger (Week 2)
`POST /api/sync/trigger` requires `DATA_LAKE_ALLOWED_PATHS` (comma/semicolon-separated list of allowed roots).

## Testing

### Test Strategy
- **Unit tests** for individual functions
- **In-memory SQLite** for database tests (no file I/O)
- **FastAPI TestClient** for endpoint tests
- **Shared fixtures** in `conftest.py`

### Coverage
Run coverage locally and only then update any coverage claims in docs:

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Test Files
- `test_endpoints.py`: API endpoints (health, status, query, errors)
- `test_mcp_server.py`: FileSystem MCP server (list, read, security)
- `test_models.py`: Database models and queries
- `test_sync_job.py`: Sync job logic and change detection

## Development

### Add a New Endpoint
1. Define in `app/main.py`
2. Add route decorator and function
3. Add test in `tests/test_endpoints.py`
4. Run tests: `pytest tests/test_endpoints.py -v`

### Add a Database Model
1. Define in `app/db/models.py`
2. Import `Base` class
3. Add tests in `tests/test_models.py`
4. Tables auto-create on next startup

### Run Specific Tests
```bash
pytest tests/test_endpoints.py::TestHealthEndpoint -v
pytest tests/test_sync_job.py::TestChangeDetection -v
```

## Environment Variables

Create `.env` in `backend/` (if needed):
```
DB_URL=sqlite:///data_lake.db
DATA_LAKE_ALLOWED_PATHS=/home/user;/another/root
LOG_LEVEL=info
```

## Troubleshooting

### Server won't start
- Check Python version: `python --version` (need 3.10+)
- Check venv activation
- Run `pip install -r requirements.txt` again

### Tests fail
- Ensure pytest installed: `pip install pytest pytest-cov`
- Run from `backend/` directory
- Check temp directory permissions

### Database errors
- Delete `data_lake.db` to reset:
  - PowerShell: `Remove-Item .\\data_lake.db -ErrorAction SilentlyContinue`
  - Bash: `rm -f data_lake.db`
- Tables will auto-recreate on next startup

## Progress

- Week 1: FastAPI foundation + FileSystem MCP server
- Week 2: Database persistence + sync job
- Week 3+: Claude AI integration, MCP tools, additional data sources

See [PROGRESS.md](../PROGRESS.md) for detailed roadmap.

## License

MIT
