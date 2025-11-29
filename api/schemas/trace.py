"""
Code flow tracing schemas.

For tracing code execution flows through applications.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TraceRequest(BaseModel):
    """Request for code flow tracing."""

    namespace: str = Field(..., description="Namespace to search in")
    entry_point: Optional[str] = Field(
        None,
        description="Entry point file or function name (e.g., 'page.tsx', 'main', 'index')"
    )
    max_depth: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum depth to traverse"
    )
    include_code: bool = Field(
        default=True,
        description="Include code snippets in response"
    )


class CodeNode(BaseModel):
    """A node in the code flow trace."""

    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Function/class/file name")
    type: str = Field(..., description="Node type (function, class, file)")
    file_path: str = Field(..., description="File path")
    code: Optional[str] = Field(None, description="Code snippet")
    line_number: Optional[int] = Field(None, description="Line number")
    depth: int = Field(..., description="Depth in traversal")


class CodeRelationship(BaseModel):
    """A relationship between code nodes."""

    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type (CALLS, IMPORTS)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class TraceResponse(BaseModel):
    """Response from code flow tracing."""

    success: bool = Field(..., description="Whether trace succeeded")
    namespace: str = Field(..., description="Namespace traced")
    entry_point: str = Field(..., description="Entry point used")
    nodes: List[CodeNode] = Field(..., description="Nodes in the trace")
    relationships: List[CodeRelationship] = Field(..., description="Relationships between nodes")
    total_nodes: int = Field(..., description="Total nodes traced")
    total_relationships: int = Field(..., description="Total relationships traced")
    max_depth_reached: int = Field(..., description="Maximum depth reached")
    message: str = Field(..., description="Status message")
