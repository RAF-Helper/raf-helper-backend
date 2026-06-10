"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "raf-helper-backend"
    debug: bool = False
    allowed_origins: list[str] = ["*"]

    # Database - PostgreSQL
    postgres_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost/raf_db",
        alias="DATABASE_URL",
    )

    # Elasticsearch
    elasticsearch_url: str = Field(
        default="http://localhost:9200",
        alias="ELASTICSEARCH_URL",
    )
    elasticsearch_update_password: str = Field(
        default="",
        alias="ELASTICSEARCH_UPDATE_PASSWORD",
    )

    # Firebase
    firebase_credentials_path: str = Field(
        default="firebase-credentials.json",
        alias="FIREBASE_CREDENTIALS_PATH",
    )

    # OpenRouter
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemma-4-31b-it"

    # Embeddings
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="bge-m3", alias="EMBEDDING_MODEL")

    # Tavily (web search)
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # Langfuse (observability)
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = "https://cloud.langfuse.com"

    # File storage
    storage_path: str = Field(default="./storage/files", alias="STORAGE_PATH")

    # Chunking
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    slides_chunk_size: int = Field(default=500, alias="SLIDES_CHUNK_SIZE")
    slides_chunk_overlap: int = Field(default=100, alias="SLIDES_CHUNK_OVERLAP")

    # Routing
    routing_threshold: float = Field(default=0.7, alias="ROUTING_THRESHOLD")
    routing_margin: float = Field(default=0.1, alias="ROUTING_MARGIN")

    model_config = SettingsConfigDict(

        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )



settings = Settings()
