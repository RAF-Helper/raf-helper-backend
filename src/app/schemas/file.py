"""File schemas."""

from datetime import datetime
from pydantic import BaseModel


class FileRead(BaseModel):
    id: int
    user_id: int
    original_name: str
    mime_type: str
    size: int
    is_indexed: bool
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FileUploadResponse(BaseModel):
    file: FileRead
    message: str = "File uploaded and queued for indexing."
