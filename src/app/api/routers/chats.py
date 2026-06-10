"""Chat session and messaging endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.chat_service import ChatService, ChatNotFoundError
from app.services.user_service import UserService
from app.services.document_service import DocumentService
from app.api.auth.firebase import verify_firebase_token
from app.schemas.chat import ChatCreate, ChatRead, ChatUpdate
from app.schemas.message import MessageRead
from app.schemas.file import FileRead
from app.schemas.agent import ChatMessageRequest, AgentChatResponse
from app.chat.graph import get_agent_graph
from app.chat.services import services
from app.chat.orchestrator import Orchestrator

router = APIRouter(prefix="/chats", tags=["chats"])

logger = logging.getLogger(__name__)

async def _resolve_user_id(firebase_uid: str, session: AsyncSession) -> int:
    user = await UserService(session).get_by_firebase_id(firebase_uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User not found. Call POST /auth/sync first.")
    return user.id


# ------------------------------------------------------------------ #
# Chat CRUD                                                             #
# ------------------------------------------------------------------ #

@router.post("/", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    body: ChatCreate,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    user_id = await _resolve_user_id(firebase_uid, session)
    chat = await ChatService(session).create_chat(
        user_id=user_id, title=body.title, is_web_search_enabled=body.is_web_search_enabled,
    )
    return ChatRead.model_validate(chat)


@router.get("/", response_model=list[ChatRead])
async def list_chats(
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> list[ChatRead]:
    user_id = await _resolve_user_id(firebase_uid, session)
    chats = await ChatService(session).list_chats(user_id)
    return [ChatRead.model_validate(c) for c in chats]


@router.get("/{chat_id}", response_model=ChatRead)
async def get_chat(
    chat_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    user_id = await _resolve_user_id(firebase_uid, session)
    chat = await ChatService(session).get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    return ChatRead.model_validate(chat)


@router.patch("/{chat_id}", response_model=ChatRead)
async def update_chat(
    chat_id: int,
    body: ChatUpdate,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> ChatRead:
    user_id = await _resolve_user_id(firebase_uid, session)
    updates = body.model_dump(exclude_none=True)
    chat = await ChatService(session).update_chat(chat_id, user_id, **updates)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = await _resolve_user_id(firebase_uid, session)
    deleted = await ChatService(session).delete_chat(chat_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")


# ------------------------------------------------------------------ #
# Messages                                                              #
# ------------------------------------------------------------------ #

@router.get("/{chat_id}/messages", response_model=list[MessageRead])
async def get_messages(
    chat_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> list[MessageRead]:
    user_id = await _resolve_user_id(firebase_uid, session)
    try:
        messages = await ChatService(session).get_history(chat_id, user_id)
    except ChatNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    return [MessageRead.model_validate(m) for m in messages]


@router.post("/{chat_id}/messages", response_model=AgentChatResponse)
async def send_message(
    chat_id: int,
    body: ChatMessageRequest,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> AgentChatResponse:
    """Send a user message → route through agent graph → return agent response."""
    user_id = await _resolve_user_id(firebase_uid, session)
    svc = ChatService(session)

    chat = await svc.get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")

    await svc.save_user_message(chat_id, body.message)

    history = await svc.get_history_as_messages(chat_id, user_id, limit=40)
    file_ids = await svc.get_context_file_ids(chat_id)

    # Use the cached agent graph
    graph = get_agent_graph()

    initial_state = {
        "user_message": body.message,
        "masked_message": "",
        "history": history,
        "file_ids": file_ids,
        "use_web_search": chat.is_web_search_enabled,
        "forced_agent": body.agent,
        "chosen_agent": None,
        "final_output": None,
        "agent_metadata": {},
        "session": session,
        "metadata": {
            "chat_id": chat_id,
            "user_id": user_id,
            "summarization_mode": body.summarization_mode
        },
        "plan_outline": None,
        "current_step": 0,
        "accumulated_content": [],
        "iteration_summary": None,
        "reviewer_passed": False,
        "review_attempts": 0,
    }

    try:
        # Use a savepoint to ensure that a graph failure doesn't roll back the user message
        async with session.begin_nested():
            final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Graph execution failed: {e}", exc_info=True)
        # session.begin_nested() automatically rolls back to the savepoint on exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent processing error: {str(e)}"
        )

    result_content = final_state["final_output"]
    agent_used = final_state["agent_metadata"].get("agent_used")
    masked_query = final_state["agent_metadata"].get("masked_query")

    msg = await svc.save_message(chat_id, role="assistant", content=result_content)
    return AgentChatResponse(
        message_id=msg.id,
        chat_id=chat_id,
        content=result_content,
        agent_used=agent_used,
        masked_query=masked_query,
    )


# ------------------------------------------------------------------ #
# Context file linking                                                  #
# ------------------------------------------------------------------ #

@router.get("/{chat_id}/context", response_model=list[FileRead])
async def get_context_files(
    chat_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> list[FileRead]:
    user_id = await _resolve_user_id(firebase_uid, session)
    chat = await ChatService(session).get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    from app.repositories.postgres_repository import ChatContextRepository
    files = await ChatContextRepository(session).get_files_for_chat(chat_id)
    return [FileRead.model_validate(f) for f in files]


@router.post("/{chat_id}/context/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_context_file(
    chat_id: int,
    file_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = await _resolve_user_id(firebase_uid, session)
    chat = await ChatService(session).get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    linked = await DocumentService(session).link_to_chat(file_id, chat_id, user_id)
    if not linked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")


@router.delete("/{chat_id}/context/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_context_file(
    chat_id: int,
    file_id: int,
    firebase_uid: str = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session),
) -> None:
    user_id = await _resolve_user_id(firebase_uid, session)
    chat = await ChatService(session).get_chat(chat_id, user_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
    await DocumentService(session).unlink_from_chat(file_id, chat_id)
