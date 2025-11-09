"""
Flow analysis API endpoints.

API Layer is responsible for this module.
"""

from fastapi import APIRouter, HTTPException, status
import logging

from api.schemas import (
    FlowAnalysisRequest,
    FlowAnalysisResponse,
    FlowStepResponse,
    ParallelizationResponse,
    ParallelizationOpportunity,
)
from orchestrator.flow import get_flow_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flows", tags=["flows"])


@router.post("/analyze", response_model=FlowAnalysisResponse)
async def analyze_flow(request: FlowAnalysisRequest) -> FlowAnalysisResponse:
    """
    Analyze an execution flow for optimization opportunities.

    Returns detailed analysis including parallelization opportunities,
    critical path, and performance estimates.
    """
    logger.info(f"Analyzing flow in namespace: {request.namespace}, flow_id: {request.flow_id}")

    try:
        if not request.flow_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="flow_id is required for flow analysis"
            )

        # Get flow analyzer
        flow_analyzer = get_flow_analyzer()

        # Analyze flow
        analysis = flow_analyzer.analyze_flow(
            flow_id=request.flow_id,
            namespace=request.namespace
        )

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow not found: {request.flow_id}"
            )

        # Convert steps to response model
        steps = [
            FlowStepResponse(
                step_number=step.step_number,
                description=step.description,
                step_type=step.step_type.value,
                depends_on=step.depends_on,
                parallel_with=step.parallel_with,
                estimated_time=step.estimated_time,
                is_critical_path=step.is_critical_path,
            )
            for step in analysis.steps
        ]

        return FlowAnalysisResponse(
            flow_id=analysis.flow_id,
            description=analysis.description,
            total_steps=analysis.total_steps,
            steps=steps,
            parallel_groups=analysis.parallel_groups,
            critical_path=analysis.critical_path,
            sequential_time=analysis.sequential_time,
            parallel_time=analysis.parallel_time,
            speedup_potential=analysis.speedup_potential,
            recommendations=analysis.recommendations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flow analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flow analysis failed: {str(e)}"
        )


@router.post("/parallelization", response_model=ParallelizationResponse)
async def find_parallelization_opportunities(
    request: FlowAnalysisRequest
) -> ParallelizationResponse:
    """
    Find parallelization opportunities across flows.

    Identifies steps that can be executed in parallel to improve performance.
    """
    logger.info(f"Finding parallelization opportunities in namespace: {request.namespace}")

    try:
        # Get flow analyzer
        flow_analyzer = get_flow_analyzer()

        # Find opportunities
        opportunities_raw = flow_analyzer.find_parallelization_opportunities(
            namespace=request.namespace,
            flow_id=request.flow_id
        )

        # Convert to response model
        opportunities = [
            ParallelizationOpportunity(
                flow_id=opp["flow_id"],
                flow_description=opp["flow_description"],
                parallel_steps=opp["parallel_steps"],
            )
            for opp in opportunities_raw
        ]

        return ParallelizationResponse(
            namespace=request.namespace,
            opportunities=opportunities,
            total_opportunities=len(opportunities),
        )

    except Exception as e:
        logger.error(f"Parallelization search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parallelization search failed: {str(e)}"
        )
