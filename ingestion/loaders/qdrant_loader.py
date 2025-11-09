"""
Qdrant data loader for vector embeddings.

Loads code units and documents into Qdrant vector database.
Ingestion Agent is responsible for this module.
"""

from typing import List, Dict, Any
import logging

from databases import get_qdrant_client
from ingestion.parsers.base import CodeUnit
from ingestion.chunkers.document_chunker import DocumentChunk
from ingestion.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class QdrantLoader:
    """Loader for ingesting embeddings into Qdrant."""

    def __init__(self):
        """Initialize Qdrant loader."""
        self.client = get_qdrant_client()
        self.embedding_service = get_embedding_service()

    def load_code_units(
        self,
        code_units: List[CodeUnit],
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Load code units into Qdrant.

        Args:
            code_units: List of code units to load
            namespace: Namespace

        Returns:
            Load statistics
        """
        if not code_units:
            return {"upserted_count": 0}

        # Prepare texts for embedding
        texts = []
        for unit in code_units:
            # Combine signature, docstring, and code for embedding
            parts = []

            if unit.signature:
                parts.append(unit.signature)

            if unit.docstring:
                parts.append(unit.docstring)

            parts.append(unit.code[:500])  # First 500 chars of code

            texts.append("\n".join(parts))

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} code units...")
        embeddings = self.embedding_service.generate_embeddings(texts)

        # Prepare vectors for upsert
        vectors = []
        for unit, embedding in zip(code_units, embeddings):
            vectors.append({
                "id": unit.id,
                "vector": embedding,
                "metadata": {
                    "type": "code",
                    "code_unit_type": unit.type.value,
                    "name": unit.name,
                    "file_path": unit.file_path,
                    "language": unit.language,
                    "line_start": unit.line_start,
                    "line_end": unit.line_end,
                    "signature": unit.signature,
                    "docstring": unit.docstring,
                    "full_code": unit.code,
                },
            })

        # Upsert to Qdrant
        result = self.client.upsert_vectors(vectors, namespace)

        logger.info(f"Loaded {result['upserted_count']} code unit embeddings")

        return result

    def load_document_chunks(
        self,
        chunks: List[DocumentChunk],
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Load document chunks into Qdrant.

        Args:
            chunks: List of document chunks
            namespace: Namespace

        Returns:
            Load statistics
        """
        if not chunks:
            return {"upserted_count": 0}

        # Extract texts
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} document chunks...")
        embeddings = self.embedding_service.generate_embeddings(texts)

        # Prepare vectors
        vectors = []
        for chunk, embedding in zip(chunks, embeddings):
            vectors.append({
                "id": chunk.id,
                "vector": embedding,
                "metadata": {
                    "type": "document",
                    "file_path": chunk.file_path,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "section_title": chunk.section_title,
                    "word_count": chunk.word_count,
                    "content": chunk.content,  # Store full content
                },
            })

        # Upsert to Qdrant
        result = self.client.upsert_vectors(vectors, namespace)

        logger.info(f"Loaded {result['upserted_count']} document chunk embeddings")

        return result

    def delete_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Delete all vectors for a namespace.

        Args:
            namespace: Namespace to delete

        Returns:
            Deletion stats
        """
        return self.client.delete_by_namespace(namespace)


def get_qdrant_loader() -> QdrantLoader:
    """Get Qdrant loader instance."""
    return QdrantLoader()
