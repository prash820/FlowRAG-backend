"""
CORS middleware configuration.

API Layer is responsible for this module.
"""

import logging
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from config import get_settings

logger = logging.getLogger(__name__)


def get_allowed_origins() -> List[str]:
    """
    Get allowed CORS origins based on environment.

    Returns:
        List of allowed origin URLs
    """
    settings = get_settings()

    # Development origins (always allowed in dev mode)
    dev_origins = [
        "http://localhost:3000",   # React dev server
        "http://localhost:5173",   # Vite dev server
        "http://localhost:8080",   # Alternative frontend
        "http://localhost:8501",   # Streamlit UI
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8501",
    ]

    # In development, allow all dev origins
    if settings.env == "development" and settings.debug:
        logger.info("🔓 CORS: Development mode - allowing local origins")
        return dev_origins

    # In production, use explicit whitelist from environment
    # Check for CORS_ORIGINS environment variable
    cors_origins_str = getattr(settings, 'cors_origins', None)

    if cors_origins_str:
        # Parse comma-separated origins from environment
        production_origins = [
            origin.strip()
            for origin in cors_origins_str.split(',')
            if origin.strip()
        ]
        logger.info(f"✅ CORS: Production mode - {len(production_origins)} origins whitelisted")
        return production_origins

    # Production without explicit configuration - only allow localhost (safe default)
    logger.warning("⚠️  CORS: No production origins configured - defaulting to localhost only")
    return ["http://localhost:8000"]


def setup_cors(app: FastAPI) -> None:
    """
    Setup CORS middleware with environment-specific configuration.

    Development:
    - Allows all localhost origins
    - Allows credentials
    - Allows all methods and headers

    Production:
    - Requires explicit origin whitelist via CORS_ORIGINS env var
    - Restricted methods and headers (if configured)
    - Credentials support configurable
    """
    settings = get_settings()
    allowed_origins = get_allowed_origins()

    # In production, be more restrictive
    if settings.env == "production":
        allow_methods = ["GET", "POST", "PUT", "DELETE"]
        allow_headers = [
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "Accept",
            "Origin",
        ]
    else:
        # Development - allow all for flexibility
        allow_methods = ["*"]
        allow_headers = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
    )

    logger.info(f"CORS middleware configured with {len(allowed_origins)} allowed origins")
