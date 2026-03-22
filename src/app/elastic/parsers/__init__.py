"""Parsers package."""

from .base import BaseParser
from .pdf import PDFParser
from .docx import DocxParser

__all__ = ["BaseParser", "PDFParser", "DocxParser"]
