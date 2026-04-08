"""Parsers package."""

from .base import BaseParser
from .pdf import PDFParser
from .docx import DocxParser
from .pptx import PptxParser

__all__ = ["BaseParser", "PDFParser", "DocxParser", "PptxParser"]
