"""Database models."""

import uuid
from sqlalchemy import (
    Column, BigInteger, String, Text, ForeignKey, MetaData,
    DateTime, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    firebase_id = Column(String(128), nullable=False, unique=True, index=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    files = relationship("FileMetadata", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), nullable=False, default="New Chat")
    is_web_search_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan", order_by="ChatMessage.id")
    files = relationship(
        "FileMetadata",
        secondary="chat_context",
        back_populates="chats",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    agent_used = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    chat = relationship("Chat", back_populates="messages")


class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(4096), nullable=False)
    original_name = Column(String(512), nullable=False)
    mime_type = Column(String(128), nullable=False, default="application/octet-stream")
    size = Column(BigInteger, nullable=False, default=0)
    is_indexed = Column(Boolean, nullable=False, default=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # New fields for document parsing
    document_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True, index=True)
    name = Column(String(1024), nullable=True)  # extracted document title
    format = Column(String(32), nullable=False)  # pdf, docx, pptx, txt

    user = relationship("User", back_populates="files")
    chats = relationship(
        "Chat",
        secondary="chat_context",
        back_populates="files",
    )


class ChatContext(Base):
    """Join table linking chats and files (many-to-many)."""

    __tablename__ = "chat_context"

    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    file_id = Column(BigInteger, ForeignKey("file_metadata.id", ondelete="CASCADE"), primary_key=True)
