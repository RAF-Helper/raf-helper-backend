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

    # Firebase
    firebase_credentials_path: str = Field(
        default="firebase-credentials.json",
        alias="FIREBASE_CREDENTIALS_PATH",
    )

    # OpenRouter
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-oss-20b:free"

    # Tavily (web search)
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    # Langfuse (observability)
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = "https://cloud.langfuse.com"

    # File storage
    storage_path: str = Field(default="./storage", alias="STORAGE_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )



settings = Settings()
