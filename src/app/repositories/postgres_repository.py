"""PostgreSQL repository implementations."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete
from sqlalchemy.exc import IntegrityError

from app.repositories.base import BaseRepository
from app.db.models import User, Chat, ChatMessage, FileMetadata, ChatContext


class UserRepository(BaseRepository[User]):
    """Repository for User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_firebase_id(self, firebase_id: str) -> User | None:
        """Get user by Firebase ID."""
        result = await self.session.execute(
            select(User).where(User.firebase_id == firebase_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, firebase_id: str) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_firebase_id(firebase_id)
        if user is None:
            user = await self.create(firebase_id=firebase_id)
        return user


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Chat, session)

    async def get_by_user(self, user_id: int) -> list[Chat]:
        """Get all chats for a user."""
        result = await self.session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.id.desc())
        )
        return result.scalars().all()


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository for ChatMessage model."""

    def __init__(self, session: AsyncSession):
        super().__init__(ChatMessage, session)

    async def get_by_chat(self, chat_id: int) -> list[ChatMessage]:
        """Get all messages for a chat, in order."""
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.id.asc())
        )
        return result.scalars().all()

    async def create_message(self, chat_id: int, role: str, content: str, export_path: str | None = None) -> ChatMessage:
        """Create a new chat message."""
        return await self.create(chat_id=chat_id, role=role, content=content, export_path=export_path)


class FileMetadataRepository(BaseRepository[FileMetadata]):
    """Repository for FileMetadata model."""

    def __init__(self, session: AsyncSession):
        super().__init__(FileMetadata, session)

    async def get_by_user(self, user_id: int) -> list[FileMetadata]:
        """Get all files for a user."""
        result = await self.session.execute(
            select(FileMetadata)
            .where(FileMetadata.user_id == user_id)
            .order_by(FileMetadata.id.desc())
        )
        return result.scalars().all()
    
    async def get_uuids(self, ids: int) -> list[uuid.UUID]:
        """Get uuids of all files with ids."""
        result = await self.session.execute(
            select(FileMetadata.document_id)
            .where(FileMetadata.id.in_(ids))
            .order_by(FileMetadata.id.desc())
        )
        return result.scalars().all()
    
    async def get_by_uuid(self, uuid: str) -> list[FileMetadata]:
        """Get file be uuid."""
        result = await self.session.execute(
            select(FileMetadata)
            .where(FileMetadata.document_id == uuid)
        )
        return result.scalars().one_or_none()

    async def get_by_ids(self, ids: list[int]) -> list[FileMetadata]:
        """Get multiple files by their IDs."""
        result = await self.session.execute(
            select(FileMetadata).where(FileMetadata.id.in_(ids))
        )
        return result.scalars().all()


class ChatContextRepository:
    """Repository for chat_context join table (not using BaseRepository)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def link_file_to_chat(self, chat_id: int, file_id: int) -> bool:
        """Link a file to a chat (add to chat_context)."""
        stmt = insert(ChatContext).values(chat_id=chat_id, file_id=file_id)
        try:
            await self.session.execute(stmt)
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def unlink_file_from_chat(self, chat_id: int, file_id: int) -> bool:
        """Remove file-chat association."""
        stmt = delete(ChatContext).where(
            ChatContext.chat_id == chat_id,
            ChatContext.file_id == file_id
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def get_files_for_chat(self, chat_id: int) -> list[FileMetadata]:
        """Get all files linked to a chat."""
        result = await self.session.execute(
            select(FileMetadata)
            .join(ChatContext, FileMetadata.id == ChatContext.file_id)
            .where(ChatContext.chat_id == chat_id)
        )
        return result.scalars().all()

    async def get_chats_for_file(self, file_id: int) -> list[Chat]:
        """Get all chats linked to a file."""
        result = await self.session.execute(
            select(Chat)
            .join(ChatContext, Chat.id == ChatContext.chat_id)
            .where(ChatContext.file_id == file_id)
        )
        return result.scalars().all()
