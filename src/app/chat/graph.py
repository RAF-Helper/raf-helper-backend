"""LangGraph state machine for agent orchestration."""

import logging
from typing import Any, Annotated, TypedDict
from operator import add

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage

from .state import AgentInput, AgentOutput
from ..schemas.agent import AgentType
from ..pii.presidio_masker import PIIMasker
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    """State flowing through the LangGraph pipeline."""
    user_message: str
    masked_message: str
    history: list[dict[str, str]]
    file_ids: list[str]
    use_web_search: bool
    forced_agent: Any
    chosen_agent: str | None
    final_output: str | None
    agent_metadata: dict[str, Any]
    session: Any # AsyncSession
    metadata: dict[str, Any]

# Node: PII Masking
async def pii_masker_node(state: GraphState) -> dict:
    masker = PIIMasker()
    masked, spans = await masker.mask_text_with_spans(state["user_message"])
    return {"masked_message": masked}

# Node: Routing
async def router_node(state: GraphState) -> dict:
    orchestrator = Orchestrator()
    # Use the existing routing logic from orchestrator
    # We pass the masked message as the query
    agent_type = await orchestrator._route(state["masked_message"])

    # Handle forced agent override
    if state["forced_agent"]:
        agent_type = state["forced_agent"]

    return {"chosen_agent": agent_type.value if hasattr(agent_type, 'value') else str(agent_type)}

# Node: Agent Execution
async def _execute_agent(state: GraphState, agent_type: AgentType) -> dict:
    """Helper to execute a specific agent and update state."""
    orchestrator = Orchestrator()
    agent = orchestrator._agents[agent_type]

    # Construct AgentInput from state
    inp = AgentInput(
        message=state["user_message"],
        masked_message=state["masked_message"],
        chat_id=state["metadata"].get("chat_id"),
        user_id=state["metadata"].get("user_id"),
        history=state["history"],
        file_ids=state["file_ids"],
        use_web_search=state["use_web_search"],
        summarization_mode=state["metadata"].get("summarization_mode"),
        forced_agent=state["forced_agent"],
        pii_spans=state["metadata"].get("pii_spans"),
    )

    output = await agent.run(inp)

    return {
        "final_output": output.content,
        "agent_metadata": {
            "agent_used": output.agent_used,
            "masked_query": output.masked_query
        }
    }

async def support_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.support)

async def events_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.events)

async def staff_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.staff)

async def qa_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.qa)

async def summarizer_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.summarizer)

async def abstract_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.abstract)

async def presentation_node(state: GraphState) -> dict:
    return await _execute_agent(state, AgentType.presentation)

def route_to_agent(state: GraphState) -> str:
    """Conditional edge to route to the correct agent node."""
    agent_slug = state["chosen_agent"]
    mapping = {
        "support": "support_node",
        "events": "events_node",
        "staff": "staff_node",
        "qa": "qa_node",
        "summarizer": "summarizer_node",
        "abstract": "abstract_node",
        "presentation": "presentation_node",
    }
    return mapping.get(agent_slug, "support_node")

def build_agent_graph():
    """Build and compile the LangGraph state machine."""
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("pii_masker", pii_masker_node)
    workflow.add_node("router", router_node)
    workflow.add_node("support_node", support_node)
    workflow.add_node("events_node", events_node)
    workflow.add_node("staff_node", staff_node)
    workflow.add_node("qa_node", qa_node)
    workflow.add_node("summarizer_node", summarizer_node)
    workflow.add_node("abstract_node", abstract_node)
    workflow.add_node("presentation_node", presentation_node)

    # Define Edges
    workflow.add_edge(START, "pii_masker")
    workflow.add_edge("pii_masker", "router")

    # Conditional routing from router to specific agent nodes
    workflow.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "support_node": "support_node",
            "events_node": "events_node",
            "staff_node": "staff_node",
            "qa_node": "qa_node",
            "summarizer_node": "summarizer_node",
            "abstract_node": "abstract_node",
            "presentation_node": "presentation_node",
        }
    )

    # All agent nodes lead to END
    for node in ["support_node", "events_node", "staff_node", "qa_node", "summarizer_node", "abstract_node", "presentation_node"]:
        workflow.add_edge(node, END)

    return workflow.compile()
