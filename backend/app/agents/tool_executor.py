"""
Tool executor — shared by all agent providers.

Executes tool calls against our real backend services:
  - VectorStore (FAISS semantic search)
  - FileSystemMCPServer (list/read files)

Extracted from the original ClaudeAgent._execute_tool() so that
all providers share the same execution logic. The LLM decides
WHAT to call; this module decides HOW to call it.
"""

import json
import traceback
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.indexing.embeddings import get_provider
from app.indexing.vector_store import VectorStore
from app.mcp.servers import FileSystemMCPServer


# Max characters per tool result to prevent context window overflow.
MAX_TOOL_RESULT_CHARS = 8000


class ToolExecutor:
    """
    Executes tool calls against backend services.

    Initialised with a DB session and allowed paths, then reused
    across all tool calls within a single query.
    """

    def __init__(self, db: Session, allowed_paths: List[str]):
        self.db = db
        self.fs_server = FileSystemMCPServer(allowed_paths=allowed_paths)
        provider = get_provider()
        self.vector_store = VectorStore(db=db, embedding_provider=provider)

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single tool call and return the result as a dict.

        All results are dicts so they can be JSON-serialized for
        the LLM to read.
        """
        try:
            if tool_name == "vector_search":
                raw_k = arguments.get("k", 5)
                try:
                    k = int(raw_k)
                except (TypeError, ValueError):
                    k = 5
                k = min(k, 20)  # Cap at 20
                
                results = self.vector_store.search(
                    query=arguments["query"],
                    n_results=k,
                )
                return {
                    "results": results,
                    "total": len(results),
                    "query": arguments["query"],
                }

            elif tool_name == "filesystem_list_files":
                raw_hidden = arguments.get("include_hidden", False)
                if isinstance(raw_hidden, str):
                    include_hidden = raw_hidden.lower() == "true"
                else:
                    include_hidden = bool(raw_hidden)

                return self.fs_server.list_files(
                    path=arguments["path"],
                    include_hidden=include_hidden,
                )

            elif tool_name == "filesystem_read_file":
                return self.fs_server.read_file(path=arguments["path"])

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "traceback": traceback.format_exc(),
            }


def truncate(text: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Truncate text to max_chars, adding a note if truncated."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n... [truncated, {len(text) - max_chars} chars omitted]"
