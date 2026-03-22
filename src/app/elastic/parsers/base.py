"""Abstract base parser class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseParser(ABC):
    """Base parser interface for document parsing."""

    @abstractmethod
    def parse_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Parse a document from file path.

        Args:
            file_path: Path to the document file

        Returns:
            Dictionary with parsed content and metadata
                - "text": str (main text content)
                - "metadata": dict (additional metadata)
        """
        pass

    @abstractmethod
    def parse_bytes(self, data: bytes, filename: str | None = None) -> dict[str, Any]:
        """
        Parse a document from binary data.

        Args:
            data: Raw file bytes
            filename: Optional filename for metadata

        Returns:
            Dictionary with parsed content and metadata
        """
        pass
