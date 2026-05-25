"""Database session module."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from alembic.config import Config
from alembic import command
from uuid import uuid4
import logging

from .models import Base
from ..config import settings

# SQLAlchemy async engine
engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    poolclass=NullPool if settings.debug else None,
    pool_recycle=300,
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        "statement_cache_size": 0 # temp work around for asyncpg+pgbouncer
    },
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        config = Config()
        script_location = './alembic'
        config.set_main_option('script_location', script_location)
        config.set_main_option('sqlalchemy.url', settings.postgres_url)
        logging.info('Running DB migrations in %r on %r', script_location, settings.postgres_url)
        command.upgrade(config, 'head', sql=True)
        logging.info('DB migrations ran successfully')


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
