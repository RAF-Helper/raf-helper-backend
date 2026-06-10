"""Embedding service with support for multiple providers (Local, OpenRouter)."""

import asyncio
import logging
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)

# Model choices for local provider
SUPPORTED_LOCAL_MODELS = {
    "bge-m3": "BAAI/bge-m3",  # Multilingual, 1024 dims
    "bge-small": "BAAI/bge-small-en-v1.5",  # English, 384 dims
    "paraphrase-multilingual": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # 384 dims
}


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single batch."""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            hf_name = SUPPORTED_LOCAL_MODELS.get(self.model_name, self.model_name)
            logger.info(f"Loading local sentence-transformers model: {hf_name}")
            self._model = SentenceTransformer(hf_name)
            logger.info("Local model loaded successfully")
        return self._model

    async def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Cannot embed empty text")

        try:
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(
                None, lambda: self.model.encode(text, convert_to_numpy=False)
            )
            if hasattr(embedding, "tolist"):
                embedding = embedding.tolist()
            return list(embedding)
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        valid_texts = [t for t in texts if t.strip()]
        if not valid_texts:
            return []

        try:
            loop = asyncio.get_running_loop()
            embeddings = await loop.run_in_executor(
                None, lambda: self.model.encode(valid_texts, convert_to_numpy=False)
            )
            results = []
            for emb in embeddings:
                if hasattr(emb, "tolist"):
                    results.append(emb.tolist())
                else:
                    results.append(list(emb))
            return results
        except Exception as e:
            logger.error(f"Local batch embedding failed: {e}")
            raise


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using OpenRouter API."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self.api_key = settings.openrouter_api_key
        self.base_url = f"{settings.openrouter_base_url}/embeddings"

    async def embed_text(self, text: str) -> list[float]:
        return (await self.embed_batch([text]))[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "input": texts,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # OpenRouter typically follows OpenAI embeddings format:
                # { "data": [ { "embedding": [...], ... }, ... ] }
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings
        except Exception as e:
            logger.error(f"OpenRouter embedding failed: {e}")
            raise


class EmbeddingService:
    """Coordinator for embedding providers."""

    def __init__(self):
        provider_type = settings.embedding_provider.lower()
        model_name = settings.embedding_model

        if provider_type == "openrouter":
            self.provider = OpenRouterEmbeddingProvider(model_name)
            logger.info(f"EmbeddingService initialized with OpenRouter provider (model={model_name})")
        elif provider_type == "local":
            self.provider = LocalEmbeddingProvider(model_name)
            logger.info(f"EmbeddingService initialized with Local provider (model={model_name})")
        else:
            logger.warning(f"Unknown embedding provider '{provider_type}', falling back to local")
            self.provider = LocalEmbeddingProvider(model_name)

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        return await self.provider.embed_text(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single batch."""
        return await self.provider.embed_batch(texts)


@lru_cache()
def get_embedding_service() -> "EmbeddingService":
    """Get or create the global embedding service instance."""
    return EmbeddingService()
