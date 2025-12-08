"""
Namespace Groups API schemas.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class NamespaceGroupCreate(BaseModel):
    """Request to create a namespace group."""
    name: str = Field(..., min_length=1, max_length=255, description="Unique group name")
    description: Optional[str] = Field(None, max_length=1000, description="Group description")
    namespaces: List[str] = Field(default_factory=list, description="Initial namespaces to include")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class NamespaceGroupUpdate(BaseModel):
    """Request to update a namespace group."""
    description: Optional[str] = Field(None, max_length=1000)
    metadata: Optional[Dict[str, Any]] = None


class NamespaceInGroup(BaseModel):
    """Namespace info within a group."""
    name: str
    source_type: str
    stats: Dict[str, int]
    created_at: Optional[str] = None


class NamespaceGroupResponse(BaseModel):
    """Response for a namespace group."""
    name: str
    description: Optional[str] = None
    namespaces: List[NamespaceInGroup] = Field(default_factory=list)
    namespace_count: int = 0
    total_nodes: int = 0
    total_relationships: int = 0
    created_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NamespaceGroupListResponse(BaseModel):
    """Response for listing namespace groups."""
    groups: List[NamespaceGroupResponse]
    total: int


class AddNamespacesToGroupRequest(BaseModel):
    """Request to add namespaces to a group."""
    namespaces: List[str] = Field(..., min_items=1, description="Namespaces to add")


class RemoveNamespacesFromGroupRequest(BaseModel):
    """Request to remove namespaces from a group."""
    namespaces: List[str] = Field(..., min_items=1, description="Namespaces to remove")


class GroupQueryRequest(BaseModel):
    """Request to query across a namespace group."""
    query: str = Field(..., min_length=1, max_length=10000, description="The query text")
    group_name: Optional[str] = Field(None, description="Name of the namespace group (optional, taken from URL path)")
    max_results: int = Field(default=10, ge=1, le=50, description="Max results per namespace")
    include_flow_analysis: bool = Field(default=False, description="Include flow analysis")
    include_cross_service: bool = Field(default=True, description="Include cross-service relationships")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class GroupQueryResponse(BaseModel):
    """Response from a group query."""
    answer: str
    query: str
    group_name: str
    namespaces_searched: List[str]
    context_items: List[Dict[str, Any]] = Field(default_factory=list)
    sources_count: int = 0
    flow_analysis: Optional[Dict[str, Any]] = None
    retrieval_time: float = 0.0
    total_time: float = 0.0
