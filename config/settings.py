"""
Configuration settings for FlowRAG.
Follows the agent specification for centralized configuration management.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="FlowRAG", description="Application name")
    env: str = Field(default="development", description="Environment (development/production)")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")
    neo4j_database: str = Field(default="neo4j", description="Neo4j database name")

    # Qdrant
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_collection: str = Field(default="code_embeddings", description="Qdrant collection name")
    qdrant_vector_size: int = Field(default=1536, description="Embedding vector size")

    # Redis
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-sonnet-20240229", description="Anthropic model"
    )

    # Local SLM (Gemma 3 270M)
    slm_model_name: str = Field(
        default="google/gemma-3-270m", description="HuggingFace model name for SLM"
    )
    slm_device: str = Field(default="cpu", description="Device for SLM (cpu/cuda/mps)")
    slm_max_length: int = Field(default=512, description="Max sequence length for SLM")
    slm_temperature: float = Field(default=0.1, description="Temperature for SLM generation")
    slm_use_cache: bool = Field(default=True, description="Use model cache")

    # Ingestion
    max_chunk_size: int = Field(default=1000, description="Maximum chunk size in tokens")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    supported_languages: str = Field(
        default="python,javascript,typescript,go,rust,java",
        description="Comma-separated list of supported languages",
    )

    # Security
    secret_key: str = Field(..., description="Secret key for JWT")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration time"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")

    # Security Settings (New - Backward Compatible)
    enable_security: bool = Field(
        default=False,
        description="Enable API key authentication (disabled by default for backward compatibility)"
    )
    enable_rate_limiting: bool = Field(
        default=False,
        description="Enable rate limiting (disabled by default for backward compatibility)"
    )
    enable_path_validation: bool = Field(
        default=True,
        description="Enable path validation for file operations"
    )
    api_keys: Optional[str] = Field(
        default=None,
        description="Comma-separated list of valid API keys"
    )
    allowed_directories: Optional[str] = Field(
        default=None,
        description="Comma-separated list of allowed directories for file access"
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size in MB for ingestion"
    )
    cors_origins: Optional[str] = Field(
        default=None,
        description="Comma-separated list of allowed CORS origins for production"
    )

    @property
    def supported_languages_list(self) -> list[str]:
        """Get list of supported programming languages."""
        return [lang.strip() for lang in self.supported_languages.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
