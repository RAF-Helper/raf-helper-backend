"""Simple recursive text chunker for RAG indexing."""

from typing import Optional


class TextChunker:
    """Splits long texts into overlapping chunks for Elasticsearch indexing.

    Strategy: recursive split on paragraph boundaries first, then sentence
    boundaries, then whitespace — keeping chunks within *max_size* characters
    with *overlap* characters of context from the previous chunk.
    """

    SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, max_size: int = 1000, overlap: int = 200):
        if overlap >= max_size:
            raise ValueError("overlap must be smaller than max_size")
        self.max_size = max_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        """Split *text* into chunks; returns a list of non-empty strings."""
        text = text.strip()
        if not text:
            return []
        raw = self._recursive_split(text, self.SEPARATORS)
        return self._merge_with_overlap(raw)

    # ------------------------------------------------------------------ #

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.max_size:
            return [text] if text.strip() else []

        sep = separators[0]
        rest = separators[1:]

        if sep == "":
            # last resort: hard cut
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
        """Merge small pieces into chunks of at most *max_size* chars,
        adding *overlap* chars from the tail of the previous chunk."""
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
