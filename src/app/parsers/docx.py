"""DOCX parser using python-docx."""

import io
from pathlib import Path
from uuid import uuid4

from docx import Document as DocxDocument

from .base import BaseParser
from ..schemas.document import Document, DocumentChunk, DocumentFormat

class DocxParser(BaseParser[DocxDocument]):
    """Parser for DOCX documents."""

    def load(self, filename: str) -> DocxDocument:
        """Load DOCX file into a Document object."""
        return DocxDocument(filename)

    def parse(self, artifact: DocxDocument, filename: str) -> Document:
        """Parse DOCX into a Document model."""
        chunks: list[DocumentChunk] = []

        # Basic structural extraction: group by paragraphs
        # Future improvement: detect headings to populate level1, level2, etc.
        for p in artifact.paragraphs:
            text = p.text.strip()
            if text:
                chunks.append(DocumentChunk(
                    content=text,
                    level1=None,
                    level2=None,
                    level3=None,
                    metadata={"page_number": 1} # python-docx doesn't provide page numbers easily
                ))

        core = artifact.core_properties
        return Document(
            id=uuid4(),
            name=core.title or Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.DOCX,
            document_chunks=chunks
        )
