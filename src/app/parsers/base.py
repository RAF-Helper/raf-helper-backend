"""Abstract base parser class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar, Generic

from ..schemas.document import Document

T = TypeVar("T")

class BaseParser(ABC, Generic[T]):
    """Base parser interface for document parsing."""

    @abstractmethod
    def load(self, filename: str) -> T:
        """
        Load the file and extract the artifact required for parsing.

        Args:
            filename: Path to the file to load.

        Returns:
            The artifact (e.g., a library-specific document object) used for parsing.
        """
        pass

    @abstractmethod
    def parse(self, artifact: T, filename: str) -> Document:
        """
        Parse the artifact into a Document model.

        Args:
            artifact: The artifact produced by the load method.
            filename: The name of the file being parsed.

        Returns:
            A parsed Document object containing chunks and metadata.
        """
        pass
