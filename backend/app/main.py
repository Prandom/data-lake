import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.models import FileMetadata
from app.db.session import get_db, init_db
from app.jobs.sync import get_sync_stats, run_sync

# Week 3 imports
from app.api.search import router as search_router

# Week 4 imports
from app.api.agent import router as agent_router


# =============================================================================
# SCHEDULER HELPERS (Week 4)
# =============================================================================


def _get_allowed_paths_from_env_safe() -> List[str]:
    """
    Parse allowed paths from env. Returns empty list if not configured
    (used by scheduler — should not raise HTTPException).
    """
    raw = os.getenv("DATA_LAKE_ALLOWED_PATHS", "").strip()
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]


def _run_scheduled_sync():
    """
    Scheduled sync job. Runs every 30 minutes.
    Scans allowed paths and flags changed files.
    """
    from app.db.session import SessionLocal

    allowed = _get_allowed_paths_from_env_safe()
    if not allowed:
        print("[Scheduler] Skipping sync: DATA_LAKE_ALLOWED_PATHS not set")
        return

    db = SessionLocal()
    try:
        result = run_sync(db, allowed_paths=allowed)
        print(
            f"[Scheduler] Sync complete: "
            f"{result['stats']['files_scanned']} scanned, "
            f"{result['stats']['files_changed']} changed"
        )
    except Exception as e:
        print(f"[Scheduler] Sync failed: {e}")
    finally:
        db.close()


def _run_scheduled_index():
    """
    Scheduled indexing job. Runs 5 minutes after sync.
    Embeds any files flagged with needs_sync=True.
    """
    from app.db.session import SessionLocal
    from app.indexing.chunker import chunk_file
    from app.indexing.embeddings import get_provider
    from app.indexing.vector_store import VectorStore

    db = SessionLocal()
    try:
        pending = (
            db.query(FileMetadata)
            .filter(FileMetadata.needs_sync == True)
            .limit(100)
            .all()
        )

        if not pending:
            return

        provider = get_provider()
        vector_store = VectorStore(db=db, embedding_provider=provider)

        indexed = 0
        for file in pending:
            try:
                chunks = chunk_file(Path(file.path))
                if not chunks:
                    file.needs_sync = False
                    continue
                vector_store.delete_by_path(file.path)
                vector_store.add_chunks(chunks)
                file.needs_sync = False
                indexed += 1
            except Exception as e:
                print(f"[Scheduler] Index error for {file.path}: {e}")

        db.commit()
        print(f"[Scheduler] Indexed {indexed} files")
    except Exception as e:
        print(f"[Scheduler] Indexing failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise database
    if os.getenv("DATA_LAKE_TESTING") != "1":
        init_db()

    # Start APScheduler (Week 4)
    scheduler = None
    if os.getenv("DATA_LAKE_TESTING") != "1":
        try:
            from apscheduler.schedulers.background import BackgroundScheduler

            scheduler = BackgroundScheduler()

            # Sync every 30 minutes — scans filesystem, flags changed files
            scheduler.add_job(
                _run_scheduled_sync,
                "interval",
                minutes=30,
                id="sync_job",
                name="Filesystem sync",
            )

            # Index 5 minutes after sync — embeds flagged files into FAISS
            scheduler.add_job(
                _run_scheduled_index,
                "interval",
                minutes=30,
                id="index_job",
                name="FAISS indexing",
                next_run_time=datetime.now() + timedelta(minutes=5),
            )

            scheduler.start()
            print("[Scheduler] Started: sync every 30min, index every 30min (offset 5min)")
        except ImportError:
            print("[Scheduler] APScheduler not installed, running without auto-sync")
        except Exception as e:
            print(f"[Scheduler] Failed to start: {e}")

    print("Starting Personal Data Lake Agent (Week 4)...")
    print("Docs: http://localhost:8000/docs")
    yield

    # Shutdown scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")
    print("Shutting down...")


app = FastAPI(
    title="Personal Data Lake Agent",
    description="Week 4: FastAPI + FAISS Search + Claude Agent + APScheduler",
    version="0.4.0",
    lifespan=lifespan,
    redoc_url=None,  # Disable ReDoc to avoid CDN MIME type issues
)

# CORS (for frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in prod, restrict to your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(search_router)
app.include_router(agent_router)


# =============================================================================
# HEALTH / STATUS
# =============================================================================


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Personal Data Lake Agent",
    }


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Simple status including placeholder source info."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "sources": {
            "filesystem": {"connected": True, "last_synced": None},
            "google_drive": {"connected": False, "last_synced": None},
            "notion": {"connected": False, "last_synced": None},
            "github": {"connected": False, "last_synced": None},
            "email": {"connected": False, "last_synced": None},
        },
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# SIMPLE QUERY PLACEHOLDER
# =============================================================================


@app.post("/api/query")
async def query_endpoint(query: str = Query(..., min_length=1, max_length=1000)) -> Dict[str, Any]:
    """
    Week 1: placeholder query endpoint.

    Later this will call the Claude agent and MCP tools.
    For now it just echoes the query so you can test end-to-end.
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return {
        "query": query,
        "response": f"[Week 1 Placeholder] You asked: {query}",
        "sources": [],
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# WEBSOCKET (STREAMING PLACEHOLDER)
# =============================================================================


@app.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    WebSocket endpoint for streaming responses.

    Week 1: just sends a couple of JSON messages back.
    Later: will stream Claude's tokens.
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
                query = message.get("query", "").strip()

                if not query:
                    await websocket.send_json(
                        {"type": "error", "message": "Query cannot be empty"}
                    )
                    continue

                await websocket.send_json(
                    {"type": "start", "timestamp": datetime.now().isoformat()}
                )

                await websocket.send_json(
                    {
                        "type": "chunk",
                        "content": f"[Week 1 Placeholder] Processing query: {query}...",
                    }
                )

                await websocket.send_json(
                    {
                        "type": "complete",
                        "sources": [],
                        "metadata": {"tokens_used": 0, "duration_ms": 0},
                    }
                )
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.close(code=1000)


# =============================================================================
# FILESYSTEM TEST ENDPOINTS (BEFORE MCP INTEGRATION)
# =============================================================================


@app.get("/api/test/filesystem/list")
async def test_list_files(path: str = Query(".")) -> Dict[str, Any]:
    """
    TEST ONLY: list files in a directory.

    This is NOT the MCP server yet; just a helper so you can see things work.
    Example:
      GET /api/test/filesystem/list?path=.
    """
    try:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail=f"Not a directory: {path}")

        entries = []
        for item in os.listdir(path):
            full = os.path.join(path, item)
            try:
                stat = os.stat(full)
                entries.append(
                    {
                        "name": item,
                        "type": "directory" if os.path.isdir(full) else "file",
                        "size": stat.st_size if os.path.isfile(full) else None,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "path": full,
                    }
                )
            except (OSError, PermissionError):
                continue

        entries.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))

        return {
            "path": os.path.abspath(path),
            "entries": entries,
            "total": len(entries),
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test/filesystem/read")
async def test_read_file(path: str = Query(...)) -> Dict[str, Any]:
    """
    TEST ONLY: read a text file.

    Example:
      GET /api/test/filesystem/read?path=./some_file.txt
    """
    try:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail=f"Not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is not UTF-8 text")

        return {
            "path": os.path.abspath(path),
            "content": content,
            "size": len(content),
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# WEEK 2: SYNC ENDPOINTS
# =============================================================================


def _get_allowed_paths_from_env() -> List[str]:
    raw = os.getenv("DATA_LAKE_ALLOWED_PATHS", "").strip()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail=(
                "DATA_LAKE_ALLOWED_PATHS is required (comma/semicolon-separated "
                "list of allowed root paths)"
            ),
        )

    paths = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="DATA_LAKE_ALLOWED_PATHS did not contain any usable paths",
        )

    return paths


@app.get("/api/sync/status")
async def sync_status(db: Session = Depends(get_db)):
    """
    Get sync status and summary stats.
    
    Example:
      GET /api/sync/status
    """
    stats = get_sync_stats(db)
    return stats


@app.post("/api/sync/trigger")
async def trigger_sync(db: Session = Depends(get_db)):
    """
    Trigger a manual filesystem sync.
    
    Returns sync run ID and stats.
    """
    allowed_paths = _get_allowed_paths_from_env()
    try:
        return run_sync(db, allowed_paths=allowed_paths)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/files")
async def list_files(
    limit: int = 50,
    offset: int = 0,
    needs_sync: bool | None = None,
    db: Session = Depends(get_db),
):
    """
    List indexed files with sync state.
    
    Query params:
    - limit: max files to return
    - offset: pagination
    - needs_sync: filter by sync state
    """
    query = db.query(FileMetadata)
    
    if needs_sync is not None:
        query = query.filter(FileMetadata.needs_sync.is_(needs_sync))
    
    total = query.count()
    files = (
        query.order_by(FileMetadata.modified.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return {
        "files": [
            {
                "path": f.path,
                "size": f.size,
                "modified": f.modified.isoformat(),
                "last_synced": f.last_synced.isoformat() if f.last_synced else None,
                "needs_sync": f.needs_sync,
            }
            for f in files
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

# =============================================================================
# ROOT + ERROR HANDLER
# =============================================================================


@app.get("/")
async def root() -> Dict[str, Any]:
    """Welcome & docs hint."""
    return {
        "message": "Personal Data Lake Agent backend is running",
        "status": "ok",
        "version": "0.4.0",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "agent_query": "POST /api/agent/query",
            "query_legacy": "POST /api/query?query=...",
            "websocket": "ws://localhost:8000/ws/query",
            "fs_list": "/api/test/filesystem/list?path=.",
            "fs_read": "/api/test/filesystem/read?path=./some_file.txt",
            "sync_status": "/api/sync/status",
            "sync_trigger": "POST /api/sync/trigger",
            "files": "/api/files",
            "search": "POST /api/search/",
            "search_index": "POST /api/search/index",
            "search_stats": "/api/search/stats",
            "docs": "/docs",
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "status_code": 422,
            "timestamp": datetime.now().isoformat(),
            "details": exc.errors(),
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
