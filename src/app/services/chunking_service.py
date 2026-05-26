"""Service for splitting documents into overlapping chunks with structural awareness."""

from typing import Optional
from uuid import uuid4
from ..config import settings
from ..schemas.document import Document, DocumentChunk, DocumentFormat

class TextChunker:
    """Internal recursive text chunker logic."""

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, max_size: int, overlap: int):
        if overlap >= max_size:
            raise ValueError("overlap must be smaller than max_size")
        self.max_size = max_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        raw = self._recursive_split(text, self.SEPARATORS)
        return self._merge_with_overlap(raw)

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.max_size:
            return [text] if text.strip() else []

        sep = separators[0]
        rest = separators[1:]

        if sep == "":
            chunks = []
            for i in range(0, len(text), self.max_size):
                chunks.append(text[i : i + self.max_size])
            return chunks

        parts = text.split(sep)
        result: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= self.max_size:
                result.append(part)
            else:
                result.extend(self._recursive_split(part, rest))
        return result

    def _merge_with_overlap(self, pieces: list[str]) -> list[str]:
        if not pieces:
            return []

        chunks: list[str] = []
        current = pieces[0]

        for piece in pieces[1:]:
            candidate = current + " " + piece
            if len(candidate) <= self.max_size:
                current = candidate
            else:
                chunks.append(current)
                tail = current[-self.overlap :] if self.overlap else ""
                current = (tail + " " + piece).strip() if tail else piece

        if current:
            chunks.append(current)

        return chunks


class ChunkingService:
    """Orchestrates document chunking respecting structural metadata."""

    def __init__(self):
        # Config parameters are fetched per-document in the chunk method
        pass

    def chunk(self, document: Document) -> Document:
        """
        Processes a Document and returns a new Document with refined chunks.
        """
        # 1. Determine config parameters
        if document.format == DocumentFormat.PPTX: # Simplified check for slides
            max_size = settings.slides_chunk_size
            overlap = settings.slides_chunk_overlap
        else:
            max_size = settings.chunk_size
            overlap = settings.chunk_overlap

        chunker = TextChunker(max_size=max_size, overlap=overlap)
        final_chunks: list[DocumentChunk] = []

        # 2. Process initial structural blocks
        for block in document.document_chunks:
            if len(block.content) <= max_size:
                final_chunks.append(block)
                continue

            # Split the block into smaller chunks using the recursive chunker
            sub_texts = chunker.split(block.content)

            for i, text in enumerate(sub_texts):
                # Maintain structural levels and metadata
                # For page numbers, we typically assume the block starts on a certain page.
                # If the parser provided a page number in metadata, we keep it for the first chunk.
                page = block.metadata.get("page_number", 1)

                final_chunks.append(DocumentChunk(
                    content=text,
                    level1=block.level1,
                    level2=block.level2,
                    level3=block.level3,
                    metadata={**block.metadata, "page_number": page}
                ))

        # Update the document with the refined chunks
        document.document_chunks = final_chunks
        return document
