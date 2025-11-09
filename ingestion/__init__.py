"""Ingestion module for FlowRAG."""

from .parsers.base import get_parser, detect_language, CodeUnit, ParseResult
from .chunkers.document_chunker import DocumentChunker, DocumentChunk
from .embeddings import get_embedding_service
from .loaders.neo4j_loader import get_neo4j_loader
from .loaders.qdrant_loader import get_qdrant_loader

__all__ = [
    "get_parser",
    "detect_language",
    "CodeUnit",
    "ParseResult",
    "DocumentChunker",
    "DocumentChunk",
    "get_embedding_service",
    "get_neo4j_loader",
    "get_qdrant_loader",
]
