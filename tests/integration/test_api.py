"""
Integration tests for API endpoints.
Tests actual HTTP requests to the API.
"""

import pytest
import requests
from pathlib import Path
from typing import Generator

from config import get_settings


# Get settings
settings = get_settings()
API_BASE_URL = f"http://{settings.api_host}:{settings.api_port}"
API_PREFIX = settings.api_prefix


@pytest.fixture(scope="module")
def api_url() -> str:
    """Get API base URL."""
    return API_BASE_URL


@pytest.fixture(scope="module")
def test_namespace() -> Generator[str, None, None]:
    """Create and cleanup test namespace via API."""
    namespace = "test_api_integration"

    yield namespace

    # Cleanup: Delete namespace via API
    try:
        response = requests.request(
            "DELETE",
            f"{API_BASE_URL}{API_PREFIX}/ingest/namespace",
            json={"namespace": namespace, "confirm": True},
            timeout=30
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Warning: Failed to cleanup namespace via API: {e}")


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, api_url: str):
        """Test root endpoint."""
        response = requests.get(api_url, timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_health_endpoint(self, api_url: str):
        """Test health check endpoint."""
        response = requests.get(f"{api_url}/health", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data

        # Check service statuses
        services = data["services"]
        assert services.get("neo4j") == "healthy"
        assert services.get("qdrant") == "healthy"


class TestIngestEndpoints:
    """Test ingestion endpoints."""

    def test_ingest_file(
        self,
        api_url: str,
        test_namespace: str,
        sample_code_file: Path
    ):
        """Test file ingestion endpoint."""
        payload = {
            "file_path": str(sample_code_file),
            "namespace": test_namespace,
            "overwrite": True
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=60
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["files_processed"] == 1
        assert data["nodes_created"] > 0
        assert data["relationships_created"] > 0
        assert data["vectors_stored"] > 0
        assert "processing_time" in data

    def test_ingest_directory(
        self,
        api_url: str,
        test_namespace: str,
        temp_code_dir: Path
    ):
        """Test directory ingestion endpoint."""
        payload = {
            "directory_path": str(temp_code_dir),
            "namespace": test_namespace,
            "recursive": True,
            "file_patterns": ["*.py"],
            "overwrite": True
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/directory",
            json=payload,
            timeout=120
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["files_processed"] >= 2  # sample.py and utils.py
        assert data["nodes_created"] > 0
        assert data["vectors_stored"] > 0

    def test_ingest_nonexistent_file(self, api_url: str, test_namespace: str):
        """Test ingesting a file that doesn't exist."""
        payload = {
            "file_path": "/nonexistent/file.py",
            "namespace": test_namespace
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=30
        )

        # Should return error
        assert response.status_code in [400, 404]

    def test_delete_namespace(
        self,
        api_url: str,
        sample_code_file: Path
    ):
        """Test deleting a namespace."""
        # Create temporary namespace
        temp_namespace = "test_delete_namespace"

        # Ingest some data
        ingest_payload = {
            "file_path": str(sample_code_file),
            "namespace": temp_namespace
        }
        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=ingest_payload,
            timeout=60
        )
        assert response.status_code == 200

        # Delete namespace
        delete_payload = {
            "namespace": temp_namespace,
            "confirm": True
        }
        response = requests.request(
            "DELETE",
            f"{api_url}{API_PREFIX}/ingest/namespace",
            json=delete_payload,
            timeout=30
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["nodes_deleted"] > 0


class TestQueryEndpoints:
    """Test query endpoints."""

    @pytest.fixture(autouse=True)
    def setup_data(
        self,
        api_url: str,
        test_namespace: str,
        sample_code_file: Path
    ):
        """Setup: Ingest sample data before each test."""
        payload = {
            "file_path": str(sample_code_file),
            "namespace": test_namespace,
            "overwrite": True
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=60
        )
        assert response.status_code == 200

    def test_query_endpoint(self, api_url: str, test_namespace: str):
        """Test query endpoint (non-streaming)."""
        payload = {
            "query": "What does the process_data function do?",
            "namespace": test_namespace,
            "max_results": 5,
            "temperature": 0.2
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/query",
            json=payload,
            timeout=120
        )

        assert response.status_code == 200

        data = response.json()
        assert "answer" in data
        assert "intent" in data
        assert "intent_confidence" in data
        assert "sources_count" in data
        assert "model" in data
        assert "total_time" in data

        # Answer should mention process_data
        assert len(data["answer"]) > 0

    def test_query_stream_endpoint(self, api_url: str, test_namespace: str):
        """Test query streaming endpoint."""
        payload = {
            "query": "How is data cleaned?",
            "namespace": test_namespace,
            "max_results": 5,
            "stream": True
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/query/stream",
            json=payload,
            stream=True,
            timeout=120
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # Read chunks
        chunks = []
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    chunks.append(decoded[6:])  # Remove 'data: ' prefix

        # Should have received chunks
        assert len(chunks) > 0

    def test_query_empty_namespace(self, api_url: str):
        """Test querying an empty namespace."""
        payload = {
            "query": "What functions exist?",
            "namespace": "empty_namespace_test",
            "max_results": 5
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/query",
            json=payload,
            timeout=120
        )

        assert response.status_code == 200

        data = response.json()
        assert data["sources_count"] == 0


class TestFlowEndpoints:
    """Test flow analysis endpoints."""

    @pytest.fixture(autouse=True)
    def setup_data(
        self,
        api_url: str,
        test_namespace: str,
        sample_code_file: Path
    ):
        """Setup: Ingest sample data before each test."""
        payload = {
            "file_path": str(sample_code_file),
            "namespace": test_namespace,
            "overwrite": True
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=60
        )
        assert response.status_code == 200

    def test_analyze_flow_endpoint(self, api_url: str, test_namespace: str):
        """Test flow analysis endpoint."""
        payload = {
            "namespace": test_namespace,
            "flow_name": "data_processing"
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/flows/analyze",
            json=payload,
            timeout=60
        )

        # May not find flows in simple test data
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "flow_name" in data

    def test_parallelization_endpoint(self, api_url: str, test_namespace: str):
        """Test parallelization opportunities endpoint."""
        payload = {
            "namespace": test_namespace
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/flows/parallelization",
            json=payload,
            timeout=60
        )

        # May not find opportunities in simple test data
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test API error handling."""

    def test_invalid_json(self, api_url: str):
        """Test sending invalid JSON."""
        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        assert response.status_code == 422

    def test_missing_required_field(self, api_url: str):
        """Test missing required field in request."""
        payload = {
            # Missing file_path
            "namespace": "test"
        }

        response = requests.post(
            f"{api_url}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=10
        )

        assert response.status_code == 422

    def test_invalid_endpoint(self, api_url: str):
        """Test accessing invalid endpoint."""
        response = requests.get(
            f"{api_url}{API_PREFIX}/nonexistent",
            timeout=10
        )

        assert response.status_code == 404
