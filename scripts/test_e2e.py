#!/usr/bin/env python3
"""
End-to-end test script for FlowRAG.

Tests the complete pipeline:
1. Health check
2. Ingest sample code
3. Query the codebase
4. Analyze execution flows
"""

import requests
import json
import time
from pathlib import Path
import sys

# Configuration
API_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
NAMESPACE = "test_e2e"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def print_step(message):
    """Print test step."""
    print(f"\n{YELLOW}>>> {message}{RESET}")


def print_success(message):
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message):
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def test_health_check():
    """Test health check endpoint."""
    print_step("Testing health check...")

    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()

        data = response.json()
        print_success(f"Health check passed: {data['status']}")
        print(f"  Neo4j: {data['services'].get('neo4j', 'unknown')}")
        print(f"  Qdrant: {data['services'].get('qdrant', 'unknown')}")
        return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def create_sample_file():
    """Create a sample Python file for testing."""
    print_step("Creating sample Python file...")

    sample_code = '''"""Sample module for testing FlowRAG."""

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
'''

    # Create temp directory
    temp_dir = Path("/tmp/flowrag_test")
    temp_dir.mkdir(exist_ok=True)

    sample_file = temp_dir / "sample.py"
    sample_file.write_text(sample_code)

    print_success(f"Sample file created: {sample_file}")
    return str(sample_file)


def test_ingest_file(file_path):
    """Test file ingestion."""
    print_step(f"Testing file ingestion: {file_path}")

    try:
        payload = {
            "file_path": file_path,
            "namespace": NAMESPACE,
            "overwrite": True
        }

        response = requests.post(
            f"{API_BASE_URL}{API_PREFIX}/ingest/file",
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        print_success("File ingestion successful!")
        print(f"  Files processed: {data['files_processed']}")
        print(f"  Nodes created: {data['nodes_created']}")
        print(f"  Relationships created: {data['relationships_created']}")
        print(f"  Vectors stored: {data['vectors_stored']}")
        print(f"  Processing time: {data['processing_time']:.2f}s")
        return True
    except Exception as e:
        print_error(f"File ingestion failed: {e}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response.text}")
        return False


def test_query(query_text):
    """Test query endpoint."""
    print_step(f"Testing query: '{query_text}'")

    try:
        payload = {
            "query": query_text,
            "namespace": NAMESPACE,
            "max_results": 5,
            "temperature": 0.2
        }

        response = requests.post(
            f"{API_BASE_URL}{API_PREFIX}/query",
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        data = response.json()
        print_success("Query successful!")
        print(f"  Intent: {data['intent']} (confidence: {data['intent_confidence']:.2f})")
        print(f"  Sources: {data['sources_count']}")
        print(f"  Model: {data['model']}")
        print(f"  Tokens used: {data.get('tokens_used', 'N/A')}")
        print(f"  Total time: {data['total_time']:.2f}s")
        print(f"\n  Answer:\n  {data['answer'][:200]}...")
        return True
    except Exception as e:
        print_error(f"Query failed: {e}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response.text}")
        return False


def test_cleanup():
    """Test cleanup by deleting the namespace."""
    print_step(f"Cleaning up namespace: {NAMESPACE}")

    try:
        payload = {
            "namespace": NAMESPACE,
            "confirm": True
        }

        response = requests.request(
            "DELETE",
            f"{API_BASE_URL}{API_PREFIX}/ingest/namespace",
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        print_success("Cleanup successful!")
        print(f"  Nodes deleted: {data['nodes_deleted']}")
        print(f"  Vectors deleted: {data['vectors_deleted']}")
        return True
    except Exception as e:
        print_error(f"Cleanup failed: {e}")
        if hasattr(e, 'response'):
            print(f"  Response: {e.response.text}")
        return False


def main():
    """Run all tests."""
    print(f"{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}FlowRAG End-to-End Test Suite{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")

    results = []

    # Test 1: Health check
    results.append(("Health Check", test_health_check()))

    if not results[0][1]:
        print_error("\nHealth check failed. Make sure all services are running.")
        print("Run: docker-compose up -d")
        sys.exit(1)

    # Test 2: Create sample file
    sample_file = create_sample_file()

    # Test 3: Ingest file
    results.append(("File Ingestion", test_ingest_file(sample_file)))

    # Give some time for indexing
    if results[-1][1]:
        print("\nWaiting 2 seconds for indexing...")
        time.sleep(2)

    # Test 4: Query tests
    if results[-1][1]:
        queries = [
            "What does the process_data function do?",
            "How is data cleaned?",
            "Show me the DataProcessor class",
        ]

        for query in queries:
            result = test_query(query)
            results.append((f"Query: {query[:30]}...", result))
            if result:
                time.sleep(1)  # Rate limiting

    # Test 5: Cleanup
    results.append(("Cleanup", test_cleanup()))

    # Print summary
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}Test Summary{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {test_name}")

    print(f"\n{YELLOW}Total: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}✓ All tests passed!{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}✗ Some tests failed{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
