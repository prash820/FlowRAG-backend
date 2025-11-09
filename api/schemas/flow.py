"""
Flow analysis API schemas.

API Layer is responsible for this module.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FlowAnalysisRequest(BaseModel):
    """Request for flow analysis."""

    namespace: str = Field(..., description="Namespace to search")
    flow_id: Optional[str] = Field(
        None,
        description="Specific flow ID to analyze"
    )


class FlowStepResponse(BaseModel):
    """Flow step in response."""

    step_number: int = Field(..., description="Step number")
    description: str = Field(..., description="Step description")
    step_type: str = Field(..., description="Step type (sequential/parallel/etc)")
    depends_on: List[int] = Field(
        default_factory=list,
        description="Dependencies"
    )
    parallel_with: List[int] = Field(
        default_factory=list,
        description="Steps that can run in parallel"
    )
    estimated_time: Optional[float] = Field(
        None,
        description="Estimated execution time"
    )
    is_critical_path: bool = Field(
        default=False,
        description="Is on critical path"
    )


class FlowAnalysisResponse(BaseModel):
    """Response from flow analysis."""

    flow_id: str = Field(..., description="Flow ID")
    description: str = Field(..., description="Flow description")
    total_steps: int = Field(..., description="Total steps")

    # Steps
    steps: List[FlowStepResponse] = Field(
        default_factory=list,
        description="Flow steps"
    )

    # Parallelization
    parallel_groups: List[List[int]] = Field(
        default_factory=list,
        description="Groups of steps that can run in parallel"
    )

    # Critical path
    critical_path: List[int] = Field(
        default_factory=list,
        description="Steps on critical path"
    )

    # Performance
    sequential_time: Optional[float] = Field(
        None,
        description="Sequential execution time"
    )
    parallel_time: Optional[float] = Field(
        None,
        description="Parallel execution time"
    )
    speedup_potential: Optional[float] = Field(
        None,
        description="Potential speedup factor"
    )

    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list,
        description="Optimization recommendations"
    )


class ParallelizationOpportunity(BaseModel):
    """Parallelization opportunity."""

    flow_id: str = Field(..., description="Flow ID")
    flow_description: str = Field(..., description="Flow description")
    parallel_steps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Steps that can be parallelized"
    )


class ParallelizationResponse(BaseModel):
    """Response from parallelization search."""

    namespace: str = Field(..., description="Namespace searched")
    opportunities: List[ParallelizationOpportunity] = Field(
        default_factory=list,
        description="Parallelization opportunities found"
    )
    total_opportunities: int = Field(
        default=0,
        description="Total opportunities"
    )
