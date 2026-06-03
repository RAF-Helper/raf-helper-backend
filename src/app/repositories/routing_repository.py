"""Repository for routing intents using PostgreSQL pgvector."""

import logging
from typing import Any, Optional
from sqlalchemy import select, insert, text, bindparam
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
        try:
            # Ensure search_path includes 'vector' schema for operators
            await self._session.execute(text("SET search_path TO public, vector"))

            # We use a raw SQL query but use bindparam to explicitly define the type as Vector.
            # This prevents the 'operator does not exist' and 'syntax error' issues
            # because asyncpg will now correctly encode the list as a pgvector type.
            query = text("""
                SELECT route_id, text, 1 - (text_embedding <=> :vector) as score
                FROM vector.intents
                ORDER BY text_embedding <=> :vector
                LIMIT :k
            """).bindparams(bindparam("vector", type_=Vector(1024)))

            result = await self._session.execute(query, {
                "vector": query_vector,
                "k": k
            })
            rows = result.all()

            return [
                {
                    "route_id": row[0],
                    "score": row[2],
                    "text": row[1]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error searching intents: {e}")
            raise
