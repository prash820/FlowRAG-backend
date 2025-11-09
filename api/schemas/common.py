"""
Common API schemas.

API Layer is responsible for this module.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status (healthy/unhealthy)")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(default="0.1.0", description="API version")
    services: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependent services"
    )


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp"
    )


class SuccessResponse(BaseModel):
    """Generic success response."""

    success: bool = Field(default=True, description="Success flag")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
