"""
Hybrid retrieval combining graph traversal and vector search.

Orchestrator Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from databases import get_neo4j_client, get_qdrant_client
from databases.neo4j import queries
from ingestion.embeddings import get_embedding_service
from orchestrator.router.intent_classifier import QueryIntent

logger = logging.getLogger(__name__)


class RetrievalResult(BaseModel):
    """Result from hybrid retrieval."""

    # Vector search results
    vector_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Graph traversal results
    graph_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Combined metadata
    total_results: int = Field(default=0)
    retrieval_time: float = Field(default=0.0)


class HybridRetriever:
    """
    Hybrid retrieval combining:
    - Vector search (Qdrant) for semantic similarity
    - Graph traversal (Neo4j) for structural relationships
    """

    def __init__(self):
        """Initialize retriever."""
        self.neo4j_client = get_neo4j_client()
        self.qdrant_client = get_qdrant_client()
        self.embedding_service = get_embedding_service()

    def retrieve(
        self,
        query: str,
        namespace: str,
        intent: QueryIntent,
        top_k: int = 10,
        entities: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant information based on query and intent.

        Args:
            query: User query
            namespace: Namespace to search in
            intent: Detected query intent
            top_k: Number of results to retrieve
            entities: Extracted entities from query

        Returns:
            RetrievalResult with combined results
        """
        import time
        start_time = time.time()

        entities = entities or {}

        # Retrieve based on intent
        if intent == QueryIntent.FIND_FUNCTION:
            result = self._retrieve_function(query, namespace, entities, top_k)

        elif intent == QueryIntent.FIND_CLASS:
            result = self._retrieve_class(query, namespace, entities, top_k)

        elif intent == QueryIntent.FIND_USAGE:
            result = self._retrieve_usage(query, namespace, entities, top_k)

        elif intent == QueryIntent.TRACE_CALLS:
            result = self._retrieve_call_chain(query, namespace, entities, top_k)

        elif intent == QueryIntent.FIND_FLOW:
            result = self._retrieve_flow(query, namespace, top_k)

        elif intent == QueryIntent.PARALLEL_STEPS:
            result = self._retrieve_parallel_steps(query, namespace, top_k)

        elif intent == QueryIntent.FIND_DEPENDENCIES:
            result = self._retrieve_dependencies(query, namespace, entities, top_k)

        else:
            # Default: semantic search
            result = self._retrieve_semantic(query, namespace, top_k)

        result.retrieval_time = time.time() - start_time
        result.total_results = len(result.vector_results) + len(result.graph_results)

        return result

    def _retrieve_semantic(
        self,
        query: str,
        namespace: str,
        top_k: int,
    ) -> RetrievalResult:
        """Semantic vector search."""
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)

        # Search Qdrant
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
        )

        return RetrievalResult(vector_results=vector_results)

    def _retrieve_function(
        self,
        query: str,
        namespace: str,
        entities: Dict[str, Any],
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve function with context."""
        # First try vector search
        query_embedding = self.embedding_service.generate_embedding(query)
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
            filters={"code_unit_type": "function"},
        )

        # If we have a specific function name, get graph context
        graph_results = []
        if "name" in entities and vector_results:
            function_id = vector_results[0]["id"]

            # Get function context (what it calls, who calls it)
            context_query = queries.GET_FUNCTION_CONTEXT
            context = self.neo4j_client.execute_query(
                context_query,
                {"function_id": function_id, "namespace": namespace}
            )

            if context:
                graph_results = context

        return RetrievalResult(
            vector_results=vector_results,
            graph_results=graph_results,
        )

    def _retrieve_class(
        self,
        query: str,
        namespace: str,
        entities: Dict[str, Any],
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve class with hierarchy."""
        # Vector search for class
        query_embedding = self.embedding_service.generate_embedding(query)
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
            filters={"code_unit_type": "class"},
        )

        # Get class hierarchy from graph
        graph_results = []
        if vector_results:
            hierarchy_query = queries.FIND_CLASS_HIERARCHY
            hierarchy = self.neo4j_client.execute_query(
                hierarchy_query,
                {"namespace": namespace}
            )
            graph_results = hierarchy

        return RetrievalResult(
            vector_results=vector_results,
            graph_results=graph_results,
        )

    def _retrieve_usage(
        self,
        query: str,
        namespace: str,
        entities: Dict[str, Any],
        top_k: int,
    ) -> RetrievalResult:
        """Find usage/callers of a function."""
        # This is primarily a graph operation
        graph_results = []

        # Use search to find the function first
        if "name" in entities:
            search_query = queries.SEARCH_BY_NAME
            matches = self.neo4j_client.execute_query(
                search_query,
                {
                    "namespace": namespace,
                    "search_term": entities["name"],
                    "limit": 5
                }
            )

            if matches:
                # Find what calls this function
                function_id = matches[0]["id"]

                context_query = queries.GET_FUNCTION_CONTEXT
                context = self.neo4j_client.execute_query(
                    context_query,
                    {"function_id": function_id, "namespace": namespace}
                )

                graph_results = context

        return RetrievalResult(graph_results=graph_results)

    def _retrieve_call_chain(
        self,
        query: str,
        namespace: str,
        entities: Dict[str, Any],
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve call chain/stack."""
        graph_results = []

        if "name" in entities:
            # Find the starting function
            search_query = queries.SEARCH_BY_NAME
            matches = self.neo4j_client.execute_query(
                search_query,
                {
                    "namespace": namespace,
                    "search_term": entities["name"],
                    "limit": 1
                }
            )

            if matches:
                start_id = matches[0]["id"]

                # Find call chains
                call_chain_query = queries.FIND_CALL_CHAIN
                chains = self.neo4j_client.execute_query(
                    call_chain_query,
                    {
                        "start_id": start_id,
                        "namespace": namespace,
                        "max_depth": 5,
                        "limit": top_k
                    }
                )

                graph_results = chains

        return RetrievalResult(graph_results=graph_results)

    def _retrieve_flow(
        self,
        query: str,
        namespace: str,
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve execution flow information."""
        # Vector search for flow documents
        query_embedding = self.embedding_service.generate_embedding(query)
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
        )

        # Also search graph for ExecutionFlow nodes
        flow_query = """
        MATCH (flow:ExecutionFlow)
        WHERE flow.namespace = $namespace
        RETURN properties(flow) as flow
        LIMIT $limit
        """

        graph_results = self.neo4j_client.execute_query(
            flow_query,
            {"namespace": namespace, "limit": top_k}
        )

        return RetrievalResult(
            vector_results=vector_results,
            graph_results=graph_results,
        )

    def _retrieve_parallel_steps(
        self,
        query: str,
        namespace: str,
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve parallel execution opportunities."""
        # Search for flow documents
        query_embedding = self.embedding_service.generate_embedding(query)
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
        )

        # Get parallel steps from graph
        parallel_query = """
        MATCH (step:Step)-[:PARALLEL_WITH]->(parallel:Step)
        WHERE step.namespace = $namespace
        RETURN step.step_number as step,
               step.description as description,
               collect(parallel.step_number) as parallel_with
        ORDER BY step.step_number
        LIMIT $limit
        """

        graph_results = self.neo4j_client.execute_query(
            parallel_query,
            {"namespace": namespace, "limit": top_k}
        )

        return RetrievalResult(
            vector_results=vector_results,
            graph_results=graph_results,
        )

    def _retrieve_dependencies(
        self,
        query: str,
        namespace: str,
        entities: Dict[str, Any],
        top_k: int,
    ) -> RetrievalResult:
        """Retrieve dependency information."""
        # Vector search for context
        query_embedding = self.embedding_service.generate_embedding(query)
        vector_results = self.qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=top_k,
        )

        # Get dependencies from graph
        deps_query = """
        MATCH (n)-[:DEPENDS_ON]->(dep)
        WHERE n.namespace = $namespace
        RETURN n.name as name,
               collect(dep.name) as dependencies
        LIMIT $limit
        """

        graph_results = self.neo4j_client.execute_query(
            deps_query,
            {"namespace": namespace, "limit": top_k}
        )

        return RetrievalResult(
            vector_results=vector_results,
            graph_results=graph_results,
        )


def get_hybrid_retriever() -> HybridRetriever:
    """Get hybrid retriever instance."""
    return HybridRetriever()
