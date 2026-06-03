"""Repository for routing intents using PostgreSQL pgvector."""

import logging
from typing import Any
from sqlalchemy import select, cast
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Intent
from pgvector.sqlalchemy import Vector

logger = logging.getLogger(__name__)

class RoutingRepository:
    """Repository for managing and searching routing intents in PostgreSQL using pgvector."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_intent(self, route_id: int, text: str, embedding: list[float]):
        """Add a single routing intent to the database."""
        new_intent = Intent(
            route_id=route_id,
            text=text,
            text_embedding=embedding
        )
        self._session.add(new_intent)
        await self._session.commit()

    async def search_intents(self, query_vector: list[float], k: int = 10) -> list[dict[str, Any]]:
        """
        Perform cosine similarity search for the most similar intents.
        Returns a list of dicts with route_id, score, and text.
        """
        # Explicitly cast the query_vector to the Vector type to avoid 'operator does not exist' error
        stmt = (
            select(
                Intent.route_id,
                Intent.text,
                (1 - Intent.text_embedding.cosine_distance(cast(query_vector, Vector(1024)))).label("score")
            )
            .order_by(Intent.text_embedding.cosine_distance(cast(query_vector, Vector(1024))))
            .limit(k)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return [
            {
                "route_id": row.route_id,
                "score": row.score,
                "text": row.text
            }
            for row in rows
        ]
