"""
Main orchestrator controller.

Orchestrator Agent is responsible for this module.
Coordinates intent classification, retrieval, context assembly, and flow analysis.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from orchestrator.router.intent_classifier import (
    get_intent_classifier,
    IntentResult,
    QueryIntent,
)
from orchestrator.retrieval.hybrid_retriever import (
    get_hybrid_retriever,
    RetrievalResult,
)
from orchestrator.context.context_assembler import (
    get_context_assembler,
    AssembledContext,
)
from orchestrator.flow.flow_analyzer import (
    get_flow_analyzer,
    FlowAnalysis,
)

logger = logging.getLogger(__name__)


class OrchestrationRequest(BaseModel):
    """Request for orchestration."""

    query: str = Field(..., description="User query")
    namespace: str = Field(..., description="Namespace to search")
    max_results: int = Field(default=10, ge=1, le=50, description="Max results")
    max_context_tokens: int = Field(default=4000, description="Max context tokens")
    include_flow_analysis: bool = Field(
        default=False,
        description="Include flow analysis if applicable"
    )


class OrchestrationResult(BaseModel):
    """Result from orchestration."""

    # Original request
    query: str
    namespace: str

    # Intent classification
    intent: QueryIntent
    intent_confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Retrieval results
    retrieval_result: Optional[RetrievalResult] = None

    # Assembled context
    context: Optional[AssembledContext] = None

    # Flow analysis (if requested and applicable)
    flow_analysis: Optional[FlowAnalysis] = None

    # Metadata
    total_retrieval_time: float = Field(default=0.0)
    total_orchestration_time: float = Field(default=0.0)

    # Flags
    requires_llm: bool = Field(
        default=True,
        description="Whether LLM is needed for this query"
    )


class Orchestrator:
    """
    Main orchestrator coordinating all retrieval and analysis.

    Responsibilities:
    1. Classify query intent
    2. Route to appropriate retrieval strategy
    3. Assemble context for LLM
    4. Detect and analyze execution flows
    """

    def __init__(
        self,
        max_context_tokens: int = 4000,
    ):
        """
        Initialize orchestrator.

        Args:
            max_context_tokens: Maximum tokens for LLM context
        """
        self.intent_classifier = get_intent_classifier()
        self.retriever = get_hybrid_retriever()
        self.context_assembler = get_context_assembler(max_context_tokens)
        self.flow_analyzer = get_flow_analyzer()

    def orchestrate(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResult:
        """
        Orchestrate retrieval and analysis for a query.

        Args:
            request: Orchestration request

        Returns:
            OrchestrationResult with context and analysis
        """
        import time
        start_time = time.time()

        # Step 1: Classify intent
        intent_result = self._classify_intent(request.query)

        # Step 2: Retrieve relevant information
        retrieval_result = self._retrieve(
            query=request.query,
            namespace=request.namespace,
            intent_result=intent_result,
            top_k=request.max_results,
        )

        # Step 3: Assemble context
        context = self._assemble_context(
            retrieval_result=retrieval_result,
            query=request.query,
            intent=intent_result.intent,
        )

        # Step 4: Flow analysis (if applicable)
        flow_analysis = None
        if request.include_flow_analysis and self._should_analyze_flow(intent_result):
            flow_analysis = self._analyze_flow(
                retrieval_result=retrieval_result,
                namespace=request.namespace,
            )

        # Build result
        total_time = time.time() - start_time

        result = OrchestrationResult(
            query=request.query,
            namespace=request.namespace,
            intent=intent_result.intent,
            intent_confidence=intent_result.confidence,
            entities=intent_result.entities,
            retrieval_result=retrieval_result,
            context=context,
            flow_analysis=flow_analysis,
            total_retrieval_time=retrieval_result.retrieval_time,
            total_orchestration_time=total_time,
            requires_llm=self._requires_llm(intent_result, context),
        )

        logger.info(
            f"Orchestration completed in {total_time:.2f}s - "
            f"Intent: {intent_result.intent.value}, "
            f"Results: {retrieval_result.total_results}, "
            f"Context tokens: {context.total_tokens}"
        )

        return result

    def _classify_intent(self, query: str) -> IntentResult:
        """Classify query intent."""
        logger.debug(f"Classifying intent for query: {query}")
        return self.intent_classifier.classify(query)

    def _retrieve(
        self,
        query: str,
        namespace: str,
        intent_result: IntentResult,
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve relevant information."""
        logger.debug(
            f"Retrieving for intent: {intent_result.intent.value}, "
            f"Graph: {intent_result.requires_graph}, "
            f"Vector: {intent_result.requires_vector}"
        )

        return self.retriever.retrieve(
            query=query,
            namespace=namespace,
            intent=intent_result.intent,
            top_k=top_k,
            entities=intent_result.entities,
        )

    def _assemble_context(
        self,
        retrieval_result: RetrievalResult,
        query: str,
        intent: QueryIntent,
    ) -> AssembledContext:
        """Assemble context from retrieval results."""
        logger.debug(
            f"Assembling context from "
            f"{len(retrieval_result.vector_results)} vector results, "
            f"{len(retrieval_result.graph_results)} graph results"
        )

        return self.context_assembler.assemble(
            retrieval_result=retrieval_result,
            query=query,
            intent=intent,
        )

    def _should_analyze_flow(self, intent_result: IntentResult) -> bool:
        """Determine if flow analysis is applicable."""
        flow_intents = {
            QueryIntent.FIND_FLOW,
            QueryIntent.PARALLEL_STEPS,
            QueryIntent.OPTIMIZE_FLOW,
        }

        return intent_result.intent in flow_intents

    def _analyze_flow(
        self,
        retrieval_result: RetrievalResult,
        namespace: str,
    ) -> Optional[FlowAnalysis]:
        """Analyze execution flow if applicable."""
        # Try to extract flow_id from graph results
        flow_id = self._extract_flow_id(retrieval_result.graph_results)

        if not flow_id:
            logger.debug("No flow ID found for analysis")
            return None

        logger.debug(f"Analyzing flow: {flow_id}")
        return self.flow_analyzer.analyze_flow(flow_id, namespace)

    def _extract_flow_id(
        self,
        graph_results: list[Dict[str, Any]]
    ) -> Optional[str]:
        """Extract flow ID from graph results."""
        for result in graph_results:
            # Check if result has flow data
            if "flow" in result:
                flow_data = result["flow"]
                if isinstance(flow_data, dict) and "id" in flow_data:
                    return flow_data["id"]

            # Check if result directly has id
            if "id" in result:
                return result["id"]

        return None

    def _requires_llm(
        self,
        intent_result: IntentResult,
        context: AssembledContext
    ) -> bool:
        """
        Determine if LLM is needed to answer this query.

        Some queries can be answered directly from graph results.
        """
        # Intents that might not need LLM
        direct_answer_intents = {
            QueryIntent.FIND_FUNCTION,
            QueryIntent.FIND_CLASS,
        }

        # If we have good context, LLM is needed
        if context.total_items > 0:
            return True

        # Low confidence = need LLM to handle uncertainty
        if intent_result.confidence < 0.7:
            return True

        return True  # Default to using LLM

    def find_parallelization_opportunities(
        self,
        namespace: str,
        flow_id: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        Find parallelization opportunities.

        This is a specialized operation for flow optimization.

        Args:
            namespace: Namespace to search
            flow_id: Optional specific flow ID

        Returns:
            List of parallelization opportunities
        """
        logger.info(f"Finding parallelization opportunities in namespace: {namespace}")
        return self.flow_analyzer.find_parallelization_opportunities(
            namespace=namespace,
            flow_id=flow_id
        )


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator(max_context_tokens: int = 4000) -> Orchestrator:
    """Get orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(max_context_tokens=max_context_tokens)
    return _orchestrator
