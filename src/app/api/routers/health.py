"""Health check and utility endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_session
from ...elastic.client import ElasticsearchClient

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Readiness check that verifies database and Elasticsearch connectivity.

    Returns:
        Dictionary with status of each service
    """
    status = {"status": "ready"}

    # Check PostgreSQL
    try:
        await session.execute(text("SELECT 1"))
        status["database"] = "connected"
    except Exception as e:
        status["database"] = "disconnected"
        status["error"] = str(e)
        status["status"] = "not ready"

    # Check Elasticsearch
    try:
        es = ElasticsearchClient.get()
        if await es.ping():
            status["elasticsearch"] = "connected"
        else:
            status["elasticsearch"] = "disconnected"
            status["status"] = "not ready"
    except Exception as e:
        status["elasticsearch"] = "disconnected"
        if "error" not in status:
            status["error"] = str(e)
        status["status"] = "not ready"

    return status
