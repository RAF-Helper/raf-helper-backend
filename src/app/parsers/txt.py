"""Text parser for plain text files."""

from pathlib import Path
from uuid import uuid4
from .base import BaseParser
from ..schemas.document import Document, DocumentChunk, DocumentFormat

class TextParser(BaseParser[str]):
    """Parser for .txt files and as a default fallback."""

    def load(self, filename: str) -> str:
        """Load file content as a string."""
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def parse(self, artifact: str, filename: str) -> Document:
        """Parse text content into a Document model."""
        # For basic text parser, we treat the whole content as one chunk for now
        # as part of initial testing. Future iterations will implement
        # the chunking strategy described in requirements.md.

        chunk = DocumentChunk(
            content=artifact,
            level1=None,
            level2=None,
            level3=None,
            metadata={"page_number": 1}
        )

        return Document(
            id=uuid4(),
            name=Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.TXT,
            document_chunks=[chunk]
        )
