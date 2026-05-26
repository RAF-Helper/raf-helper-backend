"""DOCX parser using python-docx."""

import re
import io
from pathlib import Path
from uuid import uuid4

from docx import Document as DocxDocument

from .base import BaseParser
from ..schemas.document import Document, DocumentChunk, DocumentFormat

# Regex patterns for heading detection (supports English, Russian, Belarusian)
# Matches: "1. Introduction", "Глава 1", "Article 2.1", etc.
RE_HEADING_GENERAL = re.compile(
    r'^(?:\d+\.?\s+|[Гг]лава\s+\d+|[Сс]татья\s+\d+|[SectionChapter]+\s+\d+)',
    re.IGNORECASE
)

class DocxParser(BaseParser[DocxDocument]):
    """Parser for DOCX documents with structural heading detection."""

    def load(self, filename: str) -> DocxDocument:
        """Load DOCX file into a Document object."""
        return DocxDocument(filename)

    def parse(self, artifact: DocxDocument, filename: str) -> Document:
        """Parse DOCX into a Document model with structural levels."""
        chunks: list[DocumentChunk] = []

        # Track current structural levels
        current_level1 = None
        current_level2 = None
        current_level3 = None

        # Track if styles are used at all
        has_styles = any(p.style.name.startswith('Heading') for p in artifact.paragraphs)

        for p in artifact.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name if has_styles else ""

            if has_styles and style_name.startswith('Heading 1'):
                current_level1 = text
                current_level2 = None
                current_level3 = None
                # Add heading itself as a chunk or skip? Let's skip to avoid redundancy.
                continue
            elif has_styles and style_name.startswith('Heading 2'):
                current_level2 = text
                current_level3 = None
                continue
            elif has_styles and style_name.startswith('Heading 3'):
                current_level3 = text
                continue
            else:
                # Fallback: regex detection if no styles are used
                if not has_styles and RE_HEADING_GENERAL.match(text):
                    # Simple heuristic: if it looks like a heading, treat as level1
                    # (Advanced: could check numbering to distinguish levels)
                    current_level1 = text
                    current_level2 = None
                    current_level3 = None
                    continue

            # Regular paragraph: create chunk with current structural levels
            chunks.append(DocumentChunk(
                content=text,
                level1=current_level1,
                level2=current_level2,
                level3=current_level3,
                metadata={
                    "page_number": 1,  # python-docx doesn't provide page numbers easily
                    "chapter": current_level1,
                    "article": current_level2,
                    "point": current_level3,
                }
            ))

        core = artifact.core_properties
        return Document(
            id=uuid4(),
            name=core.title or Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.DOCX,
            document_chunks=chunks
        )
