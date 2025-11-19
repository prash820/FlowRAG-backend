"""
Rate limiting with optional enforcement.

Rate limiting can be disabled for development/testing.
Uses slowapi for implementation.
"""

import logging
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import get_settings

logger = logging.getLogger(__name__)


def get_rate_limiter() -> Optional[Limiter]:
    """
    Get rate limiter instance.

    Returns None if rate limiting is disabled (development mode).
    """
    settings = get_settings()

    # Check if rate limiting is enabled
    enable_rate_limit = getattr(settings, 'enable_rate_limiting', True)

    if settings.env == "development" and settings.debug:
        enable_rate_limit = getattr(settings, 'enable_rate_limiting', False)

    if not enable_rate_limit:
        logger.warning("🔓 Rate limiting is DISABLED - API can be abused!")
        return None

    # Create limiter
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute}/minute"],
        storage_uri="memory://",  # Can be configured to use Redis
    )

    logger.info(f"✅ Rate limiting enabled: {settings.rate_limit_per_minute}/minute")
    return limiter


# Create global limiter instance
_limiter_instance = None


def get_limiter() -> Optional[Limiter]:
    """Get or create limiter instance."""
    global _limiter_instance
    if _limiter_instance is None:
        _limiter_instance = get_rate_limiter()
    return _limiter_instance
