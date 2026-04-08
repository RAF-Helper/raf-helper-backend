"""LangGraph state machine builder — stub."""

from typing import Any
from dataclasses import dataclass, field

from ..schemas.agent import AgentType
from .state import AgentInput, AgentOutput


@dataclass
class GraphState:
    """State flowing through the LangGraph pipeline."""

    input: AgentInput | None = None
    output: AgentOutput | None = None
    next_node: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_agent_graph():
    """Build the LangGraph state machine.

    TODO: implement nodes and edges:
      1. pii_masker_node
      2. router_node
      3. support_node / events_node / staff_node / qa_node
      4. summarizer_node / abstract_node / presentation_node
    """
    raise NotImplementedError(
        "LangGraph builder not yet implemented. Use Orchestrator directly."
    )
