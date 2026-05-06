"""Repository for routing intents using Elasticsearch."""

import logging
from typing import Any, Optional

from ..repositories.elasticsearch_repository import ElasticsearchRepository

logger = logging.getLogger(__name__)

class RoutingRepository:
    """Repository for managing and searching routing intents in Elasticsearch."""

    INDEX_NAME = "routing_intents"

    def __init__(self):
        self._es_repo = ElasticsearchRepository()

    async def create_index(self):
        """Create the routing intents index with appropriate mapping."""
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "route_id": {"type": "keyword"},
                    "intent_text": {"type": "text"},
                    "intent_embedding": {
                        "type": "dense_vector",
                        "dims": 1024,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        }
        # Use the underlying es_repo to create the index
        # Assuming ElasticsearchRepository has a method to create index or we use the client directly
        # Since I don't see a create_index in ElasticsearchRepository, I'll use the client.
        await self._es_repo.client.indices.create(index=self.INDEX_NAME, body=mapping, error_handling="ignore")
        logger.info(f"Routing index {self.INDEX_NAME} ensured.")

    async def add_intent(self, route_id: str, text: str, embedding: list[float]):
        """Add a single routing intent to the index."""
        doc = {
            "route_id": route_id,
            "intent_text": text,
            "intent_embedding": embedding,
        }
        await self._es_repo.client.index(index=self.INDEX_NAME, document=doc)

    async def search_intents(self, query_vector: list[float], k: int = 10) -> list[dict[str, Any]]:
        """
        Perform cosine similarity search for the most similar intents.

        Returns:
            List of hits containing route_id and score.
        """
        query = {
            "field": "intent_embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": 100,
        }

        # Use the knn search functionality of ES
        response = await self._es_repo.client.search(
            index=self.INDEX_NAME,
            knn=query,
            source=["route_id", "intent_text"],
            size=k
        )

        results = []
        for hit in response["hits"]["hits"]:
            results.append({
                "route_id": hit["_source"]["route_id"],
                "score": hit["_score"],
                "text": hit["_source"]["intent_text"]
            })

        return results
