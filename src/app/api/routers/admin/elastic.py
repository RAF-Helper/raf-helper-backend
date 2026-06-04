"""Admin endpoints for Elasticsearch configuration management."""

import logging
from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field

from app.elastic.index_manager import ensure_indexes

from app.config import settings
from app.elastic.client import ElasticsearchClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/elastic", tags=["admin", "elastic"])


class ElasticsearchUpdateRequest(BaseModel):
    """Request to update Elasticsearch connection URL."""
    url: str = Field(..., description="New Elasticsearch URL (e.g., https://localhost:9200)")


def verify_admin_token(x_admin_token: str = Header(..., alias="X-Admin-Token")) -> str:
    """
    Verify the admin token from header.

    Raises HTTPException 401 if token is invalid.
    """
    expected_token = settings.elasticsearch_update_password
    if not expected_token:
        logger.error("ELASTICSEARCH_UPDATE_PASSWORD environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin token not configured on server"
        )

    if x_admin_token != expected_token:
        logger.warning(f"Invalid admin token attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token"
        )

    return x_admin_token


@router.post("/update-url")
async def update_elasticsearch_url(
    body: ElasticsearchUpdateRequest,
    admin_token: str = Depends(verify_admin_token),
):
    """
    Update the Elasticsearch connection URL and reconnect.

    This endpoint updates the application-wide Elasticsearch URL setting
    and reinitializes the client connection.

    **Authentication required:** Include `X-Admin-Token` header with the
    token configured in `ELASTICSEARCH_UPDATE_PASSWORD` environment variable.
    The same token must also be provided in the request body as `password`.

    Args:
        body: Request with new URL and password

    Returns:
        Confirmation message with old and new URLs
    """
    old_url = settings.elasticsearch_url
    old_client = ElasticsearchClient._instance

    # Close existing client if it exists
    if old_client is not None:
        try:
            await old_client.close()
            logger.info(f"Closed existing Elasticsearch connection to {old_url}")
        except Exception as e:
            logger.error(f"Error closing Elasticsearch client: {e}")

    # Update settings
    settings.elasticsearch_url = body.url

    # Recreate client with new URL (no auth for simplicity - can be added if needed)
    try:
        new_client = AsyncElasticsearch(
            hosts=[body.url],
            request_timeout=120,
            retry_on_timeout=True,
        )
        ElasticsearchClient._instance = new_client

        # Test connection
        await new_client.ping()

        logger.info(
            f"Updated Elasticsearch URL from {old_url} to {body.url}"
        )

        await ensure_indexes(new_client)

        return {
            "message": "Elasticsearch URL updated successfully",
            "old_url": old_url,
            "new_url": body.url,
            "connected": True,
        }

    except Exception as e:
        # If connection fails, restore old client
        logger.error(f"Failed to connect to new Elasticsearch URL {body.url}: {e}")
        ElasticsearchClient._instance = old_client

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to new Elasticsearch URL: {str(e)}"
        )


@router.get("/status")
async def get_elasticsearch_status():
    """
    Get current Elasticsearch connection status and configuration.

    **Authentication required:** Include `X-Admin-Token` header.
    """
    client = ElasticsearchClient.get()

    try:
        # Get cluster info
        info = await client.info()
        ping = await client.ping()

        # Get index information
        indices = await client.indices.get_alias()
        index_names = list(indices.keys())

        return {
            "url": settings.elasticsearch_url,
            "connected": True,
            "cluster_name": info.get("cluster_name"),
            "cluster_uuid": info.get("cluster_uuid"),
            "version": info.get("version", {}).get("number"),
            "ping": ping,
            "indices_count": len(index_names),
            "indices": index_names,
        }
    except Exception as e:
        logger.error(f"Error getting Elasticsearch status: {e}")
        return {
            "url": settings.elasticsearch_url,
            "connected": False,
            "error": str(e),
        }
