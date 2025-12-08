"""
Qdrant data loader for vector embeddings.

Loads code units and documents into Qdrant vector database.
Supports semantic enrichment for improved retrieval.
Ingestion Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional, Union
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

        # Ensure collection exists
        try:
            self.client.get_collection_info()
        except Exception:
            logger.info("Collection doesn't exist, creating it...")
            self.client.create_collection()

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

        # Return with vectors_stored key for API compatibility
        return {"vectors_stored": result.get("upserted_count", 0)}

    def load_enriched_code_units(
        self,
        enriched_units: List[Any],  # List[EnrichedCodeUnit]
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Load semantically enriched code units into Qdrant.

        Uses the enriched embedding_text for generating embeddings,
        which includes natural language summaries for better semantic matching.

        Args:
            enriched_units: List of EnrichedCodeUnit objects
            namespace: Namespace

        Returns:
            Load statistics
        """
        if not enriched_units:
            return {"vectors_stored": 0}

        # Use the enriched embedding_text for generating embeddings
        texts = [unit.embedding_text for unit in enriched_units]

        # Generate embeddings from enriched text
        logger.info(f"Generating embeddings for {len(texts)} enriched code units...")
        embeddings = self.embedding_service.generate_embeddings(texts)

        # Prepare vectors for upsert with enriched metadata
        vectors = []
        for unit, embedding in zip(enriched_units, embeddings):
            vectors.append({
                "id": unit.id,
                "vector": embedding,
                "metadata": {
                    "type": "code",
                    "code_unit_type": unit.code_unit_type,
                    "name": unit.name,
                    "file_path": unit.file_path,
                    "language": unit.language,
                    "line_start": unit.line_start,
                    "line_end": unit.line_end,
                    "signature": unit.signature,
                    "docstring": unit.docstring,
                    "full_code": unit.code,
                    # Enrichment fields
                    "semantic_summary": unit.semantic_summary,
                    "purpose": unit.purpose,
                    "domain_concepts": unit.domain_concepts,
                    "related_features": unit.related_features,
                    "is_enriched": True,
                },
            })

        # Upsert to Qdrant
        result = self.client.upsert_vectors(vectors, namespace)

        logger.info(f"Loaded {result['upserted_count']} enriched code unit embeddings")

        return {
            "vectors_stored": result.get("upserted_count", 0),
            "enriched": True,
        }

    def load_service_documentation(
        self,
        service_doc: Any,  # ServiceDocumentation
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Load service-level documentation into Qdrant.

        Creates a high-level documentation vector that helps answer
        questions like "What does this service do?"

        Args:
            service_doc: ServiceDocumentation object
            namespace: Namespace

        Returns:
            Load statistics
        """
        import hashlib

        # Generate embedding from full documentation
        doc_embedding = self.embedding_service.generate_embeddings(
            [service_doc.full_documentation]
        )[0]

        # Generate unique ID for service documentation
        doc_id = f"{namespace}_service_doc"
        doc_hash = hashlib.md5(doc_id.encode()).hexdigest()[:16]

        # Prepare vector with comprehensive metadata
        doc_vector = {
            "id": doc_hash,
            "vector": doc_embedding,
            "metadata": {
                "type": "service_documentation",
                "namespace": namespace,
                "service_name": service_doc.service_name,
                "description": service_doc.description,
                "purpose": service_doc.purpose,
                "key_features": service_doc.key_features,
                "main_components": service_doc.main_components,
                "external_dependencies": service_doc.external_dependencies,
                "api_patterns": service_doc.api_patterns,
                "full_documentation": service_doc.full_documentation,
                "is_service_documentation": True,
                "original_id": doc_id,
            },
        }

        # Upsert to Qdrant
        result = self.client.upsert_vectors([doc_vector], namespace)

        logger.info(f"Loaded service documentation for {namespace}")

        return {
            "vectors_stored": result.get("upserted_count", 0),
            "service_documentation": True,
        }

    def load_glossary_terms(
        self,
        terms: List[Any],  # List[GlossaryTerm]
        namespace: str,
    ) -> Dict[str, Any]:
        """
        Load glossary terms into Qdrant.

        Glossary terms help with domain-specific queries and acronym expansion.

        Args:
            terms: List of GlossaryTerm objects
            namespace: Namespace

        Returns:
            Load statistics
        """
        if not terms:
            return {"vectors_stored": 0}

        import hashlib

        vectors = []
        for term in terms:
            # Build embedding text for the term
            parts = [f"Term: {term.term}"]
            if term.full_name:
                parts.append(f"Full name: {term.full_name}")
            parts.append(f"Description: {term.description}")
            if term.usage_context:
                parts.append(f"Context: {term.usage_context}")

            term_text = "\n".join(parts)

            # Generate embedding
            term_embedding = self.embedding_service.generate_embeddings([term_text])[0]

            # Generate ID
            term_id = f"{namespace}_glossary_{term.term}"
            term_hash = hashlib.md5(term_id.encode()).hexdigest()[:16]

            vectors.append({
                "id": term_hash,
                "vector": term_embedding,
                "metadata": {
                    "type": "glossary",
                    "term": term.term,
                    "full_name": term.full_name,
                    "description": term.description,
                    "related_services": term.related_services,
                    "usage_context": term.usage_context,
                    "namespace": namespace,
                    "is_glossary": True,
                    "original_id": term_id,
                },
            })

        # Upsert to Qdrant
        result = self.client.upsert_vectors(vectors, namespace)

        logger.info(f"Loaded {len(terms)} glossary terms for {namespace}")

        return {
            "vectors_stored": result.get("upserted_count", 0),
            "glossary_terms": len(terms),
        }

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
            # Generate a hash ID from the chunk ID for Qdrant UUID format
            import hashlib
            chunk_hash = hashlib.md5(chunk.id.encode()).hexdigest()[:16]

            vectors.append({
                "id": chunk_hash,
                "vector": embedding,
                "metadata": {
                    "type": "document",
                    "file_path": chunk.file_path,
                    "chunk_index": chunk.chunk_index,
                    "total_chunks": chunk.total_chunks,
                    "section_title": chunk.section_title,
                    "word_count": chunk.word_count,
                    "content": chunk.content,  # Store full content
                    "original_id": chunk.id,  # Store original ID for reference
                },
            })

        # Upsert to Qdrant
        result = self.client.upsert_vectors(vectors, namespace)

        logger.info(f"Loaded {result['upserted_count']} document chunk embeddings")

        # Return with vectors_stored key for API compatibility
        return {"vectors_stored": result.get("upserted_count", 0)}

    def enrich_with_documentation(
        self,
        namespace: str,
        documentation_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich existing vectors with documentation metadata.

        This adds service-level documentation context to all vectors in a namespace,
        improving retrieval relevance by providing high-level context.

        Args:
            namespace: Namespace to enrich
            documentation_metadata: Documentation metadata to add
                - service_name: Name of the service
                - description: Service description
                - architecture_summary: Architecture overview
                - responsibilities: List of service responsibilities

        Returns:
            Update statistics
        """
        try:
            # Get all vectors for this namespace
            # Note: This is a conceptual implementation - actual implementation
            # depends on Qdrant client's scroll/search capabilities

            # For now, we'll store the documentation as a special vector
            # that can be retrieved during semantic search
            doc_text_parts = []

            if documentation_metadata.get("service_name"):
                doc_text_parts.append(f"Service: {documentation_metadata['service_name']}")

            if documentation_metadata.get("description"):
                doc_text_parts.append(f"Description: {documentation_metadata['description']}")

            if documentation_metadata.get("architecture_summary"):
                doc_text_parts.append(f"Architecture: {documentation_metadata['architecture_summary']}")

            if documentation_metadata.get("responsibilities"):
                responsibilities = documentation_metadata["responsibilities"]
                if isinstance(responsibilities, list):
                    doc_text_parts.append(f"Responsibilities: {', '.join(responsibilities[:5])}")

            doc_text = "\n".join(doc_text_parts)

            # Generate embedding for documentation
            doc_embedding = self.embedding_service.generate_embeddings([doc_text])[0]

            # Generate hash ID for the documentation summary vector
            import hashlib
            doc_id = f"{namespace}_documentation"
            doc_hash = hashlib.md5(doc_id.encode()).hexdigest()[:16]

            # Store as special documentation vector
            doc_vector = {
                "id": doc_hash,
                "vector": doc_embedding,
                "metadata": {
                    "type": "documentation",
                    "namespace": namespace,
                    "service_name": documentation_metadata.get("service_name", ""),
                    "description": documentation_metadata.get("description", ""),
                    "architecture_summary": documentation_metadata.get("architecture_summary", ""),
                    "responsibilities": documentation_metadata.get("responsibilities", []),
                    "full_text": doc_text,
                    "is_service_documentation": True,
                    "original_id": doc_id,  # Store original ID for reference
                },
            }

            # Upsert documentation vector
            result = self.client.upsert_vectors([doc_vector], namespace)

            logger.info(f"Enriched namespace {namespace} with documentation metadata")

            return {
                "enriched": True,
                "documentation_vector_stored": result.get("upserted_count", 0) > 0
            }

        except Exception as e:
            logger.error(f"Failed to enrich namespace with documentation: {e}")
            return {"enriched": False, "error": str(e)}

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
