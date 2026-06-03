"""Chat and message management service."""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chat, ChatMessage
from app.repositories.postgres_repository import (
    ChatRepository, ChatMessageRepository, ChatContextRepository
)


class ChatNotFoundError(Exception):
    pass


class ChatService:
    def __init__(self, session: AsyncSession):
        self.chat_repo = ChatRepository(session)
        self.msg_repo = ChatMessageRepository(session)
        self.ctx_repo = ChatContextRepository(session)

    # ------------------------------------------------------------------ #
    # Chat CRUD                                                             #
    # ------------------------------------------------------------------ #

    async def create_chat(
        self,
        user_id: int,
        title: str = "New Chat",
        is_web_search_enabled: bool = False,
    ) -> Chat:
        return await self.chat_repo.create(
            user_id=user_id,
            title=title,
            is_web_search_enabled=is_web_search_enabled,
        )

    async def get_chat(self, chat_id: int, user_id: int) -> Optional[Chat]:
        chat = await self.chat_repo.get(chat_id)
        if chat and chat.user_id == user_id:
            return chat
        return None

    async def list_chats(self, user_id: int) -> list[Chat]:
        return await self.chat_repo.get_by_user(user_id)

    async def update_chat(self, chat_id: int, user_id: int, **kwargs) -> Optional[Chat]:
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            return None
        return await self.chat_repo.update(chat_id, **kwargs)

    async def delete_chat(self, chat_id: int, user_id: int) -> bool:
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            return False
        return await self.chat_repo.delete(chat_id)

    # ------------------------------------------------------------------ #
    # Messages                                                              #
    # ------------------------------------------------------------------ #

    async def get_history(self, chat_id: int, user_id: int) -> list[ChatMessage]:
        chat = await self.get_chat(chat_id, user_id)
        if not chat:
            raise ChatNotFoundError(chat_id)
        return await self.msg_repo.get_by_chat(chat_id)

    async def save_user_message(self, chat_id: int, content: str) -> ChatMessage:
        return await self.msg_repo.create_message(chat_id, role="user", content=content)

    async def save_message(self, chat_id: int, role: str, content: str) -> ChatMessage:
        return await self.msg_repo.create_message(chat_id, role=role, content=content)

    # ------------------------------------------------------------------ #
    # Context files                                                         #
    # ------------------------------------------------------------------ #

    async def get_context_file_ids(self, chat_id: int) -> list[str]:
        """Get document UUIDs for files linked to a chat."""
        files = await self.ctx_repo.get_files_for_chat(chat_id)
        return [str(f.document_id) for f in files]

    async def get_history_as_messages(
        self, chat_id: int, user_id: int, limit: int = 40
    ) -> list[dict[str, str]]:
        """Return last *limit* messages as [{"role": ..., "content": ...}] dicts."""
        messages = await self.get_history(chat_id, user_id)
        tail = messages[-limit:] if len(messages) > limit else messages
        return [{"role": m.role, "content": m.content} for m in tail]
