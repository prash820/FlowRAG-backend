"""
Workflow Router - Facade pattern for specialized query processing.

Routes queries to appropriate workflow based on intent.
Non-intrusive: sits on top of existing orchestrator.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging

from orchestrator.router.intent_classifier import QueryIntent
from orchestrator import get_orchestrator, OrchestrationRequest

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Types of specialized workflows."""

    DEBUG = "debug"           # Issue hunting, error tracing
    OPTIMIZE = "optimize"     # Performance, parallelization
    GENERAL = "general"       # Questions, exploration (existing)


class WorkflowRequest(BaseModel):
    """Request for workflow processing."""

    query: str = Field(..., description="User query")
    namespace: str = Field(..., description="Namespace to search")
    workflow_type: Optional[WorkflowType] = Field(
        default=None,
        description="Explicit workflow type (auto-detected if not provided)"
    )

    # Debug-specific fields
    error_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Error context for debug workflow (stack trace, logs, etc.)"
    )

    # Optimization-specific fields
    target_function: Optional[str] = Field(
        default=None,
        description="Target function for optimization analysis"
    )
    analysis_depth: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Max depth for flow analysis"
    )

    # General parameters
    max_results: int = Field(default=10, ge=1, le=50)
    max_context_tokens: int = Field(default=4000)
    include_code: bool = Field(default=True)


class WorkflowStage(BaseModel):
    """Stage in multi-stage workflow execution."""

    stage: str = Field(..., description="Stage name")
    status: str = Field(..., description="completed, running, failed")
    results_count: int = Field(default=0)
    details: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    """Result from workflow processing."""

    success: bool
    workflow_type: WorkflowType
    query: str
    namespace: str

    # General fields
    answer: Optional[str] = None
    context_items: List[Dict[str, Any]] = Field(default_factory=list)

    # Multi-stage workflows
    stages: List[WorkflowStage] = Field(default_factory=list)

    # Debug-specific
    likely_causes: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    similar_fixes: List[Dict[str, Any]] = Field(default_factory=list)

    # Optimization-specific
    flow_map: Optional[Dict[str, Any]] = None
    bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    parallel_opportunities: List[Dict[str, Any]] = Field(default_factory=list)

    # Metadata
    total_time: float = 0.0
    error: Optional[str] = None


class WorkflowRouter:
    """
    Routes queries to specialized workflows.

    Facade pattern: provides unified interface while delegating to
    appropriate workflow implementation.
    """

    def __init__(self):
        """Initialize router with workflow implementations."""
        # Import workflows lazily to avoid circular imports
        from orchestrator.workflows.debug_workflow import DebugWorkflow
        from orchestrator.workflows.optimization_workflow import OptimizationWorkflow

        self.debug_workflow = DebugWorkflow()
        self.optimization_workflow = OptimizationWorkflow()
        self.general_orchestrator = get_orchestrator()

        # Intent to workflow mapping
        self.intent_mapping = {
            # Debug workflow triggers
            QueryIntent.FIND_USAGE: WorkflowType.DEBUG,
            QueryIntent.TRACE_CALLS: WorkflowType.DEBUG,

            # Optimization workflow triggers
            QueryIntent.OPTIMIZE_FLOW: WorkflowType.OPTIMIZE,
            QueryIntent.PARALLEL_STEPS: WorkflowType.OPTIMIZE,
            QueryIntent.FIND_DEPENDENCIES: WorkflowType.OPTIMIZE,

            # All others → general workflow (existing system)
        }

    async def route(self, request: WorkflowRequest) -> WorkflowResult:
        """
        Route request to appropriate workflow.

        Args:
            request: Workflow request

        Returns:
            WorkflowResult from appropriate workflow
        """
        import time
        start_time = time.time()

        try:
            # Determine workflow type
            workflow_type = self._determine_workflow(request)

            logger.info(f"Routing query to {workflow_type.value} workflow: {request.query[:50]}...")

            # Execute appropriate workflow
            if workflow_type == WorkflowType.DEBUG:
                result = await self.debug_workflow.execute(request)

            elif workflow_type == WorkflowType.OPTIMIZE:
                result = await self.optimization_workflow.execute(request)

            else:  # GENERAL - Use existing orchestrator
                result = self._execute_general_workflow(request)

            # Add metadata
            result.total_time = time.time() - start_time
            result.workflow_type = workflow_type

            return result

        except Exception as e:
            logger.error(f"Workflow routing failed: {e}", exc_info=True)
            return WorkflowResult(
                success=False,
                workflow_type=WorkflowType.GENERAL,
                query=request.query,
                namespace=request.namespace,
                error=str(e),
                total_time=time.time() - start_time
            )

    def _determine_workflow(self, request: WorkflowRequest) -> WorkflowType:
        """
        Determine which workflow to use.

        Priority:
        1. Explicit workflow_type in request
        2. Intent classification from query
        3. Default to GENERAL
        """
        # Explicit workflow type
        if request.workflow_type:
            return request.workflow_type

        # Classify intent
        from orchestrator.router.intent_classifier import get_intent_classifier
        classifier = get_intent_classifier()
        intent_result = classifier.classify(request.query)

        # Map intent to workflow
        workflow_type = self.intent_mapping.get(
            intent_result.intent,
            WorkflowType.GENERAL
        )

        # Special case: if error_context provided, force DEBUG
        if request.error_context:
            workflow_type = WorkflowType.DEBUG

        # Special case: if target_function provided, force OPTIMIZE
        if request.target_function:
            workflow_type = WorkflowType.OPTIMIZE

        return workflow_type

    def _execute_general_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        """
        Execute general workflow using existing orchestrator.

        This is the backward-compatible path - uses existing system unchanged.
        """
        # Build orchestration request
        orch_request = OrchestrationRequest(
            query=request.query,
            namespace=request.namespace,
            max_results=request.max_results,
            max_context_tokens=request.max_context_tokens,
            include_flow_analysis=False,
        )

        # Use existing orchestrator
        orch_result = self.general_orchestrator.orchestrate(orch_request)

        # Generate response using existing LLM agent
        from agents.llm import get_response_generator, ResponseRequest
        response_generator = get_response_generator()

        response_request = ResponseRequest(
            orchestration_result=orch_result,
            stream=False,
        )

        # Synchronous generation
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        generated_response = loop.run_until_complete(
            response_generator.generate_async(response_request)
        )
        loop.close()

        # Format context items
        context_items = []
        if orch_result.context:
            for item in orch_result.context.items:
                context_items.append({
                    "content": item.content,
                    "source_type": item.source_type,
                    "relevance_score": item.relevance_score,
                    "citation": item.citation,
                    "metadata": item.metadata,
                })

        return WorkflowResult(
            success=True,
            workflow_type=WorkflowType.GENERAL,
            query=request.query,
            namespace=request.namespace,
            answer=generated_response.content,
            context_items=context_items,
        )


# Singleton instance
_router: Optional[WorkflowRouter] = None


def get_workflow_router() -> WorkflowRouter:
    """Get or create workflow router instance."""
    global _router

    if _router is None:
        _router = WorkflowRouter()

    return _router
