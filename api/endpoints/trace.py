"""
Code flow tracing API endpoints.

Provides linear code flow analysis starting from entry points.
"""

from fastapi import APIRouter, HTTPException, status
import logging

from api.schemas import (
    TraceRequest,
    TraceResponse,
    CodeNode,
    CodeRelationship,
)
from orchestrator.trace import get_code_tracer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trace", tags=["trace"])


@router.post("/flow", response_model=TraceResponse)
async def trace_code_flow(request: TraceRequest) -> TraceResponse:
    """
    Trace code flow from an entry point.

    This endpoint performs graph traversal following CALLS and IMPORTS
    relationships to trace the execution flow through the application.

    Use this for linear, logical flow analysis:
    - Start from homepage/entry point
    - Follow authentication flows
    - Trace API call chains
    - Track data storage operations
    - Map request/response cycles

    Args:
        request: Trace request with namespace and optional entry point

    Returns:
        Traced nodes and relationships in execution order
    """
    logger.info(
        f"Tracing code flow in namespace: {request.namespace}, "
        f"entry_point: {request.entry_point or 'auto-detect'}"
    )

    try:
        # Get code tracer
        tracer = get_code_tracer()

        # Trace the flow
        result = tracer.trace_linear_flow(
            namespace=request.namespace,
            entry_point=request.entry_point,
            max_depth=request.max_depth,
            include_code=request.include_code,
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result['message']
            )

        # Convert to response model
        nodes = [
            CodeNode(
                id=node['id'],
                name=node['name'],
                type=node['type'],
                file_path=node['file_path'],
                code=node.get('code'),
                line_number=node.get('line_number'),
                depth=node['depth']
            )
            for node in result['nodes']
        ]

        relationships = [
            CodeRelationship(
                from_id=rel['from_id'],
                to_id=rel['to_id'],
                type=rel['type'],
                properties=rel.get('properties', {})
            )
            for rel in result['relationships']
            if rel.get('to_id') is not None  # Filter out relationships with null to_id
        ]

        return TraceResponse(
            success=True,
            namespace=request.namespace,
            entry_point=result['entry_point'],
            nodes=nodes,
            relationships=relationships,
            total_nodes=result['total_nodes'],
            total_relationships=result['total_relationships'],
            max_depth_reached=result['max_depth_reached'],
            message=result['message']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code flow tracing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tracing failed: {str(e)}"
        )
