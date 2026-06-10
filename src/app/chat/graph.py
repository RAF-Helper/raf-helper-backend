"""LangGraph state machine for agent orchestration."""

import logging
from typing import Any, Annotated, TypedDict
from operator import add

from langgraph.graph import StateGraph, START, END
from app.chat.state import AgentInput, AgentOutput
from app.schemas.agent import AgentType
from app.chat.orchestrator import Orchestrator
from app.chat.services import services
import json
from app.services.export_service import export_service

logger = logging.getLogger(__name__)

class GraphState(TypedDict):
    """State flowing through the LangGraph pipeline."""
    user_message: str
    masked_message: str
    history: list[dict[str, str]]
    file_ids: list[int]
    use_web_search: bool
    forced_agent: Any
    chosen_agent: str | None
    final_output: str | None
    agent_metadata: dict[str, Any]
    session: Any # AsyncSession
    metadata: dict[str, Any]
    # Iterative generation fields
    plan_outline: list[str] | None
    current_step: int
    accumulated_content: list[str]
    iteration_summary: str | None
    # Reviewer fields
    reviewer_passed: bool
    review_attempts: int

# Shared Orchestrator instance for routing and agent access
_shared_orchestrator = Orchestrator(services)

# Node: PII Masking
async def pii_masker_node(state: GraphState) -> dict:
    masked, spans = await services.pii.mask_text_with_spans(state["user_message"])
    # Store spans in metadata so downstream agents (like StaffAgent) can use them
    metadata = state.get("metadata", {}).copy()
    metadata["pii_spans"] = spans
    return {
        "masked_message": masked,
        "metadata": metadata
    }

# Node: Orchestrator (The new routing node)
async def orchestrator_node(state: GraphState) -> dict:
    """Routes the request to the appropriate agent using two-stage routing."""
    # Handle forced agent override
    if state["forced_agent"]:
        chosen_agent = state["forced_agent"].value if hasattr(state["forced_agent"], 'value') else str(state["forced_agent"])
        return {"chosen_agent": chosen_agent}

    # Use the orchestrator's two-stage routing (Semantic -> LLM Fallback)
    agent_type = await _shared_orchestrator.route(
        query=state["masked_message"],
        session=state["session"]
    )
    return {"chosen_agent": agent_type.value}

# --- Iterative Nodes for Abstract Agent ---

async def abstract_planner_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.abstract].planner

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
    
    try:
        outline = json.loads(output.content)
    except:
        outline = ["Introduction", "Main Content", "Conclusion"]

    return {
        "plan_outline": outline,
        "current_step": 0,
        "accumulated_content": [],
        "iteration_summary": None
    }

async def abstract_writer_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.abstract].writer

    outline = state["plan_outline"]
    step = state["current_step"]
    heading = outline[step] if outline and step < len(outline) else "Section"
    summary = state["iteration_summary"] or "No previous sections written yet."

    prompt = f"Current Heading: {heading}\n\nContext Summary: {summary}\n\nRequest: {state['masked_message']}"

    inp = AgentInput(
        message=state["user_message"],
        masked_message=prompt,
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

    new_content = state["accumulated_content"] + [f"## {heading}\n\n{output.content}"]
    return {
        "accumulated_content": new_content,
        "current_step": step + 1
    }

async def abstract_summarizer_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.abstract].summarizer

    content_to_summarize = "\n\n".join(state["accumulated_content"][-3:])

    inp = AgentInput(
        message=state["user_message"],
        masked_message=content_to_summarize,
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
    return {"iteration_summary": output.content}

async def abstract_finalizer_node(state: GraphState) -> dict:

    final_text = "\n\n".join(state["accumulated_content"])

    # Export to LaTeX
    filename = f"abstract_{state['metadata'].get('chat_id', 'unknown')}"
    filepath = export_service.export_latex(filename, final_text)

    return {
        "final_output": f"{final_text}\n\n--- Exported to LaTeX: {filepath} ---",
        "agent_metadata": {"agent_used": "abstract", "masked_query": state["masked_message"], "export_path": filepath}
    }


async def abstract_reviewer_node(state: GraphState) -> dict:
    """Review all generated sections for quality and coherence."""
    agent = _shared_orchestrator._agents[AgentType.abstract].reviewer

    content_to_review = "\n\n".join(state["accumulated_content"]) if state["accumulated_content"] else ""

    inp = AgentInput(
        message=state["user_message"],
        masked_message=content_to_review,
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

    attempts = state.get("review_attempts", 0) + 1

    try:
        review = json.loads(output.content)
        if review.get("approved"):
            return {"reviewer_passed": True, "review_attempts": attempts}

        has_revisions = review.get("revised_sections") and len(review["revised_sections"]) > 0
        if has_revisions and attempts < 3:
            revised_content = [
                f"## {section.get('title', 'Section')}\n\n{section.get('content', '')}"
                for section in review["revised_sections"]
            ]
            return {
                "accumulated_content": revised_content,
                "reviewer_passed": False,
                "review_attempts": attempts,
            }

        logger.warning("ChapterReviewer could not fix issues, proceeding to finalizer")
    except Exception as e:
        logger.error(f"Failed to parse reviewer response: {e}")

    return {"reviewer_passed": True, "review_attempts": attempts}


# --- Iterative Nodes for Presentation Agent ---

async def presentation_planner_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.presentation].planner

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
    
    try:
        outline = json.loads(output.content)
    except:
        outline = ["Introduction", "Core Concept", "Conclusion"]

    return {
        "plan_outline": outline,
        "current_step": 0,
        "accumulated_content": [],
        "iteration_summary": None
    }

async def presentation_slider_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.presentation].slider

    outline = state["plan_outline"]
    step = state["current_step"]
    heading = outline[step] if outline and step < len(outline) else "Slide"
    summary = state["iteration_summary"] or "No previous slides created yet."

    prompt = f"Current Slide Title: {heading}\n\nPrevious Slides Summary: {summary}\n\nRequest: {state['masked_message']}"

    inp = AgentInput(
        message=state["user_message"],
        masked_message=prompt,
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

    new_content = state["accumulated_content"] + [f"--- Slide {step+1}: {heading} ---\n\n{output.content}"]
    return {
        "accumulated_content": new_content,
        "current_step": step + 1
    }

async def presentation_summarizer_node(state: GraphState) -> dict:
    agent = _shared_orchestrator._agents[AgentType.presentation].summarizer

    content_to_summarize = "\n\n".join(state["accumulated_content"][-3:])

    inp = AgentInput(
        message=state["user_message"],
        masked_message=content_to_summarize,
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
    return {"iteration_summary": output.content}

async def presentation_finalizer_node(state: GraphState) -> dict:

    content_list = state["accumulated_content"]

    # If the reviewer already parsed and approved slides, use those directly
    slides = []
    for item in content_list:
        if "--- Slide" in item:
            parts = item.split("---", 2)
            # parts[1] contains " Slide X: Title ---"
            title = parts[1].split(":", 1)[1].strip().replace("---", "").strip() if ":" in parts[1] else "Untitled Slide"
            body = parts[2].strip() if len(parts) > 2 else ""
            slides.append({"title": title, "content": body})
        else:
            slides.append({"title": "Untitled Slide", "content": item})

    # Export to PPTX
    filename = f"presentation_{state['metadata'].get('chat_id', 'unknown')}"
    filepath = export_service.export_pptx(filename, slides)

    final_text = "\n\n".join(content_list)
    return {
        "final_output": f"{final_text}\n\n--- Exported to PPTX: {filepath} ---",
        "agent_metadata": {"agent_used": "presentation", "masked_query": state["masked_message"], "export_path": filepath}
    }


async def presentation_reviewer_node(state: GraphState) -> dict:
    """Review all generated slides for quality and consistency."""
    agent = _shared_orchestrator._agents[AgentType.presentation].reviewer

    content_to_review = "\n\n".join(state["accumulated_content"]) if state["accumulated_content"] else ""

    inp = AgentInput(
        message=state["user_message"],
        masked_message=content_to_review,
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

    attempts = state.get("review_attempts", 0) + 1

    try:
        review = json.loads(output.content)
        if review.get("approved"):
            return {"reviewer_passed": True, "review_attempts": attempts}

        has_revisions = review.get("revised_slides") and len(review["revised_slides"]) > 0
        # If there are revised slides and we haven't exceeded max attempts, apply fixes
        if has_revisions and attempts < 3:
            revised_content = [
                f"--- Slide {i+1}: {slide.get('title', 'Untitled')} ---\n\n{slide.get('content', '')}"
                for i, slide in enumerate(review["revised_slides"])
            ]
            return {
                "accumulated_content": revised_content,
                "reviewer_passed": False,
                "review_attempts": attempts,
            }

        # No valid revisions and not approved — push through to finalizer anyway
        logger.warning("SlidesReviewer could not fix issues, proceeding to finalizer")
    except Exception as e:
        logger.error(f"Failed to parse reviewer response: {e}")

    return {"reviewer_passed": True, "review_attempts": attempts}

# Node: Agent Execution
async def _execute_agent(state: GraphState, agent_type: AgentType) -> dict:
    """Helper to execute a specific agent and update state."""
    agent = _shared_orchestrator._agents[agent_type]

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

def route_to_agent(state: GraphState) -> str:
    """Conditional edge to route to the correct agent node."""
    agent_slug = state["chosen_agent"]
    mapping = {
        "support": "support_node",
        "events": "events_node",
        "staff": "staff_node",
        "qa": "qa_node",
        "summarizer": "summarizer_node",
        "abstract": "abstract_planner_node",
        "presentation": "presentation_planner_node",
    }
    return mapping.get(agent_slug, "support_node")

def should_continue_abstract(state: GraphState) -> str:
    """Conditional edge to determine if more chapters need to be written."""
    outline = state.get("plan_outline")
    step = state.get("current_step", 0)

    if outline and step < len(outline):
        if step > 0 and step % 3 == 0:
            return "abstract_summarizer_node"
        return "abstract_writer_node"

    # All chapters written — route to reviewer
    return "abstract_reviewer_node"

def should_continue_abstract_review(state: GraphState) -> str:
    """Conditional edge after abstract review."""
    if state.get("reviewer_passed", False):
        return "abstract_finalizer_node"
    # Not approved — re-route to writer for fixes
    return "abstract_writer_node"

def should_continue_presentation(state: GraphState) -> str:
    """Conditional edge to determine if more slides need to be created."""
    outline = state.get("plan_outline")
    step = state.get("current_step", 0)

    if outline and step < len(outline):
        if step > 0 and step % 3 == 0:
            return "presentation_summarizer_node"
        return "presentation_slider_node"

    # All slides written — route to reviewer
    return "presentation_reviewer_node"

def should_continue_presentation_review(state: GraphState) -> str:
    """Conditional edge after slide review."""
    if state.get("reviewer_passed", False):
        return "presentation_finalizer_node"
    # Not approved — re-route to slider for fixes
    return "presentation_slider_node"

def build_agent_graph():
    """Build and compile the LangGraph state machine."""
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("pii_masker", pii_masker_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("support_node", support_node)
    workflow.add_node("events_node", events_node)
    workflow.add_node("staff_node", staff_node)
    workflow.add_node("qa_node", qa_node)
    workflow.add_node("summarizer_node", summarizer_node)

    # Abstract Pipeline Nodes
    workflow.add_node("abstract_planner_node", abstract_planner_node)
    workflow.add_node("abstract_writer_node", abstract_writer_node)
    workflow.add_node("abstract_summarizer_node", abstract_summarizer_node)
    workflow.add_node("abstract_reviewer_node", abstract_reviewer_node)
    workflow.add_node("abstract_finalizer_node", abstract_finalizer_node)

    # Presentation Pipeline Nodes
    workflow.add_node("presentation_planner_node", presentation_planner_node)
    workflow.add_node("presentation_slider_node", presentation_slider_node)
    workflow.add_node("presentation_summarizer_node", presentation_summarizer_node)
    workflow.add_node("presentation_reviewer_node", presentation_reviewer_node)
    workflow.add_node("presentation_finalizer_node", presentation_finalizer_node)

    # Define Edges
    workflow.add_edge(START, "pii_masker")
    workflow.add_edge("pii_masker", "orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "support_node": "support_node",
            "events_node": "events_node",
            "staff_node": "staff_node",
            "qa_node": "qa_node",
            "summarizer_node": "summarizer_node",
            "abstract_planner_node": "abstract_planner_node",
            "presentation_planner_node": "presentation_planner_node",
        }
    )

    # Standard agent edges
    for node in ["support_node", "events_node", "staff_node", "qa_node", "summarizer_node"]:
        workflow.add_edge(node, END)

    # Abstract Iterative Flow
    workflow.add_edge("abstract_planner_node", "abstract_writer_node")
    workflow.add_conditional_edges(
        "abstract_writer_node",
        should_continue_abstract,
        {
            "abstract_writer_node": "abstract_writer_node",
            "abstract_summarizer_node": "abstract_summarizer_node",
            "abstract_reviewer_node": "abstract_reviewer_node",
        }
    )
    workflow.add_edge("abstract_summarizer_node", "abstract_writer_node")
    workflow.add_conditional_edges(
        "abstract_reviewer_node",
        should_continue_abstract_review,
        {
            "abstract_writer_node": "abstract_writer_node",
            "abstract_finalizer_node": "abstract_finalizer_node",
        }
    )
    workflow.add_edge("abstract_finalizer_node", END)

    # Presentation Iterative Flow
    workflow.add_edge("presentation_planner_node", "presentation_slider_node")
    workflow.add_conditional_edges(
        "presentation_slider_node",
        should_continue_presentation,
        {
            "presentation_slider_node": "presentation_slider_node",
            "presentation_summarizer_node": "presentation_summarizer_node",
            "presentation_reviewer_node": "presentation_reviewer_node",
        }
    )
    workflow.add_edge("presentation_summarizer_node", "presentation_slider_node")
    workflow.add_conditional_edges(
        "presentation_reviewer_node",
        should_continue_presentation_review,
        {
            "presentation_slider_node": "presentation_slider_node",
            "presentation_finalizer_node": "presentation_finalizer_node",
        }
    )
    workflow.add_edge("presentation_finalizer_node", END)

    return workflow.compile()

# Cache the compiled graph
_cached_graph = build_agent_graph()

def get_agent_graph():
    """Return the cached agent graph."""
    return _cached_graph
