"""
Embedding generation service using OpenAI.

Ingestion Agent is responsible for this module.
"""

from typing import List, Optional
import logging

from openai import OpenAI

from config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (default from settings)
            model: Embedding model name (default from settings)
        """
        settings = get_settings()

        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_embedding_model

        self.client = OpenAI(api_key=self.api_key)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
            )

            # Sort by index to maintain order
            embeddings = sorted(response.data, key=lambda x: x.index)

            return [emb.embedding for emb in embeddings]

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
