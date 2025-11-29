"""
Workflow API endpoints - Debug and Optimization workflows.

API Layer is responsible for this module.
"""

from fastapi import APIRouter, HTTPException, status
import logging
import time
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from orchestrator.workflows import (
    get_workflow_router,
    WorkflowRequest,
    WorkflowType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["workflows"])


# Request schemas
class DebugRequest(BaseModel):
    """Request for debug workflow."""

    query: str = Field(..., description="Debug query")
    namespace: str = Field(..., description="Namespace to search")
    error_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Error context (error_message, stack_trace, etc.)"
    )
    max_results: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=4000)
    include_code: bool = Field(default=True)


class OptimizeRequest(BaseModel):
    """Request for optimization workflow."""

    query: str = Field(..., description="Optimization query")
    namespace: str = Field(..., description="Namespace to search")
    target_function: Optional[str] = Field(
        default=None,
        description="Target function to optimize"
    )
    analysis_depth: int = Field(default=5, ge=1, le=10)
    max_results: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=4000)
    include_code: bool = Field(default=True)


# Response schemas
class WorkflowStageResponse(BaseModel):
    """Workflow stage information."""

    stage: str
    status: str
    results_count: int
    details: Dict[str, Any]


class DebugResponse(BaseModel):
    """Response from debug workflow."""

    success: bool
    query: str
    namespace: str
    answer: Optional[str] = None
    likely_causes: list = Field(default_factory=list)
    recommendations: list = Field(default_factory=list)
    similar_fixes: list = Field(default_factory=list)
    context_items: list = Field(default_factory=list)
    stages: list = Field(default_factory=list)
    total_time: float
    error: Optional[str] = None


class OptimizationResponse(BaseModel):
    """Response from optimization workflow."""

    success: bool
    query: str
    namespace: str
    answer: Optional[str] = None
    flow_map: Optional[Dict[str, Any]] = None
    bottlenecks: list = Field(default_factory=list)
    parallel_opportunities: list = Field(default_factory=list)
    context_items: list = Field(default_factory=list)
    stages: list = Field(default_factory=list)
    total_time: float
    error: Optional[str] = None


# Endpoints
@router.post("/debug", response_model=DebugResponse)
async def debug_workflow(request: DebugRequest) -> DebugResponse:
    """
    Execute debug workflow for issue hunting and root cause analysis.

    Multi-stage workflow:
    1. Locate: Broad semantic search to find relevant code
    2. Narrow: Graph traversal to trace call chains
    3. Diagnose: Pattern matching for likely causes
    4. Synthesize: LLM-powered analysis and recommendations
    """
    logger.info(f"Debug workflow: '{request.query}' in namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Get workflow router
        router = get_workflow_router()

        # Create workflow request
        workflow_request = WorkflowRequest(
            query=request.query,
            namespace=request.namespace,
            workflow_type=WorkflowType.DEBUG,
            error_context=request.error_context,
            max_results=request.max_results,
            max_context_tokens=request.max_context_tokens,
            include_code=request.include_code,
        )

        # Execute workflow
        result = await router.route(workflow_request)

        # Convert to response
        return DebugResponse(
            success=result.success,
            query=result.query,
            namespace=result.namespace,
            answer=result.answer,
            likely_causes=result.likely_causes,
            recommendations=result.recommendations,
            similar_fixes=result.similar_fixes,
            context_items=result.context_items,
            stages=[
                {
                    "stage": stage.stage,
                    "status": stage.status,
                    "results_count": stage.results_count,
                    "details": stage.details,
                }
                for stage in result.stages
            ],
            total_time=result.total_time,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Debug workflow failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug workflow failed: {str(e)}"
        )


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_workflow(request: OptimizeRequest) -> OptimizationResponse:
    """
    Execute optimization workflow for performance analysis.

    Multi-stage workflow:
    1. Map Flow: Build execution flow graph
    2. Detect Bottlenecks: Identify performance bottlenecks
    3. Find Parallelization: Discover parallel execution opportunities
    4. Generate Plan: LLM-powered optimization plan
    """
    logger.info(f"Optimization workflow: '{request.query}' in namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Get workflow router
        router = get_workflow_router()

        # Create workflow request
        workflow_request = WorkflowRequest(
            query=request.query,
            namespace=request.namespace,
            workflow_type=WorkflowType.OPTIMIZE,
            target_function=request.target_function,
            analysis_depth=request.analysis_depth,
            max_results=request.max_results,
            max_context_tokens=request.max_context_tokens,
            include_code=request.include_code,
        )

        # Execute workflow
        result = await router.route(workflow_request)

        # Convert to response
        return OptimizationResponse(
            success=result.success,
            query=result.query,
            namespace=result.namespace,
            answer=result.answer,
            flow_map=result.flow_map,
            bottlenecks=result.bottlenecks,
            parallel_opportunities=result.parallel_opportunities,
            context_items=result.context_items,
            stages=[
                {
                    "stage": stage.stage,
                    "status": stage.status,
                    "results_count": stage.results_count,
                    "details": stage.details,
                }
                for stage in result.stages
            ],
            total_time=result.total_time,
            error=result.error,
        )

    except Exception as e:
        logger.error(f"Optimization workflow failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization workflow failed: {str(e)}"
        )
