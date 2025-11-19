"""
Input validation and sanitization utilities.

Provides path validation, namespace validation, and error sanitization.
Can be optionally enabled/disabled via configuration.
"""

import re
from pathlib import Path
from typing import Optional, List
from fastapi import HTTPException, status
import logging

from config import get_settings

logger = logging.getLogger(__name__)


class ValidationConfig:
    """Configuration for validation settings."""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = getattr(self.settings, 'enable_path_validation', True)
        self.allowed_directories = self._get_allowed_directories()

        if not self.enabled:
            logger.warning("🔓 Path validation is DISABLED - Security risk!")

    def _get_allowed_directories(self) -> List[Path]:
        """Get list of allowed directories for file operations."""
        allowed_dirs_str = getattr(self.settings, 'allowed_directories', '')

        if allowed_dirs_str:
            dirs = [Path(d.strip()) for d in allowed_dirs_str.split(',') if d.strip()]
            return [d.resolve() for d in dirs]

        # Default allowed directories for development
        if self.settings.env == "development":
            logger.warning("Using default allowed directories for development")
            return [
                Path.cwd(),  # Current directory
                Path.home(),  # User home directory
            ]

        # Production should have explicit allowed directories
        logger.error("No allowed directories configured for production!")
        return []


# Global instance
_validation_config = None


def get_validation_config() -> ValidationConfig:
    """Get or create validation config instance."""
    global _validation_config
    if _validation_config is None:
        _validation_config = ValidationConfig()
    return _validation_config


def validate_file_path(file_path: str, must_exist: bool = True) -> Path:
    """
    Validate and sanitize file path to prevent directory traversal.

    Args:
        file_path: The file path to validate
        must_exist: Whether the file must exist

    Returns:
        Validated absolute Path object

    Raises:
        HTTPException: If path is invalid or outside allowed directories
    """
    config = get_validation_config()

    try:
        # Convert to absolute path and resolve symlinks
        abs_path = Path(file_path).resolve()

        # Check if validation is enabled
        if not config.enabled:
            logger.debug(f"Path validation disabled - allowing: {abs_path}")
            if must_exist and not abs_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )
            return abs_path

        # Validation is enabled - check allowed directories
        allowed_directories = config.allowed_directories

        if not allowed_directories:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File access not properly configured"
            )

        # Check if path is within any allowed directory
        is_allowed = False
        for allowed_dir in allowed_directories:
            try:
                abs_path.relative_to(allowed_dir)
                is_allowed = True
                logger.debug(f"Path {abs_path} is within allowed directory {allowed_dir}")
                break
            except ValueError:
                continue

        if not is_allowed:
            logger.warning(f"Access denied to path outside allowed directories: {abs_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Path outside allowed directories"
            )

        # Check file exists if required
        if must_exist:
            if not abs_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: {file_path}"
                )

            if not abs_path.is_file():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a file: {file_path}"
                )

        return abs_path

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file path: {str(e)}"
        )


def validate_directory_path(dir_path: str, must_exist: bool = True) -> Path:
    """
    Validate directory path.

    Similar to validate_file_path but for directories.
    """
    config = get_validation_config()

    try:
        abs_path = Path(dir_path).resolve()

        # Check if validation is enabled
        if not config.enabled:
            logger.debug(f"Path validation disabled - allowing directory: {abs_path}")
            if must_exist and not abs_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Directory not found: {dir_path}"
                )
            return abs_path

        # Validation enabled - check allowed directories
        allowed_directories = config.allowed_directories

        if not allowed_directories:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Directory access not properly configured"
            )

        # Check if path is within allowed directories
        is_allowed = False
        for allowed_dir in allowed_directories:
            try:
                abs_path.relative_to(allowed_dir)
                is_allowed = True
                break
            except ValueError:
                continue

        if not is_allowed:
            logger.warning(f"Access denied to directory: {abs_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Directory outside allowed paths"
            )

        # Check directory exists if required
        if must_exist:
            if not abs_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Directory not found: {dir_path}"
                )

            if not abs_path.is_dir():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path is not a directory: {dir_path}"
                )

        return abs_path

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Directory validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid directory path: {str(e)}"
        )


def validate_namespace(namespace: str) -> str:
    """
    Validate namespace to prevent injection attacks.

    Ensures namespace contains only safe characters.

    Args:
        namespace: The namespace to validate

    Returns:
        The validated namespace string

    Raises:
        HTTPException: If namespace contains invalid characters
    """
    if not namespace:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Namespace cannot be empty"
        )

    # Allow only alphanumeric, underscore, hyphen, and dot
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', namespace):
        logger.warning(f"Invalid namespace format: {namespace}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Namespace can only contain letters, numbers, underscore, hyphen, and dot"
        )

    # Check length
    if len(namespace) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Namespace too long (max 100 characters)"
        )

    return namespace


def sanitize_error_message(error: Exception, include_details: bool = None) -> str:
    """
    Sanitize error messages to prevent information leakage.

    Args:
        error: The exception to sanitize
        include_details: Whether to include detailed error info.
                        If None, uses debug mode from settings.

    Returns:
        Sanitized error message
    """
    settings = get_settings()

    if include_details is None:
        include_details = settings.debug

    if include_details:
        # Development mode - include full error details
        return str(error)
    else:
        # Production mode - generic error message
        # Log the real error internally
        logger.error(f"Internal error (sanitized in response): {error}", exc_info=True)
        return "An internal error occurred. Please contact support."


def validate_query_length(query: str, max_length: int = 10000) -> str:
    """
    Validate query string length.

    Args:
        query: The query string
        max_length: Maximum allowed length

    Returns:
        The validated query

    Raises:
        HTTPException: If query is too long
    """
    if len(query) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query too long (max {max_length} characters)"
        )

    if len(query.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )

    return query


def validate_limit(limit: int, max_limit: int = 100) -> int:
    """
    Validate result limit parameter.

    Args:
        limit: The requested limit
        max_limit: Maximum allowed limit

    Returns:
        The validated limit

    Raises:
        HTTPException: If limit is invalid
    """
    if limit < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be at least 1"
        )

    if limit > max_limit:
        logger.warning(f"Limit {limit} exceeds max {max_limit}, capping")
        return max_limit

    return limit
