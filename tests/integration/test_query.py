"""
Integration tests for query pipeline.
Tests: orchestration → retrieval → context → response
"""

import pytest
from pathlib import Path

from ingestion.parsers import get_parser
from ingestion.loaders.neo4j_loader import Neo4jLoader
from ingestion.loaders.qdrant_loader import QdrantLoader
from orchestrator.controller import OrchestrationController
from orchestrator.models import OrchestrationRequest
from orchestrator.router.intent_classifier import QueryIntent


class TestQueryPipeline:
    """Test complete query pipeline."""

    @pytest.fixture(autouse=True)
    def setup_data(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        qdrant_loader: QdrantLoader
    ):
        """Setup: Ingest sample data before each test."""
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)
        neo4j_loader.load_parse_result(result)
        qdrant_loader.load_parse_result(result)

    def test_orchestrate_function_query(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test orchestrating a function-finding query."""
        request = OrchestrationRequest(
            query="What does the process_data function do?",
            namespace=test_namespace,
            max_results=5
        )

        result = orchestrator.orchestrate(request)

        # Verify result
        assert result is not None
        assert result.intent in [QueryIntent.FIND_FUNCTION, QueryIntent.CODE_EXPLANATION]
        assert result.intent_confidence > 0.0
        assert result.context is not None
        assert len(result.context.items) > 0

        # Should find process_data function
        context_text = result.context.formatted_context.lower()
        assert "process_data" in context_text

    def test_orchestrate_class_query(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test orchestrating a class-finding query."""
        request = OrchestrationRequest(
            query="Show me the DataProcessor class",
            namespace=test_namespace,
            max_results=5
        )

        result = orchestrator.orchestrate(request)

        # Verify result
        assert result is not None
        assert result.intent in [QueryIntent.FIND_CLASS, QueryIntent.CODE_EXPLANATION]
        assert len(result.context.items) > 0

        # Should find DataProcessor class
        context_text = result.context.formatted_context.lower()
        assert "dataprocessor" in context_text

    def test_orchestrate_dependency_query(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test orchestrating a dependency query."""
        request = OrchestrationRequest(
            query="What functions does process_data call?",
            namespace=test_namespace,
            max_results=10
        )

        result = orchestrator.orchestrate(request)

        # Verify result
        assert result is not None
        assert result.context is not None
        assert len(result.context.items) > 0

        # Should include called functions
        context_text = result.context.formatted_context.lower()
        assert "clean_data" in context_text or "validate_data" in context_text or "transform_data" in context_text

    def test_orchestrate_semantic_search(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test semantic search via orchestrator."""
        request = OrchestrationRequest(
            query="How is data cleaned?",
            namespace=test_namespace,
            max_results=5
        )

        result = orchestrator.orchestrate(request)

        # Verify result
        assert result is not None
        assert len(result.context.items) > 0

        # Should find clean_data function through semantic search
        context_text = result.context.formatted_context.lower()
        assert "clean" in context_text

    def test_orchestrate_empty_namespace(
        self,
        orchestrator: OrchestrationController
    ):
        """Test querying an empty namespace."""
        request = OrchestrationRequest(
            query="What functions exist?",
            namespace="nonexistent_namespace",
            max_results=5
        )

        result = orchestrator.orchestrate(request)

        # Should still return result but with no context
        assert result is not None
        assert len(result.context.items) == 0


class TestIntentClassification:
    """Test intent classification in query pipeline."""

    @pytest.fixture(autouse=True)
    def setup_data(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        qdrant_loader: QdrantLoader
    ):
        """Setup: Ingest sample data before each test."""
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)
        neo4j_loader.load_parse_result(result)
        qdrant_loader.load_parse_result(result)

    def test_classify_find_function(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test classification of find_function intent."""
        queries = [
            "Find the process_data function",
            "Show me the clean_data function",
            "What does the validate_data function do?",
        ]

        for query in queries:
            request = OrchestrationRequest(
                query=query,
                namespace=test_namespace,
                max_results=5
            )
            result = orchestrator.orchestrate(request)

            # Intent should be find_function or code_explanation
            assert result.intent in [QueryIntent.FIND_FUNCTION, QueryIntent.CODE_EXPLANATION]

    def test_classify_find_class(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test classification of find_class intent."""
        queries = [
            "Show me the DataProcessor class",
            "Find the DataProcessor class",
            "What is the DataProcessor class?",
        ]

        for query in queries:
            request = OrchestrationRequest(
                query=query,
                namespace=test_namespace,
                max_results=5
            )
            result = orchestrator.orchestrate(request)

            # Intent should be find_class or code_explanation
            assert result.intent in [QueryIntent.FIND_CLASS, QueryIntent.CODE_EXPLANATION]


class TestContextAssembly:
    """Test context assembly in query pipeline."""

    @pytest.fixture(autouse=True)
    def setup_data(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        qdrant_loader: QdrantLoader
    ):
        """Setup: Ingest sample data before each test."""
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)
        neo4j_loader.load_parse_result(result)
        qdrant_loader.load_parse_result(result)

    def test_context_deduplication(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test that context items are deduplicated."""
        request = OrchestrationRequest(
            query="Tell me about data processing",
            namespace=test_namespace,
            max_results=10
        )

        result = orchestrator.orchestrate(request)

        # Check for duplicate IDs
        ids = [item.id for item in result.context.items]
        assert len(ids) == len(set(ids)), "Context should not have duplicate items"

    def test_context_ranking(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test that context items are ranked by relevance."""
        request = OrchestrationRequest(
            query="What does process_data do?",
            namespace=test_namespace,
            max_results=5
        )

        result = orchestrator.orchestrate(request)

        # Items should be ordered by score (descending)
        scores = [item.score for item in result.context.items if item.score is not None]
        if len(scores) > 1:
            assert scores == sorted(scores, reverse=True), "Context items should be ranked by score"

    def test_context_max_results(
        self,
        orchestrator: OrchestrationController,
        test_namespace: str
    ):
        """Test that max_results is respected."""
        max_results = 3
        request = OrchestrationRequest(
            query="Tell me about the code",
            namespace=test_namespace,
            max_results=max_results
        )

        result = orchestrator.orchestrate(request)

        # Should not exceed max_results
        assert len(result.context.items) <= max_results
