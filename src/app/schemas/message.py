"""Message schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class MessageRead(BaseModel):
    id: int
    chat_id: int
    role: MessageRole
    content: str
    agent_used: Optional[str] = None
    export_path: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
