"""
Query API schemas.

API Layer is responsible for this module.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request to query the codebase."""

    query: str = Field(..., min_length=1, description="User query")
    namespace: str = Field(..., description="Namespace to search")
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results to retrieve"
    )
    max_context_tokens: int = Field(
        default=4000,
        ge=100,
        le=16000,
        description="Maximum context tokens for LLM"
    )
    include_flow_analysis: bool = Field(
        default=False,
        description="Include flow analysis if applicable"
    )
    stream: bool = Field(
        default=False,
        description="Stream response in real-time"
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="LLM generation temperature"
    )
    provider: Optional[str] = Field(
        None,
        description="LLM provider (openai/anthropic)"
    )


class ContextItemResponse(BaseModel):
    """Context item in response."""

    content: str = Field(..., description="Context content")
    source_type: str = Field(..., description="Source type (code/document/graph)")
    relevance_score: float = Field(..., description="Relevance score")
    citation: Optional[str] = Field(None, description="Citation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QueryResponse(BaseModel):
    """Response from query."""

    # Generated response
    answer: str = Field(..., description="Generated answer")
    query: str = Field(..., description="Original query")

    # Intent and classification
    intent: str = Field(..., description="Detected intent")
    intent_confidence: float = Field(..., description="Intent confidence score")

    # Context used
    context_items: List[ContextItemResponse] = Field(
        default_factory=list,
        description="Context items used"
    )
    sources_count: int = Field(default=0, description="Number of sources")

    # Flow analysis (if applicable)
    flow_analysis: Optional[Dict[str, Any]] = Field(
        None,
        description="Flow analysis results"
    )

    # Metadata
    model: str = Field(..., description="LLM model used")
    tokens_used: Optional[int] = Field(None, description="Tokens used")
    retrieval_time: float = Field(default=0.0, description="Retrieval time in seconds")
    total_time: float = Field(default=0.0, description="Total processing time")


class StreamChunk(BaseModel):
    """Chunk for streaming responses."""

    chunk: str = Field(..., description="Response chunk")
    done: bool = Field(default=False, description="Is this the final chunk")
