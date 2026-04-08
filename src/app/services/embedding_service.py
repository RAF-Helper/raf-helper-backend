"""Embedding service using sentence-transformers (local ML model)."""

import asyncio
import logging
from typing import Optional
from functools import lru_cache

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Model choices
SUPPORTED_MODELS = {
    "bge-m3": "BAAI/bge-m3",  # Multilingual, 1024 dims
    "bge-small": "BAAI/bge-small-en-v1.5",  # English, 384 dims (but we need multilingual)
    "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 384 dims
}

DEFAULT_MODEL = "bge-m3"


# Global singleton instance (lazy-loaded)
@lru_cache()
def get_embedding_service() -> "EmbeddingService":
    """Get or create the global embedding service instance."""
    return EmbeddingService()


class EmbeddingService:
    """Generates embeddings for text using sentence-transformers.

    This is a local embedding service - models are loaded into memory and run on CPU.
    No external API calls are made.

    Note: sentence-transformers is synchronous and CPU-bound. We run it in a
    thread pool to avoid blocking the event loop in async contexts.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize the embedding service with a sentence-transformers model.

        Args:
            model_name: Model identifier. Options:
                - "bge-m3" (default) - BAAI/bge-m3, multilingual, 1024 dims
                - "paraphrase-multilingual" - 384 dims, smaller/faster

        Note: The model will be downloaded on first use (~1.4GB for bge-m3).
        """
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        logger.info(f"EmbeddingService initialized with model={model_name} (lazy-loaded)")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the model on first use."""
        if self._model is None:
            hf_name = SUPPORTED_MODELS.get(self.model_name, self.model_name)
            logger.info(f"Loading sentence-transformers model: {hf_name}")
            self._model = SentenceTransformer(hf_name)
            logger.info(f"Model loaded successfully")
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Input text to embed (should be in Russian or multilingual content)

        Returns:
            Vector embedding as list of floats (1024 dims for bge-m3)
        """
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            # Run synchronous encode in thread pool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(
                None, lambda: self.model.encode(text, convert_to_numpy=False)
            )
            # Convert from numpy to list if needed
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            logger.debug(f"Generated embedding for text length={len(text)}")
            return list(embedding)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in a single batch.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors, one per input text
        """
        if not texts:
            return []

        # Filter out empty texts while preserving order
        valid_texts = [t for t in texts if t.strip()]
        if not valid_texts:
            return []

        try:
            # Run batch encoding in thread pool
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: self.model.encode(valid_texts, convert_to_numpy=False)
            )
            # Convert from numpy arrays to lists
            results = []
            for emb in embeddings:
                if hasattr(emb, "tolist"):
                    results.append(emb.tolist())
                else:
                    results.append(list(emb))
            logger.debug(f"Generated {len(results)} embeddings (batch)")
            return results
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
