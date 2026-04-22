"""Document schemas for parsing pipeline."""

from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    PPTX = "pptx"
    PPT = "ppt"
    MD = "md"
    RTF = "rtf"
    TXT = "txt"


class DocumentChunk(BaseModel):
    """A single chunk of a document with structural metadata."""
    content: str
    level1: Optional[str] = None  # e.g., chapter
    level2: Optional[str] = None  # e.g., article/section
    level3: Optional[str] = None  # e.g., point/subsection
    metadata: dict = {}  # additional structure info (page_number, etc.)


class Document(BaseModel):
    """Parsed document with chunks and metadata."""
    id: UUID
    name: Optional[str] = None  # extracted title
    filename: str
    format: DocumentFormat
    document_chunks: list[DocumentChunk] = []