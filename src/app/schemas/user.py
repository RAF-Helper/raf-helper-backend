"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    id: int
    firebase_id: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSync(BaseModel):
    """Sent by client after Firebase sign-in to create/sync the PG record."""
    firebase_id: str
    email: str
