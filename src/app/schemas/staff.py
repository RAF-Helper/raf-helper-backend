"""Staff Elasticsearch index schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class StaffCreate(BaseModel):
    name: str
    surname: str
    fathers_name: Optional[str] = None
    position: str
    room: str  # Can be "619a", "A-101", etc.
    department: str
    competences: str = Field(description="Free-text list of competences.")
    description: str = Field(description="Short biography / role description.")


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    fathers_name: Optional[str] = None
    position: Optional[str] = None
    room: Optional[str] = None
    department: Optional[str] = None
    competences: Optional[str] = None
    description: Optional[str] = None


class StaffRead(StaffCreate):
    id: str  # Elasticsearch document ID


class StaffSearchResult(BaseModel):
    id: str
    score: float
    name: str
    surname: str
    fathers_name: Optional[str] = None
    position: str
    room: str
    department: str
    competences: str
    description: str
