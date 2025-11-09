"""
Pytest fixtures for integration tests.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Generator, AsyncGenerator
import tempfile
import shutil

from databases.neo4j.client import Neo4jClient
from databases.qdrant.client import QdrantClient
from ingestion.embeddings import EmbeddingService
from ingestion.parsers import get_parser
from ingestion.loaders.neo4j_loader import Neo4jLoader
from ingestion.loaders.qdrant_loader import QdrantLoader
from orchestrator.controller import OrchestrationController
from config import get_settings


# Test namespace
TEST_NAMESPACE = "test_integration"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture(scope="session")
def neo4j_client(settings) -> Generator[Neo4jClient, None, None]:
    """Create Neo4j client for testing."""
    client = Neo4jClient()
    yield client
    # Cleanup is handled by test_namespace fixture


@pytest.fixture(scope="session")
def qdrant_client(settings) -> Generator[QdrantClient, None, None]:
    """Create Qdrant client for testing."""
    client = QdrantClient()
    yield client
    # Cleanup is handled by test_namespace fixture


@pytest.fixture(scope="session")
def embedding_service(settings) -> EmbeddingService:
    """Create embedding service for testing."""
    return EmbeddingService()


@pytest.fixture(scope="function")
def test_namespace(neo4j_client: Neo4jClient, qdrant_client: QdrantClient) -> Generator[str, None, None]:
    """Create and cleanup test namespace."""
    namespace = f"{TEST_NAMESPACE}_{id(neo4j_client)}"

    yield namespace

    # Cleanup: Delete all nodes in namespace
    try:
        query = """
        MATCH (n {namespace: $namespace})
        DETACH DELETE n
        """
        neo4j_client.execute_query(query, {"namespace": namespace})
    except Exception as e:
        print(f"Warning: Failed to cleanup Neo4j namespace {namespace}: {e}")

    # Cleanup: Delete vectors in namespace
    try:
        qdrant_client.delete_by_namespace(namespace)
    except Exception as e:
        print(f"Warning: Failed to cleanup Qdrant namespace {namespace}: {e}")


@pytest.fixture(scope="function")
def temp_code_dir() -> Generator[Path, None, None]:
    """Create temporary directory with sample code files."""
    temp_dir = Path(tempfile.mkdtemp(prefix="flowrag_test_"))

    # Create sample Python file
    sample_py = temp_dir / "sample.py"
    sample_py.write_text('''"""Sample module for testing."""

def process_data(data):
    """Process input data."""
    cleaned = clean_data(data)
    validated = validate_data(cleaned)
    return transform_data(validated)

def clean_data(data):
    """Clean the data."""
    return [item.strip() for item in data if item]

def validate_data(data):
    """Validate the data."""
    return [item for item in data if len(item) > 0]

def transform_data(data):
    """Transform the data."""
    return [item.upper() for item in data]

class DataProcessor:
    """Data processor class."""

    def __init__(self, config):
        """Initialize processor."""
        self.config = config

    def run(self, data):
        """Run the processing pipeline."""
        return process_data(data)
''')

    # Create another Python file with dependencies
    utils_py = temp_dir / "utils.py"
    utils_py.write_text('''"""Utility functions."""

import json
from typing import List, Dict

def load_config(path: str) -> Dict:
    """Load configuration from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)

def save_results(results: List, path: str) -> None:
    """Save results to JSON file."""
    with open(path, 'w') as f:
        json.dump(results, f, indent=2)

class Logger:
    """Simple logger class."""

    def __init__(self, name: str):
        self.name = name

    def log(self, message: str) -> None:
        """Log a message."""
        print(f"[{self.name}] {message}")
''')

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def neo4j_loader(neo4j_client: Neo4jClient) -> Neo4jLoader:
    """Create Neo4j loader for testing."""
    return Neo4jLoader(neo4j_client)


@pytest.fixture(scope="function")
def qdrant_loader(qdrant_client: QdrantClient, embedding_service: EmbeddingService) -> QdrantLoader:
    """Create Qdrant loader for testing."""
    return QdrantLoader(qdrant_client, embedding_service)


@pytest.fixture(scope="function")
def orchestrator(
    neo4j_client: Neo4jClient,
    qdrant_client: QdrantClient,
    embedding_service: EmbeddingService
) -> OrchestrationController:
    """Create orchestration controller for testing."""
    return OrchestrationController(
        neo4j_client=neo4j_client,
        qdrant_client=qdrant_client,
        embedding_service=embedding_service
    )


@pytest.fixture(scope="function")
def sample_code_file(temp_code_dir: Path) -> Path:
    """Get path to sample Python file."""
    return temp_code_dir / "sample.py"


@pytest.fixture(scope="function")
def utils_code_file(temp_code_dir: Path) -> Path:
    """Get path to utils Python file."""
    return temp_code_dir / "utils.py"
