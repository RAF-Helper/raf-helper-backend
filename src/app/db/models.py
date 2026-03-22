"""Database models - matching docs/postgres_schema.md"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, MetaData
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class User(Base):
    """User model - stores Firebase auth ID."""

    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    firebase_id = Column(String(28), nullable=False, index=True)

    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    files = relationship("FileMetadata", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    """Chat session model."""

    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    files = relationship(
        "FileMetadata",
        secondary="chat_context",
        back_populates="chats",
    )


class ChatMessage(Base):
    """Individual chat message."""

    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String(5), nullable=False)  # user, system, assistant
    content = Column(Text, nullable=False)

    # Relationships
    chat = relationship("Chat", back_populates="messages")


class FileMetadata(Base):
    """Uploaded file metadata."""

    __tablename__ = "file_metadata"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String(4096), nullable=False)

    # Relationships
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
