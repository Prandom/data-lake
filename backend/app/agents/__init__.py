"""
Week 4: Agent module.

Contains the multi-provider agent system for conversational
queries across the personal data lake.

Usage:
    from app.agents.agent import DataLakeAgent, get_agent_provider
    from app.agents.tool_executor import ToolExecutor

    provider = get_agent_provider()  # reads AGENT_PROVIDER from .env
    executor = ToolExecutor(db=db, allowed_paths=paths)
    agent = DataLakeAgent(provider=provider, executor=executor)
    result = await agent.query("What are my notes on binary search?")

Providers (set via AGENT_PROVIDER in .env):
    - gemini  (default, free, cloud)
    - claude  (paid, cloud, best quality)
    - ollama  (free, local, fully offline)
"""
