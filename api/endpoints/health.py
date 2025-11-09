"""
Health check API endpoints.

API Layer is responsible for this module.
"""

from fastapi import APIRouter
import logging
from datetime import datetime

from api.schemas import HealthResponse
from databases import get_neo4j_client, get_qdrant_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Checks status of all dependent services.
    """
    services = {}

    # Check Neo4j
    try:
        neo4j_client = get_neo4j_client()
        # Simple query to test connection
        result = neo4j_client.execute_query("RETURN 1 as test", {})
        services["neo4j"] = "healthy" if result else "unhealthy"
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        services["neo4j"] = "unhealthy"

    # Check Qdrant
    try:
        qdrant_client = get_qdrant_client()
        # Test connection
        collections = qdrant_client.client.get_collections()
        services["qdrant"] = "healthy" if collections else "healthy"  # Empty is still healthy
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        services["qdrant"] = "unhealthy"

    # Overall status
    overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "unhealthy"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="0.1.0",
        services=services,
    )


@router.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "FlowRAG API",
        "version": "0.1.0",
        "description": "Graph RAG System with Flow Detection",
        "docs": "/docs",
        "health": "/health",
    }
