"""
Ollama agent provider — fully local, free LLM.

Implements AgentProvider using Ollama's OpenAI-compatible API.

Ollama runs models locally on your machine. No API key, no internet,
no cost. Requires Ollama installed and a model pulled:
  brew install ollama
  ollama pull llama3.1

Key format: OpenAI-compatible (tools with "parameters", tool_calls
in response, tool role for results).

Set in .env:
  AGENT_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=llama3.1
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import requests

from app.agents.base import AgentProvider, LLMResponse, ToolCall, ToolResult, SYSTEM_PROMPT
from app.agents.tool_executor import truncate


class OllamaProvider(AgentProvider):
    """
    Ollama agent provider — fully local, free.

    Uses Ollama's OpenAI-compatible /api/chat endpoint.
    No API key required, runs entirely on your machine.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1")
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )

        # Verify Ollama is running
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            # Check if our model is available (strip tag suffix for comparison)
            model_base = self.model.split(":")[0]
            available = any(model_base in m for m in models)
            if not available:
                raise ValueError(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available: {models}. Run: ollama pull {self.model}"
                )
        except requests.ConnectionError:
            raise ValueError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            )

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert to OpenAI-compatible tool format for Ollama.

        Ollama expects OpenAI-style function definitions.
        """
        converted = []
        for tool in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            })
        return converted

    def call(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Make a single Ollama API call."""
        # Convert messages to OpenAI format
        ollama_messages = _convert_messages_to_ollama(messages)

        # Prepend system prompt
        ollama_messages.insert(0, {
            "role": "system",
            "content": SYSTEM_PROMPT,
        })

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "tools": self._convert_tools(tools),
            "stream": False,
        }

        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=120,  # Local models can be slow
        )
        resp.raise_for_status()
        data = resp.json()

        message = data.get("message", {})
        tool_calls_raw = message.get("tool_calls", [])

        # Check for tool calls
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                func = tc.get("function", {})
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),  # Ollama doesn't always provide IDs
                    name=func.get("name", ""),
                    arguments=func.get("arguments", {}),
                ))
            return LLMResponse(
                tool_calls=tool_calls,
                is_done=False,
                raw_response=data,
            )

        # No tool calls — LLM is done
        return LLMResponse(
            text=message.get("content", ""),
            is_done=True,
            raw_response=data,
        )

    def append_tool_exchange(
        self,
        messages: List[Dict[str, Any]],
        response: LLMResponse,
        results: List[ToolResult],
    ) -> List[Dict[str, Any]]:
        """
        Append Ollama/OpenAI-format tool exchange to messages.

        Format:
          1. assistant message with tool_calls
          2. one "tool" role message per result
        """
        # Append assistant's response with tool calls
        tool_calls_for_msg = []
        for tc in response.tool_calls:
            tool_calls_for_msg.append({
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments,
                },
            })

        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls_for_msg,
            "_is_ollama_native": True,
        })

        # Append tool results
        for tc, result in zip(response.tool_calls, results):
            messages.append({
                "role": "tool",
                "content": truncate(result.content),
                "_is_ollama_native": True,
            })

        return messages

    def get_name(self) -> str:
        return f"ollama ({self.model})"


# =============================================================================
# HELPERS
# =============================================================================


def _convert_messages_to_ollama(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert our neutral message format to Ollama/OpenAI format.

    Handles both plain text messages and native Ollama messages
    (from append_tool_exchange).
    """
    converted = []
    for msg in messages:
        if msg.get("_is_ollama_native"):
            # Already in Ollama format, pass through (strip our marker)
            clean = {k: v for k, v in msg.items() if k != "_is_ollama_native"}
            converted.append(clean)
        else:
            # Plain text message
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                converted.append({"role": role, "content": content})
    return converted
