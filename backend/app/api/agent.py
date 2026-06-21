"""
Week 4: Agent API endpoint (updated for provider abstraction).

POST /api/agent/query — send a natural language question,
get back the LLM's answer with tool call metadata.

Uses DataLakeAgent (provider-agnostic orchestrator) with
whichever provider is configured via AGENT_PROVIDER in .env.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.agent import DataLakeAgent, get_agent_provider
from app.agents.tool_executor import ToolExecutor
from app.db.session import get_db


router = APIRouter(prefix="/api/agent", tags=["agent"])


class QueryRequest(BaseModel):
    """Request body for the agent query endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question to ask about your files",
        examples=["What are my notes on binary search?"],
    )


class QueryResponse(BaseModel):
    """Response from the agent query endpoint."""

    query: str
    response: str
    tools_called: list
    provider: str
    iterations: int
    timestamp: str


def _get_allowed_paths() -> List[str]:
    """Parse allowed paths from environment. Raises HTTPException if missing."""
    raw = os.getenv("DATA_LAKE_ALLOWED_PATHS", "").strip()
    if not raw:
        raise HTTPException(
            status_code=500,
            detail="DATA_LAKE_ALLOWED_PATHS is not configured on the server",
        )
    paths = [p.strip() for p in re.split(r"[;,]", raw) if p.strip()]
    if not paths:
        raise HTTPException(
            status_code=500,
            detail="DATA_LAKE_ALLOWED_PATHS did not contain any usable paths",
        )
    return paths


@router.post("/query", response_model=QueryResponse)
async def agent_query(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Ask a natural language question about your indexed files.

    The agent uses whichever LLM provider is configured (AGENT_PROVIDER
    in .env) to search your files and synthesise an answer.

    Providers: gemini (free), claude (paid), ollama (free, local).

    Example:
        POST /api/agent/query
        {"query": "What are my notes on binary search?"}
    """
    allowed_paths = _get_allowed_paths()

    # Initialise provider
    try:
        provider = get_agent_provider()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Initialise tool executor and agent
    executor = ToolExecutor(db=db, allowed_paths=allowed_paths)
    agent = DataLakeAgent(provider=provider, executor=executor)

    # Run the query
    try:
        result = await agent.query(request.query)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent query failed: {str(e)}",
        )

    return {
        "query": request.query,
        "response": result["response"],
        "tools_called": result["tools_called"],
        "provider": result["provider"],
        "iterations": result["iterations"],
        "timestamp": datetime.now().isoformat(),
    }
