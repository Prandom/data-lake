"""
Week 4: MCP tool definitions — provider-neutral format.

Each tool maps to an existing backend capability — vector search,
filesystem listing, filesystem reading. The LLM sees these as
callable tools and decides which to invoke.

Format: provider-neutral. Uses "parameters" (OpenAPI standard).
Each AgentProvider converts these to its native format:
  - Claude: renames "parameters" → "input_schema"
  - Gemini: wraps in FunctionDeclaration
  - Ollama: uses as-is (OpenAI-compatible)

Design decision: vector_search is listed first because it should be
the LLM's primary retrieval mechanism. The filesystem tools are
fallbacks for when the LLM needs to browse or read a specific file
that didn't come up in search results.
"""

TOOLS = [
    {
        "name": "vector_search",
        "description": (
            "Semantically search across all indexed local files using natural "
            "language. Returns the most relevant text chunks with file paths "
            "and similarity scores. Use this FIRST to answer questions about "
            "the user's documents, notes, code, and files. The search uses "
            "cosine similarity on embeddings, so phrasing matters less than "
            "meaning."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language search query",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 20)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "filesystem_list_files",
        "description": (
            "List files and directories in a local directory path. Returns "
            "file names, sizes, types (file/directory), and modification "
            "dates. Use this to browse the user's filesystem when they ask "
            "about what files they have or where something is located. "
            "Only paths within configured allowed roots will work."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list",
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files (starting with '.')",
                    "default": False,
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "filesystem_read_file",
        "description": (
            "Read the full text content of a specific local file. Use this "
            "when you need to see the complete contents of a file, for "
            "example after vector_search returns a relevant chunk and the "
            "user wants more detail from that file. Only works for text "
            "files under 10MB within allowed paths."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
            },
            "required": ["path"],
        },
    },
]
