"""DOCX parser using python-docx."""

import io
from pathlib import Path
from typing import Any

from docx import Document

from .base import BaseParser


class DocxParser(BaseParser):
    """Parser for DOCX documents."""

    def parse_file(self, file_path: str | Path) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._parse(f.read(), str(Path(file_path).name))

    def parse_bytes(self, data: bytes, filename: str | None = None) -> dict[str, Any]:
        return self._parse(data, filename or "document.docx")

    def _parse(self, data: bytes, filename: str) -> dict[str, Any]:
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)

        core = doc.core_properties
        return {
            "text": full_text,
            "metadata": {
                "filename": filename,
                "title": core.title or "",
                "author": core.author or "",
                "paragraph_count": len(paragraphs),
            },
        }
