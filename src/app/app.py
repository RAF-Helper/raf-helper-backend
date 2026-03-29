"""FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.session import init_db, close_db
from .elastic.client import ElasticsearchClient
from .elastic.index_manager import ensure_indexes

# Routers
from .api.routers import health
from .api.routers.auth import router as auth_router
from .api.routers.chat import router as chat_router
from .api.routers.files import router as files_router
from .api.routers.chats import router as chats_router
from .api.routers.admin.staff import router as admin_staff_router
from .api.routers.admin.events import router as admin_events_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    es = ElasticsearchClient.get()
    await ensure_indexes(es)
    yield
    # Shutdown
    await close_db()
    await ElasticsearchClient.close()


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

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(files_router)
app.include_router(chats_router)
app.include_router(admin_staff_router)
app.include_router(admin_events_router)
