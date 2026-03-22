"""DOCX parser implementation (skeleton)."""

from pathlib import Path
from typing import Any
from .base import BaseParser


class DocxParser(BaseParser):
    """Parser for DOCX documents."""

    def parse_file(self, file_path: str | Path) -> dict[str, Any]:
        """Parse DOCX from file."""
        raise NotImplementedError("Implement DOCX parsing with python-docx")

    def parse_bytes(self, data: bytes, filename: str | None = None) -> dict[str, Any]:
        """Parse DOCX from bytes."""
        raise NotImplementedError("Implement DOCX parsing from bytes")
