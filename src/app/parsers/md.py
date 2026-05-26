"""Markdown parser using heading syntax."""

import re
from pathlib import Path
from uuid import uuid4

from .base import BaseParser
from ..schemas.document import Document, DocumentChunk, DocumentFormat

# Regex to detect markdown headings: # H1, ## H2, ### H3
RE_MD_HEADING = re.compile(r'^(#{1,3})\s+(.*)')

class MdParser(BaseParser[str]):
    """Parser for Markdown documents using heading syntax."""

    def load(self, filename: str) -> str:
        """Load markdown file content as a string."""
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def parse(self, artifact: str, filename: str) -> Document:
        """Parse Markdown into a Document model using headings for structure."""
        lines = artifact.split('\n')
        chunks = []

        current_level1 = None
        current_level2 = None
        current_level3 = None
        current_content_lines = []

        def flush_chunk():
            nonlocal current_content_lines
            if current_content_lines:
                content = "\n".join(current_content_lines).strip()
                if content:
                    chunks.append(DocumentChunk(
                        content=content,
                        level1=current_level1,
                        level2=current_level2,
                        level3=current_level3,
                        metadata={
                            "page_number": 1,  # Not applicable for MD
                            "chapter": current_level1,
                            "article": current_level2,
                            "point": current_level3,
                        }
                    ))
                current_content_lines = []

        for line in lines:
            heading_match = RE_MD_HEADING.match(line)
            if heading_match:
                # Save previous chunk
                flush_chunk()

                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                if level == 1:
                    current_level1 = title
                    current_level2 = None
                    current_level3 = None
                elif level == 2:
                    current_level2 = title
                    current_level3 = None
                elif level == 3:
                    current_level3 = title
            else:
                current_content_lines.append(line)

        # Flush the last chunk
        flush_chunk()

        return Document(
            id=uuid4(),
            name=Path(filename).stem,
            filename=Path(filename).name,
            format=DocumentFormat.MD,
            document_chunks=chunks
        )
