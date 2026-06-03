"""Repository for routing intents using PostgreSQL pgvector."""

import logging
from typing import Any, Optional
from sqlalchemy import select, insert, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Route, Intent
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
        # We use the SQLAlchemy expression API instead of raw text to avoid placeholder conflicts.
        # pgvector.sqlalchemy's cosine_distance handles the operator correctly.
        # To ensure the cast to vector.vector happens correctly in Supabase:

        stmt = (
            select(
                Intent.route_id,
                Intent.text,
                (1 - Intent.text_embedding.cosine_distance(query_vector)).label("score")
            )
            .order_by(Intent.text_embedding.cosine_distance(query_vector))
            .limit(k)
        )

        try:
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
        except Exception as e:
            logger.error(f"Error searching intents: {e}")
            # If the above fails, we can try a raw query with a different casting method
            # as a fallback, but the SQLAlchemy expression is the correct way.
            raise
