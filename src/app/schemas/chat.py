"""Chat schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=256)
    is_web_search_enabled: bool = False


class ChatUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=256)
    is_web_search_enabled: Optional[bool] = None


class ChatRead(BaseModel):
    id: int
    user_id: int
    title: str
    is_web_search_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}
