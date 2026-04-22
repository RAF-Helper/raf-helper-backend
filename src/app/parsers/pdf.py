"""PDF parser using pypdf."""

import io
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from .base import BaseParser
from ..schemas.document import Document, DocumentChunk, DocumentFormat

class PDFParser(BaseParser[PdfReader]):
    """Parser for PDF documents."""

    def load(self, filename: str) -> PdfReader:
        """Load PDF into a PdfReader object."""
        with open(filename, "rb") as f:
            return PdfReader(io.BytesIO(f.read()))

    def parse(self, artifact: PdfReader, filename: str) -> Document:
        """Parse PDF into a Document model with structural blocks (pages)."""
        pages_chunks: list[DocumentChunk] = []

        # For the initial version, we treat each page as a structural block.
        # Real structural extraction (headings) would happen here.
        for i, page in enumerate(artifact.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_chunks.append(DocumentChunk(
                    content=text.strip(),
                    level1=None,
                    level2=None,
                    level3=None,
                    metadata={"page_number": i + 1}
                ))

        info = artifact.metadata or {}

        return Document(
            id=uuid4(),
            name=info.get("/Title", Path(filename).stem),
            filename=Path(filename).name,
            format=DocumentFormat.PDF,
            document_chunks=pages_chunks
        )
