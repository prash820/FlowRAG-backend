"""
Security utilities for FlowRAG API.

This module provides authentication, authorization, and validation utilities.
All security features can be disabled for development via ENABLE_SECURITY env var.
"""

from .auth import (
    verify_api_key,
    get_current_user,
    optional_verify_api_key,
    APIKeyAuth,
)
from .validation import (
    validate_file_path,
    validate_namespace,
    sanitize_error_message,
)
from .rate_limit import get_rate_limiter

__all__ = [
    "verify_api_key",
    "get_current_user",
    "optional_verify_api_key",
    "APIKeyAuth",
    "validate_file_path",
    "validate_namespace",
    "sanitize_error_message",
    "get_rate_limiter",
]
