"""
Ingestion API schemas.

API Layer is responsible for this module.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class FileType(str, Enum):
    """Supported file types."""
    CODE = "code"
    DOCUMENT = "document"


class IngestFileRequest(BaseModel):
    """Request to ingest a file."""

    file_path: str = Field(..., description="Path to file to ingest")
    namespace: str = Field(..., description="Namespace for organization")
    file_type: Optional[FileType] = Field(
        None,
        description="File type (auto-detected if not provided)"
    )
    language: Optional[str] = Field(
        None,
        description="Programming language (auto-detected if not provided)"
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing data for this file"
    )

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate namespace format."""
        if not v or not v.strip():
            raise ValueError("Namespace cannot be empty")
        # Simple alphanumeric + underscore validation
        if not all(c.isalnum() or c in ('_', '-') for c in v):
            raise ValueError("Namespace must contain only alphanumeric, underscore, or hyphen characters")
        return v.strip()


class IngestDirectoryRequest(BaseModel):
    """Request to ingest a directory."""

    directory_path: str = Field(..., description="Path to directory")
    namespace: str = Field(..., description="Namespace for organization")
    recursive: bool = Field(default=True, description="Recursively ingest subdirectories")
    file_patterns: Optional[List[str]] = Field(
        None,
        description="File patterns to include (e.g., ['*.py', '*.js'])"
    )
    exclude_patterns: Optional[List[str]] = Field(
        default_factory=lambda: ["node_modules", ".git", "__pycache__", "*.pyc"],
        description="Patterns to exclude"
    )
    overwrite: bool = Field(default=False, description="Overwrite existing data")

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        """Validate namespace format."""
        if not v or not v.strip():
            raise ValueError("Namespace cannot be empty")
        if not all(c.isalnum() or c in ('_', '-') for c in v):
            raise ValueError("Namespace must contain only alphanumeric, underscore, or hyphen characters")
        return v.strip()


class IngestResponse(BaseModel):
    """Response from ingestion."""

    success: bool = Field(..., description="Success flag")
    message: str = Field(..., description="Result message")
    namespace: str = Field(..., description="Namespace used")

    # Statistics
    files_processed: int = Field(default=0, description="Number of files processed")
    nodes_created: int = Field(default=0, description="Graph nodes created")
    relationships_created: int = Field(default=0, description="Graph relationships created")
    vectors_stored: int = Field(default=0, description="Vectors stored")

    # Details
    processing_time: float = Field(default=0.0, description="Processing time in seconds")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


class DeleteNamespaceRequest(BaseModel):
    """Request to delete a namespace."""

    namespace: str = Field(..., description="Namespace to delete")
    confirm: bool = Field(
        ...,
        description="Confirmation flag (must be True)"
    )

    @field_validator("confirm")
    @classmethod
    def validate_confirm(cls, v: bool) -> bool:
        """Ensure confirmation is True."""
        if not v:
            raise ValueError("Confirmation required to delete namespace")
        return v


class DeleteNamespaceResponse(BaseModel):
    """Response from namespace deletion."""

    success: bool = Field(..., description="Success flag")
    message: str = Field(..., description="Result message")
    namespace: str = Field(..., description="Namespace deleted")
    nodes_deleted: int = Field(default=0, description="Graph nodes deleted")
    vectors_deleted: int = Field(default=0, description="Vectors deleted")
