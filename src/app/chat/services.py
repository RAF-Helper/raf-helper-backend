import logging
from app.pii.presidio_masker import PIIMasker
from app.chat.llm import OpenRouterClient
from app.services.embedding_service import get_embedding_service
from app.repositories.routing_repository import RoutingRepository

logger = logging.getLogger(__name__)

class ChatServices:
    """Shared services container to avoid repeated instantiation in graph nodes."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatServices, cls).__new__(cls)
            logger.info("Initializing shared chat services...")
            cls._instance.llm = OpenRouterClient()
            cls._instance.pii = PIIMasker()
            cls._instance.embedder = get_embedding_service()
        return cls._instance

# Singleton instance
services = ChatServices()
