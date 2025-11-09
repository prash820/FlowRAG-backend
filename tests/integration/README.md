# Integration Tests

Integration tests for FlowRAG that test the complete pipeline with real databases.

## Prerequisites

Before running integration tests, ensure all services are running:

```bash
# Start all services
docker-compose up -d

# Verify services are healthy
docker-compose ps
curl http://localhost:8000/health
```

## Running Tests

### Run all integration tests

```bash
poetry run pytest tests/integration/
```

### Run specific test file

```bash
# Test ingestion pipeline
poetry run pytest tests/integration/test_ingestion.py

# Test query pipeline
poetry run pytest tests/integration/test_query.py

# Test API endpoints
poetry run pytest tests/integration/test_api.py
```

### Run specific test class or function

```bash
# Run specific test class
poetry run pytest tests/integration/test_ingestion.py::TestIngestionPipeline

# Run specific test function
poetry run pytest tests/integration/test_ingestion.py::TestIngestionPipeline::test_parse_python_file
```

### Run with verbose output

```bash
poetry run pytest tests/integration/ -v
```

### Run with coverage

```bash
poetry run pytest tests/integration/ --cov --cov-report=html
```

The coverage report will be available at `htmlcov/index.html`.

## Test Structure

### test_ingestion.py

Tests the ingestion pipeline:
- Parsing Python files
- Loading into Neo4j
- Loading into Qdrant
- Complete ingestion flow
- Multi-file ingestion
- Edge cases (empty files, syntax errors, overwrites)

### test_query.py

Tests the query pipeline:
- Query orchestration
- Intent classification
- Context assembly
- Retrieval strategies
- Deduplication and ranking

### test_api.py

Tests API endpoints:
- Health checks
- File and directory ingestion
- Query endpoints (streaming and non-streaming)
- Flow analysis
- Error handling
- Namespace management

## Fixtures

Common fixtures are defined in `conftest.py`:

- `settings` - Application settings
- `neo4j_client` - Neo4j database client
- `qdrant_client` - Qdrant vector database client
- `embedding_service` - OpenAI embedding service
- `test_namespace` - Isolated test namespace (auto-cleanup)
- `temp_code_dir` - Temporary directory with sample code files
- `neo4j_loader` - Neo4j loader instance
- `qdrant_loader` - Qdrant loader instance
- `orchestrator` - Orchestration controller instance

## Cleanup

Tests automatically clean up after themselves by:

1. Using unique namespaces per test
2. Deleting all test data in the namespace after each test
3. Removing temporary files and directories

## Troubleshooting

### Tests fail with connection errors

Ensure all services are running:
```bash
docker-compose ps
```

Check service health:
```bash
curl http://localhost:8000/health
```

### Tests timeout

Increase timeout in `pytest.ini`:
```ini
timeout = 600
```

Or run specific test with custom timeout:
```bash
pytest tests/integration/test_api.py --timeout=600
```

### Database contains old test data

Manually clean up:
```bash
# Clean Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p your-password "MATCH (n) WHERE n.namespace STARTS WITH 'test_' DETACH DELETE n"

# Clean Qdrant
curl -X POST 'http://localhost:6333/collections/code_embeddings/points/delete' \
  -H 'Content-Type: application/json' \
  -d '{"filter": {"must": [{"key": "namespace", "match": {"text": "test_"}}]}}'
```

## CI/CD Integration

For CI/CD pipelines, use Docker Compose to start services:

```yaml
# GitHub Actions example
- name: Start services
  run: docker-compose up -d

- name: Wait for services
  run: |
    timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

- name: Run integration tests
  run: poetry run pytest tests/integration/
```
