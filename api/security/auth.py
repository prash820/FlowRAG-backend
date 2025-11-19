"""
Authentication module with optional enforcement.

Security can be disabled for development/testing by setting:
ENABLE_SECURITY=false in .env
"""

from typing import Optional
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
import logging

from config import get_settings

logger = logging.getLogger(__name__)

# API Key Header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyAuth:
    """API Key authentication with optional enforcement."""

    def __init__(self):
        self.settings = get_settings()
        # Check if security is enabled
        self.enabled = getattr(self.settings, 'enable_security', True)
        if self.settings.env == "development" and self.settings.debug:
            self.enabled = getattr(self.settings, 'enable_security', False)

        if not self.enabled:
            logger.warning("🔓 Security is DISABLED - All API endpoints are open!")

    def is_enabled(self) -> bool:
        """Check if security is enabled."""
        return self.enabled

    def get_valid_api_keys(self) -> set:
        """
        Get valid API keys from configuration.

        In production, this should load from a database or secrets manager.
        For now, uses environment variable.
        """
        api_keys_str = getattr(self.settings, 'api_keys', '')
        if api_keys_str:
            return set(key.strip() for key in api_keys_str.split(',') if key.strip())

        # Fallback: use SECRET_KEY as a valid API key for development
        if self.settings.env == "development":
            logger.warning("Using SECRET_KEY as API key - NOT FOR PRODUCTION!")
            return {self.settings.secret_key}

        return set()


# Global instance
_auth_instance = None


def get_auth_instance() -> APIKeyAuth:
    """Get or create auth instance."""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = APIKeyAuth()
    return _auth_instance


async def verify_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Verify API key (ENFORCED).

    Raises HTTPException if:
    - Security is enabled AND no key provided
    - Security is enabled AND invalid key

    Returns:
        The validated API key
    """
    auth = get_auth_instance()

    # If security is disabled, allow access
    if not auth.is_enabled():
        logger.debug("Security disabled - allowing access without API key")
        return "dev-mode-no-auth"

    # Security is enabled - enforce API key
    if not api_key:
        logger.warning("API key missing in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    valid_keys = auth.get_valid_api_keys()

    if not valid_keys:
        logger.error("No valid API keys configured!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key validation not properly configured"
        )

    if api_key not in valid_keys:
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    logger.debug("API key verified successfully")
    return api_key


async def optional_verify_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[str]:
    """
    Optional API key verification.

    Always allows access but logs if key is provided and invalid.
    Useful for endpoints that want to track usage but not block access.
    """
    auth = get_auth_instance()

    if not auth.is_enabled():
        return None

    if not api_key:
        return None

    valid_keys = auth.get_valid_api_keys()
    if api_key in valid_keys:
        return api_key

    logger.warning(f"Invalid API key provided (optional auth): {api_key[:10]}...")
    return None


async def get_current_user(api_key: str = Depends(verify_api_key)) -> dict:
    """
    Get current user information from API key.

    In a full implementation, this would look up user details from database.
    For now, returns basic info.
    """
    auth = get_auth_instance()

    if not auth.is_enabled():
        return {
            "user_id": "dev-user",
            "username": "developer",
            "role": "admin",
            "api_key": "dev-mode"
        }

    # In production, look up user from database using api_key
    # For now, return placeholder
    return {
        "user_id": "user-" + api_key[:8],
        "username": "api-user",
        "role": "user",
        "api_key": api_key[:10] + "..."
    }
