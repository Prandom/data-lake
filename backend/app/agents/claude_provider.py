"""
Claude agent provider — uses the Anthropic SDK.

Implements AgentProvider for Claude's tool_use API.

Key format differences from the neutral schema:
  - Tools use "input_schema" instead of "parameters"
  - Tool calls come as "tool_use" content blocks
  - Tool results use "tool_result" with "tool_use_id"
"""

import json
import os
from typing import Any, Dict, List, Optional

from app.agents.base import AgentProvider, LLMResponse, ToolCall, ToolResult, SYSTEM_PROMPT
from app.agents.tool_executor import truncate


class ClaudeProvider(AgentProvider):
    """
    Claude (Anthropic) agent provider.

    Paid: ~$3/MTok input, ~$15/MTok output.
    Requires ANTHROPIC_API_KEY in .env.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Get a key at https://console.anthropic.com/"
            )

        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert provider-neutral tools to Anthropic format.

        Anthropic uses "input_schema" where OpenAPI uses "parameters".
        """
        converted = []
        for tool in tools:
            converted.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],  # key rename
            })
        return converted

    def call(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Make a single Claude API call."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=self._convert_tools(tools),
            messages=messages,
        )

        # Check if Claude is done
        if response.stop_reason == "end_turn":
            text_parts = [
                block.text
                for block in response.content
                if block.type == "text"
            ]
            return LLMResponse(
                text="\n".join(text_parts),
                is_done=True,
                raw_response=response,
            )

        # Extract tool calls
        tool_calls = []
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                ))

        return LLMResponse(
            tool_calls=tool_calls,
            is_done=False,
            raw_response=response,
        )

    def append_tool_exchange(
        self,
        messages: List[Dict[str, Any]],
        response: LLMResponse,
        results: List[ToolResult],
    ) -> List[Dict[str, Any]]:
        """
        Append Claude-format tool exchange to messages.

        Claude expects:
          1. assistant message with the raw content blocks (including tool_use)
          2. user message with tool_result blocks referencing tool_use_id
        """
        # Append assistant's response (with tool_use blocks)
        messages.append({
            "role": "assistant",
            "content": response.raw_response.content,
        })

        # Append tool results
        tool_result_blocks = []
        for result in results:
            tool_result_blocks.append({
                "type": "tool_result",
                "tool_use_id": result.call_id,
                "content": truncate(result.content),
            })

        messages.append({
            "role": "user",
            "content": tool_result_blocks,
        })

        return messages

    def get_name(self) -> str:
        return f"claude ({self.model})"
