"""
Week 4: Claude agent with MCP tool calling.

This is the core intelligence layer. ClaudeAgent:
  1. Receives a natural language query from the user
  2. Sends it to Claude with tool definitions (from mcp_tools.py)
  3. Claude decides which tools to call (vector_search, filesystem, etc.)
  4. Agent executes the tools against our real backends
  5. Feeds tool results back to Claude
  6. Claude synthesises a final answer with citations

The agent runs an "agentic loop" — Claude can call multiple tools
in sequence before producing a final response. For example:
  - vector_search("binary search") → finds relevant chunks
  - filesystem_read_file("/docs/algos.md") → reads full context
  - produces final answer citing both sources

Design decisions:
  - SYSTEM_PROMPT instructs Claude to always use vector_search first
  - Tool results are truncated to avoid blowing context window
  - Max 10 loop iterations to prevent infinite tool-calling
  - Each tool execution is synchronous (our backends are not async)
"""

import json
import os
import traceback
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from sqlalchemy.orm import Session

from app.agents.mcp_tools import TOOLS
from app.indexing.embeddings import get_provider
from app.indexing.vector_store import VectorStore
from app.mcp.servers import FileSystemMCPServer


SYSTEM_PROMPT = """\
You are a personal data lake assistant. The user has indexed their local files \
(documents, notes, code) into a searchable vector database.

Your job is to answer questions using the tools available to you.

Rules:
1. ALWAYS use the vector_search tool first to find relevant content before \
   answering questions about the user's files or knowledge.
2. If vector_search returns relevant chunks, cite the file path in your answer.
3. If you need more context from a specific file, use filesystem_read_file.
4. If the user asks what files they have, use filesystem_list_files.
5. Be concise and direct. Cite sources with file paths.
6. If no relevant results are found, say so honestly — don't make things up.
"""

# Max characters per tool result to prevent context window overflow.
# Claude's context is 200k tokens but tool results can be huge
# (e.g. a 10MB file read). We truncate to keep things manageable.
MAX_TOOL_RESULT_CHARS = 8000

# Safety limit on agentic loop iterations.
MAX_ITERATIONS = 10


class ClaudeAgent:
    """
    Conversational agent backed by Claude with tool-calling.

    Bridges the user's natural language questions to our backend
    capabilities: FAISS vector search, filesystem listing/reading.
    """

    def __init__(
        self,
        db: Session,
        allowed_paths: List[str],
        model: str = "claude-sonnet-4-20250514",
    ):
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Get a free key at https://console.anthropic.com/"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.db = db

        # Initialise backend services
        self.fs_server = FileSystemMCPServer(allowed_paths=allowed_paths)
        provider = get_provider()
        self.vector_store = VectorStore(
            db=db, embedding_provider=provider
        )

        # Track tool calls for observability
        self._tool_calls: List[Dict[str, Any]] = []

    async def query(self, user_query: str) -> Dict[str, Any]:
        """
        Run an agentic query loop.

        Claude may call tools multiple times before producing a final answer.
        We feed tool results back and let Claude decide when it has enough
        information to respond.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_query}
        ]
        self._tool_calls = []

        for iteration in range(MAX_ITERATIONS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Check if Claude is done (no more tool calls)
            if response.stop_reason == "end_turn":
                # Extract final text response
                text_parts = [
                    block.text
                    for block in response.content
                    if block.type == "text"
                ]
                return {
                    "response": "\n".join(text_parts),
                    "tools_called": self._tool_calls,
                    "model": self.model,
                    "iterations": iteration + 1,
                }

            # Process tool calls from this iteration
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._execute_tool(block.name, block.input)
                    self._tool_calls.append({
                        "tool": block.name,
                        "input": block.input,
                        "result_preview": _truncate(str(result), 500),
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": _truncate(
                            json.dumps(result, default=str),
                            MAX_TOOL_RESULT_CHARS,
                        ),
                    })

            # Feed tool results back to Claude for the next iteration
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        # If we exhaust iterations, return whatever we have
        return {
            "response": "[Agent reached maximum iterations without a final answer]",
            "tools_called": self._tool_calls,
            "model": self.model,
            "iterations": MAX_ITERATIONS,
        }

    def _execute_tool(self, name: str, params: Dict) -> Dict[str, Any]:
        """
        Execute a tool call against the real backend.

        Each tool name maps to a method on one of our existing services.
        Tool results are always dicts so Claude can parse them.
        """
        try:
            if name == "vector_search":
                k = min(params.get("k", 5), 20)  # Cap at 20 results
                results = self.vector_store.search(
                    query=params["query"],
                    n_results=k,
                )
                return {
                    "results": results,
                    "total": len(results),
                    "query": params["query"],
                }

            elif name == "filesystem_list_files":
                return self.fs_server.list_files(
                    path=params["path"],
                    include_hidden=params.get("include_hidden", False),
                )

            elif name == "filesystem_read_file":
                return self.fs_server.read_file(path=params["path"])

            else:
                return {"error": f"Unknown tool: {name}"}

        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "traceback": traceback.format_exc(),
            }


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding a note if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text) - max_chars} chars omitted]"
