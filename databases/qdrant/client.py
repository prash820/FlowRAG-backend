"""
Qdrant Client Wrapper for FlowRAG.

Provides vector search capabilities with namespace filtering.
Database Agent is responsible for this module.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid

from qdrant_client import QdrantClient as QdrantClientBase
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

from config import get_settings

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Qdrant vector database client.

    Features:
    - Collection management
    - Vector upsert and search
    - Namespace-based filtering
    - Batch operations
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant host (default from settings)
            port: Qdrant port (default from settings)
            collection_name: Collection name (default from settings)
        """
        settings = get_settings()

        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = settings.qdrant_vector_size

        self.client: Optional[QdrantClientBase] = None

    def connect(self) -> None:
        """Establish connection to Qdrant."""
        try:
            self.client = QdrantClientBase(
                host=self.host,
                port=self.port,
                timeout=60,
            )
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def create_collection(
        self,
        collection_name: Optional[str] = None,
        vector_size: Optional[int] = None,
        distance: Distance = Distance.COSINE,
    ) -> None:
        """
        Create a vector collection.

        Args:
            collection_name: Collection name (default: self.collection_name)
            vector_size: Vector dimension (default: self.vector_size)
            distance: Distance metric
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name
        size = vector_size or self.vector_size

        try:
            self.client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=size,
                    distance=distance,
                ),
            )
            logger.info(f"Created collection: {name}")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Collection {name} already exists")
            else:
                raise

    def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: str,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upsert vectors with metadata.

        Args:
            vectors: List of vector dicts with 'id', 'vector', 'metadata'
            namespace: Namespace for multi-tenancy
            collection_name: Collection name (default: self.collection_name)

        Returns:
            Upsert status
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name

        # Convert to PointStruct format
        points = []
        for vec in vectors:
            payload = vec.get("metadata", {}).copy()
            payload["namespace"] = namespace
            payload["created_at"] = datetime.utcnow().isoformat()

            # Store original ID in payload for retrieval
            payload["original_id"] = vec["id"]

            # Convert hex ID to UUID string for Qdrant v1.12+
            # Take first 32 hex chars and format as UUID
            hex_id = str(vec["id"]).replace("-", "")[:32]
            # Pad if necessary
            hex_id = hex_id.ljust(32, '0')
            # Format as UUID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            point_id = f"{hex_id[:8]}-{hex_id[8:12]}-{hex_id[12:16]}-{hex_id[16:20]}-{hex_id[20:32]}"

            point = PointStruct(
                id=point_id,
                vector=vec["vector"],
                payload=payload,
            )
            points.append(point)

        # Batch upsert
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=name,
                points=batch,
            )
            total_upserted += len(batch)

        logger.info(f"Upserted {total_upserted} vectors to {name}")

        return {
            "upserted_count": total_upserted,
            "collection": name,
            "namespace": namespace,
        }

    def search(
        self,
        query_vector: List[float],
        namespace: str,
        top_k: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            namespace: Namespace filter
            top_k: Number of results
            score_threshold: Minimum similarity score
            filters: Additional metadata filters
            collection_name: Collection name (default: self.collection_name)

        Returns:
            List of search results with scores and metadata
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name

        # Build filter
        must_conditions = [
            FieldCondition(
                key="namespace",
                match=MatchValue(value=namespace),
            )
        ]

        # Add custom filters
        if filters:
            for key, value in filters.items():
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        search_filter = Filter(must=must_conditions)

        # Execute search
        results = self.client.search(
            collection_name=name,
            query_vector=query_vector,
            query_filter=search_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )

        # Format results
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "metadata": hit.payload,
            }
            for hit in results
        ]

    def delete_by_namespace(
        self,
        namespace: str,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete all vectors in a namespace.

        Args:
            namespace: Namespace to delete
            collection_name: Collection name (default: self.collection_name)

        Returns:
            Deletion status
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name

        # Delete by filter
        self.client.delete(
            collection_name=name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace),
                    )
                ]
            ),
        )

        logger.info(f"Deleted vectors in namespace: {namespace}")

        return {
            "deleted": True,
            "namespace": namespace,
            "collection": name,
        }

    def get_collection_info(
        self,
        collection_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get collection information.

        Args:
            collection_name: Collection name (default: self.collection_name)

        Returns:
            Collection stats
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name

        info = self.client.get_collection(collection_name=name)

        return {
            "name": name,
            "vector_size": info.config.params.vectors.size,
            "points_count": info.points_count,
            "indexed_vectors_count": info.indexed_vectors_count,
        }

    def count_vectors(
        self,
        namespace: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> int:
        """
        Count vectors in collection or namespace.

        Args:
            namespace: Optional namespace filter
            collection_name: Collection name (default: self.collection_name)

        Returns:
            Vector count
        """
        if not self.client:
            self.connect()

        name = collection_name or self.collection_name

        if namespace:
            count_filter = Filter(
                must=[
                    FieldCondition(
                        key="namespace",
                        match=MatchValue(value=namespace),
                    )
                ]
            )
            result = self.client.count(
                collection_name=name,
                count_filter=count_filter,
            )
            return result.count
        else:
            info = self.client.get_collection(collection_name=name)
            return info.points_count


# Singleton instance
_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient()
        _client.connect()
    return _client
