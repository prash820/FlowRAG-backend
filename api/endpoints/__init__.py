"""API endpoints module."""

from .health import router as health_router
from .ingest import router as ingest_router
from .query import router as query_router
from .flow import router as flow_router
from .trace import router as trace_router
from .workflows import router as workflows_router
from .documentation import router as documentation_router

__all__ = [
    "health_router",
    "ingest_router",
    "query_router",
    "flow_router",
    "trace_router",
    "workflows_router",
    "documentation_router",
]
