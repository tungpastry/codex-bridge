from __future__ import annotations


def recommended_tool_to_route(recommended_tool: str) -> str:
    if recommended_tool in ("codex", "gemini", "human", "local"):
        return recommended_tool
    return "local"
