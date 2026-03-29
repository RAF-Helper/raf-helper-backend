"""Events Elasticsearch index schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    name: str
    date_from: datetime
    date_to: datetime
    description: str
    bonus_amount: int = Field(default=0, ge=0)
    participant_amount: int = Field(default=0, ge=0)
    participant_requirements: str = ""


class EventUpdate(BaseModel):
    name: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    description: Optional[str] = None
    bonus_amount: Optional[int] = None
    participant_amount: Optional[int] = None
    participant_requirements: Optional[str] = None


class EventRead(EventCreate):
    id: str  # Elasticsearch document ID


class EventSearchResult(BaseModel):
    id: str
    score: float
    name: str
    date_from: datetime
    date_to: datetime
    description: str
    bonus_amount: int
    participant_amount: int
    participant_requirements: str
