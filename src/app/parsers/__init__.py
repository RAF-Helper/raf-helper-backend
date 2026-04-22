"""Parsers package."""

from .base import BaseParser
from .pdf import PDFParser
from .docx import DocxParser
from .pptx import PptxParser
from .txt import TextParser

__all__ = ["BaseParser", "PDFParser", "DocxParser", "PptxParser", "TextParser"]
