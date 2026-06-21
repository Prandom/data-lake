"""
Agent provider abstraction — common types and base class.

This mirrors the EmbeddingProvider pattern from Week 3:
define an ABC, implement per provider, swap via .env.

The key types:
  - ToolCall: what the LLM wants to execute
  - ToolResult: what we send back after executing
  - LLMResponse: normalised response from any provider
  - AgentProvider: the ABC that each LLM implements
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =============================================================================
# COMMON TYPES
# =============================================================================


@dataclass
class ToolCall:
    """
    A tool call requested by the LLM.

    Every provider produces these in different formats, but the
    provider's call() method normalises them into this shape.
    """

    id: str  # unique ID for this call (provider assigns it)
    name: str  # "vector_search", "filesystem_list_files", etc.
    arguments: Dict[str, Any]  # parsed arguments


@dataclass
class ToolResult:
    """
    Result of executing a tool call.

    Sent back to the LLM so it can reason about the output.
    """

    call_id: str  # matches ToolCall.id
    content: str  # JSON-serialized result (truncated if needed)


@dataclass
class LLMResponse:
    """
    Normalised response from any LLM provider.

    Either the LLM is done (text + is_done=True) or it wants
    more tool calls (tool_calls list + is_done=False).
    """

    text: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    is_done: bool = False
    raw_response: Optional[Any] = None  # provider-specific, for append_tool_exchange


# =============================================================================
# SYSTEM PROMPT (shared across all providers)
# =============================================================================

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


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class AgentProvider(ABC):
    """
    Abstract base for LLM providers.

    Each provider knows how to:
    1. Convert provider-neutral tool definitions into its native format
    2. Make a single LLM call with messages + tools
    3. Parse the response into our common LLMResponse format
    4. Format tool results for the next round of the agentic loop
    """

    @abstractmethod
    def call(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ) -> LLMResponse:
        """
        Make a single LLM call.

        Args:
            messages: conversation history (provider formats internally)
            tools: tool definitions in provider-neutral format

        Returns:
            LLMResponse with either text (done) or tool_calls (needs more)
        """
        ...

    @abstractmethod
    def append_tool_exchange(
        self,
        messages: List[Dict[str, Any]],
        response: LLMResponse,
        results: List[ToolResult],
    ) -> List[Dict[str, Any]]:
        """
        Append tool call + result to message history.

        Each provider has a different format for representing
        "assistant called tools, here are the results". This method
        handles that conversion.

        Returns:
            Updated messages list with tool exchange appended.
        """
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name for logging/API response."""
        ...
