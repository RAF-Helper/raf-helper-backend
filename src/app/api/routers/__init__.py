"""Re-export routers for easy import."""

from .health import router as health_router

__all__ = ["health_router"]
