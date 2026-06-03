"""PDF parser using pdfplumber for font analysis and structure detection."""

import re
from pathlib import Path
from uuid import uuid4

import pdfplumber

from app.parsers.base import BaseParser
from app.schemas.document import Document, DocumentChunk, DocumentFormat

# Heuristic thresholds
FONT_SIZE_LEVEL1 = 16.0
FONT_SIZE_LEVEL2 = 13.0
SLIDE_ASPECT_RATIO_THRESHOLD = 1.3  # w/h > this suggests slides
SLIDE_IMG_TEXT_RATIO = 0.5  # High image to text ratio suggests slides

# Regex for heading detection (supports English, Russian, Belarusian)
RE_HEADING = re.compile(
    r'^(?:\d+\.?\s+|[Гг]лава\s+\d+|[Сс]татья\s+\d+|[SectionChapter]+\s+\d+)',
    re.IGNORECASE
)


class PDFParser(BaseParser[pdfplumber.PDF]):
    """Parser for PDF documents with structural heading detection."""

    def load(self, filename: str) -> pdfplumber.PDF:
        """Load PDF into a pdfplumber PDF object."""
        return pdfplumber.open(filename)

    def _detect_pdf_type(self, pdf: pdfplumber.PDF) -> str:
        """Detect if PDF is 'slides', 'book', or 'article'."""
        if len(pdf.pages) == 0:
            return "book"  # default

        first_page = pdf.pages[0]
        width = first_page.width or 0
        height = first_page.height or 1

        # Check aspect ratio
        if (width / height) > SLIDE_ASPECT_RATIO_THRESHOLD:
            return "slides"

        # Check image-to-text ratio on first few pages (simplified)
        text_count = 0
        img_count = 0
        for page in pdf.pages[:3]:
            text_count += len(page.chars)
            img_count += len(page.images)

        if img_count > text_count * SLIDE_IMG_TEXT_RATIO:
            return "slides"

        return "book"  # or "article", but treating as book for now

    def _extract_page_structure(self, page: pdfplumber.page.Page) -> list[dict]:
        """
        Extract text blocks with font size and position.
        Returns list of {'text': str, 'font_size': float, 'top': float, 'is_heading': bool}.
        """
        words = page.extract_words(
            use_text_flow=True,
            keep_blank_chars=False,
        )

        # Group words into lines and get font sizes from chars
        lines = {}
        for w in words:
            top = round(w['top'])
            if top not in lines:
                lines[top] = {'text': "", 'sizes': []}
            lines[top]['text'] += w['text'] + ' '
            # Get font size from chars (need to access page.chars here carefully)
            # Simplified: we'll get sizes from the page.chars manually later.

        # Now get font sizes for each line
        chars = page.chars
        for c in chars:
            top = round(c['top'])
            if top in lines:
                lines[top]['sizes'].append(c['size'])

        # Average font size per line
        structure = []
        for top in sorted(lines.keys()):
            line_data = lines[top]
            text = line_data['text'].strip()
            if not text:
                continue
            avg_size = sum(line_data['sizes']) / len(line_data['sizes']) if line_data['sizes'] else 0
            is_bold = any('Bold' in c.get('fontname', '') for c in chars if round(c['top']) == top)

            # Determine if it's a heading
            is_heading = False
            if avg_size >= FONT_SIZE_LEVEL1:
                level = 1
                is_heading = True
            elif avg_size >= FONT_SIZE_LEVEL2:
                level = 2
                is_heading = True
            else:
                level = None

            # Regex check for heading patterns (e.g., "1. Introduction")
            if RE_HEADING.match(text):
                level = 1 if not level or level > 1 else level
                is_heading = True

            structure.append({
                'text': text,
                'font_size': avg_size,
                'top': top,
                'level': level if is_heading else None,
                'is_heading': is_heading,
            })

        return structure

    def parse(self, artifact: pdfplumber.PDF, filename: str) -> Document:
        """Parse PDF into a Document model with structural levels."""
        pdf_type = self._detect_pdf_type(artifact)

        if pdf_type == "slides":
            return self._parse_slides(artifact, filename)
        else:
            return self._parse_book(artifact, filename)

    def _parse_slides(self, pdf: pdfplumber.PDF, filename: str) -> Document:
        """Parse PDF as slides (similar to PptxParser)."""
        chunks = []
        for i, page in enumerate(pdf.pages):
            # Try to find a title (largest font text at top of page)
            chars = page.chars
            lines = {}
            for c in chars:
                top = round(c['top'])
                if top not in lines:
                    lines[top] = {'text': "", 'sizes': []}
                lines[top]['text'] += c['text']
                lines[top]['sizes'].append(c['size'])

            # Sort by top (y-axis), get the line with the largest font at the top
            sorted_lines = sorted(lines.items(), key=lambda x: x[0])
            title = None
            if sorted_lines:
                # Pick the first line (top of page) with significant text
                for top, data in sorted_lines:
                    if len(data['text'].strip()) > 3:
                        title = data['text'].strip()
                        break

            # Get all text
            text = page.extract_text() or ""
            chunks.append(DocumentChunk(
                content=text.strip(),
                level1=title or f"Slide {i+1}",
                level2=None,
                level3=None,
                metadata={"page_number": i + 1}
            ))

        return Document(
            id=uuid4(),
            name=Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.PDF,
            document_chunks=chunks
        )

    def _parse_book(self, pdf: pdfplumber.PDF, filename: str) -> Document:
        """Parse PDF as a book/article with heading detection."""
        chunks = []
        current_level1 = None
        current_level2 = None
        current_level3 = None

        current_content_lines = []
        current_page = 1

        def flush_chunk():
            nonlocal current_content_lines, current_level1, current_level2, current_level3, current_page
            if current_content_lines:
                content = "\n".join(current_content_lines).strip()
                if content:
                    chunks.append(DocumentChunk(
                        content=content,
                        level1=current_level1,
                        level2=current_level2,
                        level3=current_level3,
                        metadata={
                            "page_number": current_page,
                            "chapter": current_level1,
                            "article": current_level2,
                            "point": current_level3,
                        }
                    ))
                current_content_lines = []

        for i, page in enumerate(pdf.pages):
            current_page = i + 1
            structure = self._extract_page_structure(page)

            for item in structure:
                if item['is_heading'] and item['level']:
                    flush_chunk()
                    if item['level'] == 1:
                        current_level1 = item['text']
                        current_level2 = None
                        current_level3 = None
                    elif item['level'] == 2:
                        current_level2 = item['text']
                        current_level3 = None
                    else:  # level 3
                        current_level3 = item['text']
                else:
                    current_content_lines.append(item['text'])

        flush_chunk()  # Last chunk

        return Document(
            id=uuid4(),
            name=Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.PDF,
            document_chunks=chunks
        )
