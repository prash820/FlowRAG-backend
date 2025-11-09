"""
Integration tests for ingestion pipeline.
Tests: parsing → loading → verification
"""

import pytest
from pathlib import Path

from ingestion.parsers import get_parser
from ingestion.loaders.neo4j_loader import Neo4jLoader
from ingestion.loaders.qdrant_loader import QdrantLoader
from databases.neo4j.client import Neo4jClient
from databases.qdrant.client import QdrantClient
from databases.neo4j.schema import NodeLabel


class TestIngestionPipeline:
    """Test complete ingestion pipeline."""

    def test_parse_python_file(self, sample_code_file: Path, test_namespace: str):
        """Test parsing a Python file."""
        # Get parser
        parser = get_parser("python")
        assert parser is not None

        # Parse file
        result = parser.parse_file(str(sample_code_file), test_namespace)

        # Verify parse result
        assert result is not None
        assert result.namespace == test_namespace
        assert len(result.modules) > 0
        assert len(result.functions) > 0
        assert len(result.classes) > 0

        # Check specific functions
        function_names = [f.name for f in result.functions]
        assert "process_data" in function_names
        assert "clean_data" in function_names
        assert "validate_data" in function_names
        assert "transform_data" in function_names

        # Check class
        assert len(result.classes) == 1
        assert result.classes[0].name == "DataProcessor"

    def test_load_into_neo4j(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        neo4j_client: Neo4jClient
    ):
        """Test loading parsed code into Neo4j."""
        # Parse file
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)

        # Load into Neo4j
        load_result = neo4j_loader.load_parse_result(result)

        # Verify load result
        assert load_result["nodes_created"] > 0
        assert load_result["relationships_created"] > 0

        # Verify nodes exist in Neo4j
        query = """
        MATCH (n {namespace: $namespace})
        RETURN n, labels(n) as labels
        """
        nodes = neo4j_client.execute_query(query, {"namespace": test_namespace})
        assert len(nodes) > 0

        # Check for specific node types
        labels_found = set()
        for node in nodes:
            labels_found.update(node["labels"])

        assert NodeLabel.MODULE.value in labels_found
        assert NodeLabel.FUNCTION.value in labels_found
        assert NodeLabel.CLASS.value in labels_found

    def test_load_into_qdrant(
        self,
        sample_code_file: Path,
        test_namespace: str,
        qdrant_loader: QdrantLoader,
        qdrant_client: QdrantClient
    ):
        """Test loading embeddings into Qdrant."""
        # Parse file
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)

        # Load into Qdrant
        load_result = qdrant_loader.load_parse_result(result)

        # Verify load result
        assert load_result["vectors_stored"] > 0

        # Verify vectors exist in Qdrant
        # Search for any vector in namespace
        dummy_vector = [0.0] * 1536  # OpenAI embedding dimension
        search_results = qdrant_client.search(
            query_vector=dummy_vector,
            namespace=test_namespace,
            top_k=100
        )

        assert len(search_results) > 0

    def test_complete_ingestion_pipeline(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        qdrant_loader: QdrantLoader,
        neo4j_client: Neo4jClient,
        qdrant_client: QdrantClient
    ):
        """Test complete ingestion pipeline: parse → Neo4j → Qdrant."""
        # 1. Parse
        parser = get_parser("python")
        result = parser.parse_file(str(sample_code_file), test_namespace)

        # 2. Load into Neo4j
        neo4j_result = neo4j_loader.load_parse_result(result)

        # 3. Load into Qdrant
        qdrant_result = qdrant_loader.load_parse_result(result)

        # 4. Verify both databases have data
        assert neo4j_result["nodes_created"] > 0
        assert qdrant_result["vectors_stored"] > 0

        # 5. Verify we can query Neo4j for a specific function
        query = """
        MATCH (f:Function {namespace: $namespace, name: $name})
        RETURN f
        """
        functions = neo4j_client.execute_query(
            query,
            {"namespace": test_namespace, "name": "process_data"}
        )
        assert len(functions) == 1

        # 6. Verify function has relationships
        query = """
        MATCH (f:Function {namespace: $namespace, name: $name})-[r:CALLS]->(called)
        RETURN called.name as called_name
        """
        calls = neo4j_client.execute_query(
            query,
            {"namespace": test_namespace, "name": "process_data"}
        )
        assert len(calls) > 0

        called_names = [c["called_name"] for c in calls]
        assert "clean_data" in called_names
        assert "validate_data" in called_names
        assert "transform_data" in called_names


class TestMultiFileIngestion:
    """Test ingestion of multiple files."""

    def test_ingest_multiple_files(
        self,
        temp_code_dir: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        qdrant_loader: QdrantLoader,
        neo4j_client: Neo4jClient
    ):
        """Test ingesting multiple Python files."""
        parser = get_parser("python")

        total_nodes = 0
        total_vectors = 0

        # Ingest all Python files
        for py_file in temp_code_dir.glob("*.py"):
            # Parse
            result = parser.parse_file(str(py_file), test_namespace)

            # Load
            neo4j_result = neo4j_loader.load_parse_result(result)
            qdrant_result = qdrant_loader.load_parse_result(result)

            total_nodes += neo4j_result["nodes_created"]
            total_vectors += qdrant_result["vectors_stored"]

        # Verify
        assert total_nodes > 0
        assert total_vectors > 0

        # Check that both files are represented
        query = """
        MATCH (m:Module {namespace: $namespace})
        RETURN m.file_path as file_path
        """
        modules = neo4j_client.execute_query(query, {"namespace": test_namespace})

        file_paths = [m["file_path"] for m in modules]
        assert any("sample.py" in fp for fp in file_paths)
        assert any("utils.py" in fp for fp in file_paths)


class TestIngestionEdgeCases:
    """Test edge cases in ingestion."""

    def test_empty_file(self, test_namespace: str, temp_code_dir: Path):
        """Test ingesting an empty Python file."""
        empty_file = temp_code_dir / "empty.py"
        empty_file.write_text("")

        parser = get_parser("python")
        result = parser.parse_file(str(empty_file), test_namespace)

        # Should parse but create minimal nodes
        assert result is not None
        assert result.namespace == test_namespace
        assert len(result.functions) == 0
        assert len(result.classes) == 0

    def test_syntax_error_file(self, test_namespace: str, temp_code_dir: Path):
        """Test ingesting a file with syntax errors."""
        bad_file = temp_code_dir / "bad.py"
        bad_file.write_text("def broken_function(\n    # Missing closing parenthesis")

        parser = get_parser("python")

        # Should raise exception
        with pytest.raises(Exception):
            parser.parse_file(str(bad_file), test_namespace)

    def test_overwrite_namespace(
        self,
        sample_code_file: Path,
        test_namespace: str,
        neo4j_loader: Neo4jLoader,
        neo4j_client: Neo4jClient
    ):
        """Test overwriting data in an existing namespace."""
        parser = get_parser("python")

        # First ingestion
        result1 = parser.parse_file(str(sample_code_file), test_namespace)
        neo4j_loader.load_parse_result(result1)

        # Count nodes
        query = "MATCH (n {namespace: $namespace}) RETURN count(n) as count"
        count1 = neo4j_client.execute_query(query, {"namespace": test_namespace})[0]["count"]

        # Delete namespace
        delete_query = "MATCH (n {namespace: $namespace}) DETACH DELETE n"
        neo4j_client.execute_query(delete_query, {"namespace": test_namespace})

        # Second ingestion
        result2 = parser.parse_file(str(sample_code_file), test_namespace)
        neo4j_loader.load_parse_result(result2)

        # Count nodes again
        count2 = neo4j_client.execute_query(query, {"namespace": test_namespace})[0]["count"]

        # Should have same number of nodes
        assert count1 == count2
