"""LangGraph graph builder for agent workflows."""

from typing import Any
from langgraph.graph import StateGraph, END
from dataclasses import dataclass, field


@dataclass
class AgentState:
    """State for LangGraph agents."""

    messages: list[dict[str, str]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    next: str | None = None


def build_agent_graph() -> StateGraph:
    """
    Build the LangGraph state machine for agent orchestration.

    Returns:
        Compiled StateGraph ready for execution
    """
    raise NotImplementedError("Implement LangGraph builder")
    # TODO:
    # 1. Define state schema
    # 2. Add nodes (router, support, events, staff, qa, summarizer, etc.)
    # 3. Add conditional edges for routing
    # 4. Compile and return graph
