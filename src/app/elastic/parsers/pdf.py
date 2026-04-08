"""PDF parser using pypdf."""

import io
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .base import BaseParser


class PDFParser(BaseParser):
    """Parser for PDF documents."""

    def parse_file(self, file_path: str | Path) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._parse(f.read(), str(Path(file_path).name))

    def parse_bytes(self, data: bytes, filename: str | None = None) -> dict[str, Any]:
        return self._parse(data, filename or "document.pdf")

    def _parse(self, data: bytes, filename: str) -> dict[str, Any]:
        reader = PdfReader(io.BytesIO(data))
        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text.strip())

        full_text = "\n\n".join(p for p in pages_text if p)
        info = reader.metadata or {}

        return {
            "text": full_text,
            "metadata": {
                "filename": filename,
                "page_count": len(reader.pages),
                "title": info.get("/Title", ""),
                "author": info.get("/Author", ""),
            },
        }
