"""Elasticsearch client singleton."""

from elasticsearch import AsyncElasticsearch

from ..config import settings


class ElasticsearchClient:
    """Singleton wrapper for AsyncElasticsearch client."""

    _instance: AsyncElasticsearch | None = None

    @classmethod
    def get(cls) -> AsyncElasticsearch:
        """Get or create Elasticsearch client instance."""
        if cls._instance is None:
            cls._instance = AsyncElasticsearch(
                hosts=[settings.elasticsearch_url],
                # Add authentication if needed
                # basic_auth=("username", "password") if settings.elasticsearch_username else None,
            )
        return cls._instance

    @classmethod
    async def close(cls):
        """Close the client connection."""
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None


async def get_elasticsearch_client() -> AsyncElasticsearch:
    """FastAPI dependency to get Elasticsearch client."""
    return ElasticsearchClient.get()
