"""
Groq agent provider — cloud-hosted open-source models with high free-tier limits.

Implements AgentProvider using Groq's OpenAI-compatible API.
Requires GROQ_API_KEY in .env.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

import requests

from app.agents.base import AgentProvider, LLMResponse, ToolCall, ToolResult, SYSTEM_PROMPT
from app.agents.tool_executor import truncate


class GroqProvider(AgentProvider):
    """
    Groq agent provider.

    Uses Groq's OpenAI-compatible chat completion API.
    Requires GROQ_API_KEY in .env.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "").strip()

        if not self.api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is required. "
                "Get a free key at https://console.groq.com/"
            )

        self.base_url = "https://api.groq.com/openai/v1"

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert to OpenAI-compatible tool format."""
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
        """Make a single Groq API call."""
        groq_messages = _convert_messages_to_groq(messages)

        # Prepend system prompt
        groq_messages.insert(0, {
            "role": "system",
            "content": SYSTEM_PROMPT,
        })

        payload = {
            "model": self.model,
            "messages": groq_messages,
            "tools": self._convert_tools(tools),
            "tool_choice": "auto",
            "temperature": 0.3,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Groq API returned an empty choices list")

        message = choices[0].get("message", {})
        tool_calls_raw = message.get("tool_calls", [])

        # Check for tool calls
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                func = tc.get("function", {})
                args_raw = func.get("arguments", "{}")
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = args_raw

                tool_calls.append(ToolCall(
                    id=tc.get("id", str(uuid.uuid4())),
                    name=func.get("name", ""),
                    arguments=args,
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
        """Append OpenAI-format tool exchange to messages."""
        tool_calls_for_msg = []
        for tc in response.tool_calls:
            tool_calls_for_msg.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            })

        messages.append({
            "role": "assistant",
            "content": response.text or "",
            "tool_calls": tool_calls_for_msg,
            "_is_groq_native": True,
        })

        # Append tool results
        for tc, result in zip(response.tool_calls, results):
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.name,
                "content": truncate(result.content),
                "_is_groq_native": True,
            })

        return messages

    def get_name(self) -> str:
        return f"groq ({self.model})"


def _convert_messages_to_groq(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert neutral messages to Groq/OpenAI format."""
    converted = []
    for msg in messages:
        if msg.get("_is_groq_native"):
            clean = {k: v for k, v in msg.items() if k != "_is_groq_native"}
            converted.append(clean)
        else:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, str):
                converted.append({"role": role, "content": content})
    return converted
