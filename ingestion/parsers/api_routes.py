"""
API Route models for route detection across languages.

Ingestion Agent is responsible for this module.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
import hashlib


@dataclass
class APIRoute:
    """Represents an extracted API route/endpoint."""

    # Required fields
    method: str          # GET, POST, PUT, DELETE, PATCH, OPTIONS
    path: str            # /api/users/:id
    handler: str         # Handler function name
    framework: str       # express, gorilla/mux, spring, etc.

    # Optional fields
    file_path: str = ""
    handler_line: Optional[int] = None
    middleware: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    description: Optional[str] = None
    service: Optional[str] = None

    def generate_id(self) -> str:
        """Generate unique ID for this endpoint."""
        key = f"{self.method}:{self.path}:{self.framework}:{self.file_path}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def to_dict(self, namespace: str) -> dict:
        """Convert to dictionary for Neo4j storage."""
        return {
            'id': self.generate_id(),
            'name': f"{self.method} {self.path}",
            'namespace': namespace,
            'http_method': self.method,
            'path': self.path,
            'handler_function': self.handler,
            'handler_file': self.file_path,
            'framework': self.framework,
            'middleware': self.middleware,
            'parameters': self.parameters,
            'description': self.description or "",
            'service': self.service or "",
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        }

    def __repr__(self) -> str:
        return f"APIRoute({self.method} {self.path} -> {self.handler})"
