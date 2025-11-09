"""
FastAPI application entry point.
API Agent is responsible for this module.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from config import get_settings
from api.middleware import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
    setup_cors,
    RequestLoggingMiddleware,
)
from api.endpoints import (
    health_router,
    ingest_router,
    query_router,
    flow_router,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Graph RAG system with flow detection capabilities",
    version="0.1.0",
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Setup CORS
setup_cors(app)

# Add logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include routers
app.include_router(health_router)
app.include_router(ingest_router, prefix=settings.api_prefix)
app.include_router(query_router, prefix=settings.api_prefix)
app.include_router(flow_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_event():
    """Startup event - initialize services."""
    logger.info(f"Starting {settings.app_name} v0.1.0")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"API docs available at: {settings.api_prefix}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event - cleanup resources."""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
