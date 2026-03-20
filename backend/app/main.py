import os
import json
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Personal Data Lake Agent (Week 1)...")
    print("🔗 Docs: http://localhost:8000/docs")
    print("🔗 ReDoc: http://localhost:8000/redoc")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="Personal Data Lake Agent",
    description="Week 1: FastAPI + FileSystem MCP test harness",
    version="0.1.0",
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
# ROOT + ERROR HANDLER
# =============================================================================


@app.get("/")
async def root() -> Dict[str, Any]:
    """Welcome & docs hint."""
    return {
        "message": "Personal Data Lake Agent - Week 1 backend is running",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "query": "POST /api/query?query=...",
            "websocket": "ws://localhost:8000/ws/query",
            "fs_list": "/api/test/filesystem/list?path=.",
            "fs_read": "/api/test/filesystem/read?path=./some_file.txt",
            "docs": "/docs",
            "redoc": "/redoc",
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


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
