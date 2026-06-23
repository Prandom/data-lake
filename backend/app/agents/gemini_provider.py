"""
Gemini agent provider — uses the Google GenAI SDK.

Implements AgentProvider for Gemini's function calling API.

Key format differences from the neutral schema:
  - Tools wrapped in google.genai types (Tool, FunctionDeclaration)
  - Tool calls come as function_call parts
  - Tool results sent as function_response parts

Cost: FREE within rate limits (15 RPM, 1M TPM).
Requires GOOGLE_AI_API_KEY in .env.
"""

import json
import os
import uuid
from typing import Any, Dict, List, Optional

from app.agents.base import AgentProvider, LLMResponse, ToolCall, ToolResult, SYSTEM_PROMPT
from app.agents.tool_executor import truncate


class GeminiProvider(AgentProvider):
    """
    Gemini (Google AI Studio) agent provider.

    Free tier: 15 RPM, 1M TPM — more than enough for personal use.
    Requires GOOGLE_AI_API_KEY in .env.
    """

    def __init__(self, model: str = "gemini-2.5-flash-lite"):
        from google import genai

        api_key = os.getenv("GOOGLE_AI_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY environment variable is required. "
                "Get a free key at https://aistudio.google.com/apikey"
            )

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _build_tools(self, tools: List[Dict[str, Any]]):
        """
        Convert provider-neutral tools to Gemini format.

        Gemini uses google.genai types for tool definitions.
        We pass raw dicts that the SDK converts internally.
        """
        from google.genai import types

        function_declarations = []
        for tool in tools:
            # Clean parameters: remove "default" keys that Gemini doesn't support
            params = _clean_schema_for_gemini(tool["parameters"])
            function_declarations.append(
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=params,
                )
            )
        return types.Tool(function_declarations=function_declarations)

    def call(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """Make a single Gemini API call."""
        from google.genai import types

        gemini_tools = self._build_tools(tools)

        # Convert our neutral messages to Gemini's Content format
        contents = _convert_messages_to_gemini(messages)

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[gemini_tools],
                temperature=0.3,
            ),
        )

        # Parse the response
        candidate = response.candidates[0]
        parts = candidate.content.parts

        # Check for function calls
        tool_calls = []
        text_parts = []

        for part in parts:
            if part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=str(uuid.uuid4()),  # Gemini doesn't give IDs; we generate them
                    name=fc.name,
                    arguments=dict(fc.args) if fc.args else {},
                ))
            elif part.text:
                text_parts.append(part.text)

        if tool_calls:
            return LLMResponse(
                tool_calls=tool_calls,
                is_done=False,
                raw_response=response,
            )

        return LLMResponse(
            text="\n".join(text_parts) if text_parts else "",
            is_done=True,
            raw_response=response,
        )

    def append_tool_exchange(
        self,
        messages: List[Dict[str, Any]],
        response: LLMResponse,
        results: List[ToolResult],
    ) -> List[Dict[str, Any]]:
        """
        Append Gemini-format tool exchange to messages.

        Gemini expects:
          1. model message with function_call parts
          2. user message with function_response parts
        """
        from google.genai import types

        # Build the model's function_call parts
        fc_parts = []
        for tc in response.tool_calls:
            fc_parts.append(types.Part(
                function_call=types.FunctionCall(
                    name=tc.name,
                    args=tc.arguments,
                )
            ))

        messages.append({
            "role": "model",
            "parts": fc_parts,
            "_is_gemini_native": True,
        })

        # Build function_response parts
        fr_parts = []
        for tc, result in zip(response.tool_calls, results):
            # Parse the JSON result back to a dict for Gemini
            try:
                result_dict = json.loads(truncate(result.content))
            except (json.JSONDecodeError, TypeError):
                result_dict = {"raw": truncate(result.content)}

            fr_parts.append(types.Part(
                function_response=types.FunctionResponse(
                    name=tc.name,
                    response=result_dict,
                )
            ))

        messages.append({
            "role": "user",
            "parts": fr_parts,
            "_is_gemini_native": True,
        })

        return messages

    def get_name(self) -> str:
        return f"gemini ({self.model})"


# =============================================================================
# HELPERS
# =============================================================================


def _clean_schema_for_gemini(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean JSON Schema for Gemini compatibility.

    Gemini's FunctionDeclaration doesn't support "default" in properties,
    so we strip those out.
    """
    cleaned = dict(schema)
    if "properties" in cleaned:
        cleaned_props = {}
        for key, value in cleaned["properties"].items():
            prop = dict(value)
            prop.pop("default", None)
            cleaned_props[key] = prop
        cleaned["properties"] = cleaned_props
    return cleaned


def _convert_messages_to_gemini(messages: List[Dict[str, Any]]):
    """
    Convert our neutral message format to Gemini Content objects.

    Handles both plain text messages and native Gemini parts
    (from append_tool_exchange).
    """
    from google.genai import types

    contents = []
    for msg in messages:
        # Already converted to Gemini native format (from append_tool_exchange)
        if msg.get("_is_gemini_native"):
            role = msg["role"]
            contents.append(types.Content(
                role=role,
                parts=msg["parts"],
            ))
        else:
            # Plain text message
            role = "user" if msg["role"] == "user" else "model"
            content = msg.get("content", "")
            if isinstance(content, str):
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part(text=content)],
                ))
            # Skip non-string content (shouldn't happen with our flow)

    return contents
