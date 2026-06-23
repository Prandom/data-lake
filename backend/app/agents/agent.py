"""
DataLakeAgent — provider-agnostic orchestrator.

Runs the agentic loop regardless of which LLM provider is behind it.
The loop is always the same:
  1. Send user query + tools to the LLM
  2. If LLM requests tool calls → execute them
  3. Feed results back to the LLM
  4. Repeat until LLM produces a final answer

The factory function get_agent_provider() reads AGENT_PROVIDER from
.env and returns the appropriate provider. Swap LLMs with zero code changes:
  AGENT_PROVIDER=gemini   → free, cloud
  AGENT_PROVIDER=claude   → paid, cloud (best quality)
  AGENT_PROVIDER=ollama   → free, local (fully offline)
"""

import json
import os
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.agents.base import AgentProvider, LLMResponse, ToolResult
from app.agents.mcp_tools import TOOLS
from app.agents.tool_executor import ToolExecutor, truncate


# Safety limit on agentic loop iterations
MAX_ITERATIONS = 10


class DataLakeAgent:
    """
    Provider-agnostic agent orchestrator.

    Takes any AgentProvider and runs the agentic loop using
    the shared ToolExecutor for backend calls.
    """

    def __init__(self, provider: AgentProvider, executor: ToolExecutor):
        self.provider = provider
        self.executor = executor

    async def query(self, user_query: str) -> Dict[str, Any]:
        """
        Run an agentic query loop.

        The LLM may call tools multiple times before producing a
        final answer. We execute tools and feed results back until
        the LLM is done or we hit MAX_ITERATIONS.
        """
        messages: List[Dict[str, Any]] = [
            {"role": "user", "content": user_query}
        ]
        all_tool_calls: List[Dict[str, Any]] = []

        for iteration in range(MAX_ITERATIONS):
            # Ask the LLM
            response = self.provider.call(messages, TOOLS)

            # If done, return the final answer
            if response.is_done:
                return {
                    "response": response.text or "",
                    "tools_called": all_tool_calls,
                    "provider": self.provider.get_name(),
                    "iterations": iteration + 1,
                }

            # Execute requested tools
            results: List[ToolResult] = []
            for tc in response.tool_calls:
                result = self.executor.execute(tc.name, tc.arguments)
                result_json = json.dumps(result, default=str)

                results.append(ToolResult(
                    call_id=tc.id,
                    content=result_json,
                ))

                # Track for observability
                all_tool_calls.append({
                    "tool": tc.name,
                    "input": tc.arguments,
                    "result_preview": truncate(str(result), 500),
                })

            # Feed tool results back to the LLM
            messages = self.provider.append_tool_exchange(
                messages, response, results
            )

        # Exhausted iterations
        return {
            "response": "[Agent reached maximum iterations without a final answer]",
            "tools_called": all_tool_calls,
            "provider": self.provider.get_name(),
            "iterations": MAX_ITERATIONS,
        }


# =============================================================================
# FACTORY
# =============================================================================


def get_agent_provider() -> AgentProvider:
    """
    Return the configured agent provider based on AGENT_PROVIDER env var.

    Options:
      - gemini  (default, free)
      - claude  (paid, best quality)
      - ollama  (free, local)
      - groq    (free, cloud)
    """
    provider = os.getenv("AGENT_PROVIDER", "ollama").lower().strip()

    if provider == "claude":
        from app.agents.claude_provider import ClaudeProvider
        return ClaudeProvider()

    elif provider == "gemini":
        from app.agents.gemini_provider import GeminiProvider
        return GeminiProvider()

    elif provider == "ollama":
        from app.agents.ollama_provider import OllamaProvider
        return OllamaProvider()

    elif provider == "groq":
        from app.agents.groq_provider import GroqProvider
        return GroqProvider()

    else:
        raise ValueError(
            f"Unknown AGENT_PROVIDER: '{provider}'. "
            f"Valid options: claude, gemini, ollama, groq"
        )
