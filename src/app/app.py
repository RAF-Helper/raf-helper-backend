"""FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db, close_db
from app.elastic.client import ElasticsearchClient
from app.elastic.index_manager import ensure_indexes
from app.logging_config import setup_logging

# Routers
from app.api.routers.health import router as health_router
from app.api.routers.auth import router as auth_router
from app.api.routers.files import router as files_router
from app.api.routers.chats import router as chats_router
from app.api.routers.admin.staff import router as admin_staff_router
from app.api.routers.admin.events import router as admin_events_router
from app.api.routers.admin.elastic import router as admin_elastic_router
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(
        log_level="DEBUG",#settings.debug and "DEBUG" or "INFO",
        enable_console=settings.debug,
    )
    logging.info(f"Starting {settings.app_name} v{app.version}")
    logging.info(f"Debug mode: {settings.debug}")

    await init_db()
    es = ElasticsearchClient.get()
    await ensure_indexes(es)
    yield
    # Shutdown
    await close_db()
    await ElasticsearchClient.close()
    logging.info("Application shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(files_router)
app.include_router(chats_router)
app.include_router(admin_staff_router)
app.include_router(admin_events_router)
app.include_router(admin_elastic_router)
