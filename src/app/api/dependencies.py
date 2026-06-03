from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.services.embedding_service import EmbeddingService
from app.chat.services import services
from app.repositories.routing_repository import RoutingRepository

async def get_embedding_service() -> EmbeddingService:
    """Dependency to provide the shared embedding service."""
    return services.embedder

async def get_routing_repo(session: AsyncSession = Depends(get_session)) -> RoutingRepository:
    """Dependency to provide a RoutingRepository tied to the current request session."""
    return RoutingRepository(session)
