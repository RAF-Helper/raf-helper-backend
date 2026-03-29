"""Chat API router - interface to the multiagent system."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from ..auth.firebase import verify_firebase_token
from app.chat.orchestrator import Orchestrator
from app.schemas.agent import AgentType, SummarizationMode

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str
    agent: Optional[AgentType] = None
    context_material_ids: Optional[list[int]] = None
    use_web_search: bool = False


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    response: str
    agent_used: str
    metadata: Optional[dict] = None


# Global orchestrator instance (will be initialized on startup)
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or initialize the orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(verify_firebase_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """
    Process a chat message through the multiagent system.

    - If agent is specified, bypasses the router and sends directly to that agent.
    - Otherwise, the orchestrator routes to the appropriate agent.
    """
    try:
        response = await orchestrator.process(
            message=request.message,
            chat_id=0,  # stateless endpoint — no persistent chat session
            user_id=0,
            history=[],
            file_ids=request.context_material_ids or [],
            use_web_search=request.use_web_search,
            forced_agent=request.agent,
            summarization_mode=SummarizationMode.default,
            session=None,
        )
        return ChatResponse(
            response=response.content,
            agent_used=response.agent_used.value,
            metadata=response.metadata,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}",
        )
