# FlowRAG - Hybrid GraphRAG System

A production-ready Graph RAG (Retrieval-Augmented Generation) system combining graph databases with vector search for intelligent code understanding. FlowRAG enables semantic code search and execution flow tracing through a hybrid retrieval architecture.

## Overview

FlowRAG combines three powerful capabilities:
- **Vector Search** (Qdrant) - Semantic similarity for finding conceptually related code
- **Graph Traversal** (Neo4j) - Structural relationships and execution flow tracing
- **LLM Integration** (OpenAI/Anthropic) - Natural language understanding and explanations

**Production Status**: Fully validated with comprehensive test suite including 25-step CI/CD pipeline demonstration.

## Architecture

This project is organized following agent-based architecture principles:

```
graph-rag-backend/
├── ingestion/          # Ingestion Agent - Data parsing and loading
│   ├── parsers/        # Code parsers (Python, JavaScript, etc.)
│   ├── chunkers/       # Document chunking strategies
│   └── loaders/        # Data loaders for Neo4j and Qdrant
├── databases/          # Database Agent - Schema and query management
│   ├── neo4j/          # Neo4j schema, queries, migrations
│   └── qdrant/         # Qdrant collections and configurations
├── orchestrator/       # Orchestrator Agent - Query routing and coordination
│   ├── router/         # Intent classification and routing
│   ├── retrieval/      # Retrieval strategies
│   └── context/        # Context assembly logic
├── agents/             # Model Agent - LLM/SLM integration
│   ├── slm/            # Small Language Model (Gemma 270M)
│   └── llm/            # Large Language Model integration
├── api/                # API Agent - External interfaces
│   ├── endpoints/      # FastAPI route handlers
│   ├── middleware/     # Authentication, rate limiting
│   └── schemas/        # Pydantic models
├── tests/              # Testing Agent - Quality assurance
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── e2e/            # End-to-end tests
├── docs/               # Documentation Agent - Technical documentation
│   ├── architecture/   # Architecture decision records
│   ├── api/            # API reference
│   └── guides/         # Developer guides
├── infra/              # Infrastructure Agent - Deployment
│   ├── docker/         # Dockerfile and compose
│   └── terraform/      # Infrastructure as code
├── config/             # Configuration files
└── scripts/            # Utility scripts
```

## Key Features

### Core Capabilities
- **Hybrid GraphRAG**: Combines vector similarity search with graph traversal for comprehensive code understanding
- **Semantic Code Search**: Find conceptually related code with 50-57% similarity scores using OpenAI embeddings (1536D)
- **Execution Flow Tracing**: Trace function calls and dependencies through Neo4j graph relationships
- **Multi-language Support**: Python and JavaScript parsing with AST-based code analysis
- **Real-time Embeddings**: OpenAI text-embedding-3-small for accurate semantic understanding

### Web UI
- **Interactive Testing**: Beautiful gradient UI for testing semantic search and flow analysis
- **Two Search Modes**:
  - Semantic Search: Natural language queries with auto-namespace detection
  - Flow Analysis: Trace execution flows through specific namespaces
- **Live LLM Responses**: Real-time GPT-4 powered explanations with code highlighting

### Databases & Architecture
- **Neo4j Graph Database**: Stores code structure (classes, methods, modules) and relationships (CONTAINS, CALLS)
- **Qdrant Vector Database**: Stores 1536-dimensional OpenAI embeddings for semantic search
- **Redis Caching**: Optional caching layer for improved performance
- **FastAPI Backend**: Production-ready REST API with streaming support

### Validated Test Suite
- **25-Step CI/CD Pipeline Test**: Comprehensive demonstration with 119 code units, 104 relationships
- **Multiple Test Scenarios**: Hybrid RAG, LLM integration, graph-only, full RAG tests
- **Production Data**: Real OpenAI embeddings and validated results

## Quick Start

### Prerequisites

- **Python 3.11+** (tested with Python 3.13)
- **Docker and Docker Compose** - For running databases
- **OpenAI API Key** - For embeddings and GPT-4
- **Anthropic API Key** (optional) - For Claude integration

### Installation

#### Step 1: Clone and Setup

```bash
cd /path/to/your/workspace
git clone <your-repo-url> flowrag-master
cd flowrag-master
```

#### Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here
NEO4J_PASSWORD=your-secure-password

# Optional
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
SECRET_KEY=your-secret-key-here
```

#### Step 3: Start Databases

```bash
docker-compose up -d
```

This starts:
- **Neo4j** (Graph Database)
  - Web UI: http://localhost:7474
  - Bolt: bolt://localhost:7687
- **Qdrant** (Vector Database)
  - API: http://localhost:6333
  - Dashboard: http://localhost:6333/dashboard
- **Redis** (Cache) - Port 6379

Wait for services to be ready:
```bash
# Check Neo4j
docker logs flowrag-neo4j

# Check Qdrant
curl http://localhost:6333/healthz
```

#### Step 4: Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # or use poetry install
```

#### Step 5: Run Comprehensive Test

Verify the entire system with the validated 25-step CI/CD pipeline test:

```bash
source venv/bin/activate
export DEBUG=true
python3 scripts/test_25step_graphrag.py
```

Expected output:
- 119 nodes created in Neo4j
- 119 embeddings in Qdrant (1536D OpenAI vectors)
- Semantic search queries with 50-57% similarity
- Flow analysis identifying all 25 steps
- LLM-generated comprehensive explanations

#### Step 6: Launch Web UI

```bash
source venv/bin/activate
export DEBUG=true
python3 ui/app.py
```

Access the UI at: **http://localhost:8000**

**Web UI Features**:
- **Semantic Search Tab**: Ask natural language questions (auto-detects namespace)
  - Example: "How does the system scan for security vulnerabilities?"
- **Flow Analysis Tab**: Trace execution flows (requires namespace)
  - Use namespace from test output (e.g., `pipeline_25step_1762675147`)

### Quick Validation

After running the 25-step test, validate data in databases:

**Check Qdrant**:
```bash
curl -X POST http://localhost:6333/collections/pipeline_25step_code/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

**Check Neo4j**:
Open http://localhost:7474 and run:
```cypher
MATCH (n) WHERE n.namespace STARTS WITH 'pipeline_25step'
RETURN count(n) as total_nodes
```

## Test Suite

FlowRAG includes a comprehensive test suite demonstrating all capabilities:

### Available Test Scripts

1. **`test_25step_graphrag.py`** - **Recommended** comprehensive test
   - Creates 25-step CI/CD pipeline with 4 modules
   - Real OpenAI embeddings (1536D)
   - Tests semantic search + flow analysis
   - Preserves data for UI testing
   - **Expected**: 119 nodes, 104 relationships, 50-57% similarity scores

2. **`test_llm_graphrag.py`** - LLM integration test
   - Deployment orchestrator example
   - Tests GPT-4 powered explanations
   - Flow-based queries with graph traversal

3. **`test_hybrid_rag.py`** - Hybrid retrieval test
   - Combines vector search + graph expansion
   - Demonstrates both retrieval modes
   - Uses simple embeddings (fast)

4. **`test_graph_only.py`** - Graph database only
   - Tests Neo4j schema and queries
   - No vector search

5. **`test_full_rag.py`** - Complete RAG pipeline
   - End-to-end test with all components

### Running Tests

```bash
# Comprehensive 25-step test (recommended)
source venv/bin/activate
export DEBUG=true
python3 scripts/test_25step_graphrag.py

# Quick hybrid test
python3 scripts/test_hybrid_rag.py

# LLM integration test
python3 scripts/test_llm_graphrag.py
```

## Usage Examples

### Using the Web UI (Recommended)

The easiest way to use FlowRAG is through the web interface:

```bash
source venv/bin/activate
export DEBUG=true
python3 ui/app.py
```

Open http://localhost:8000 and use:
- **Semantic Search**: Natural language queries about code
- **Flow Analysis**: Trace execution flows (requires namespace from test output)

### Programmatic Usage (Python)

```python
from databases.neo4j import Neo4jClient
from databases.qdrant import QdrantClient
from ingestion.parsers import PythonParser
from ingestion.loaders import Neo4jLoader, QdrantLoader
from openai import OpenAI

# Initialize clients
neo4j = Neo4jClient()
qdrant = QdrantClient(host="localhost", port=6333)
openai_client = OpenAI(api_key="your-key")

# Parse code
parser = PythonParser()
parse_result = parser.parse_string(code_content, "my_namespace", "example.py")

# Load to Neo4j
neo4j_loader = Neo4jLoader(neo4j)
neo4j_loader.load_parse_result(parse_result)

# Create embeddings and load to Qdrant
embedding_response = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input="code snippet text"
)
embedding = embedding_response.data[0].embedding

# Query semantic search
results = qdrant.search(
    collection_name="my_collection",
    query_vector=query_embedding,
    limit=5
)

# Query graph
flow = neo4j.execute_query("""
    MATCH (m:Method {namespace: $namespace, name: $method_name})
    MATCH path = (m)-[:CALLS*1..3]->(called)
    RETURN path
""", {"namespace": "my_namespace", "method_name": "execute_pipeline"})
```

## API Endpoints

### Ingestion
- `POST /api/v1/ingest/file` - Ingest a single file
- `POST /api/v1/ingest/directory` - Ingest a directory recursively
- `DELETE /api/v1/ingest/namespace` - Delete all data for a namespace

### Query
- `POST /api/v1/query` - Query codebase (non-streaming)
- `POST /api/v1/query/stream` - Query codebase (streaming SSE)

### Flow Analysis
- `POST /api/v1/flows/analyze` - Analyze execution flow
- `POST /api/v1/flows/parallelization` - Find parallelization opportunities

### Health
- `GET /health` - Health check
- `GET /` - API info

Full API documentation: http://localhost:8000/api/v1/docs

## Validated Test Results

The FlowRAG system has been thoroughly tested with production data. Here are the validated results from the 25-step CI/CD pipeline test:

### Database Storage
- **Neo4j**: 119 nodes, 104 relationships
  - Node types: Module, Class, Method
  - Relationships: CONTAINS, CALLS
  - Namespaces: `pipeline_25step_*` for isolation

- **Qdrant**: 119 embeddings
  - Vector size: 1536 dimensions (OpenAI text-embedding-3-small)
  - Collection: `pipeline_25step_code`
  - Real production embeddings, not mock data

### Search Performance
- **Semantic Search**: 50-57% similarity scores
  - Query: "How does the system scan for security vulnerabilities?"
  - Top result: `step_06_security_scan()` - 57.2% similarity
  - Accurate semantic understanding

- **Flow Analysis**: Successfully traced all 25 pipeline steps
  - Entry point: `execute_pipeline()`
  - Complete call graph traversal
  - LLM-generated comprehensive explanations

### Test Data
The test creates a realistic 25-step CI/CD pipeline with:
1. **Phase 1: Code Validation** (Steps 1-3)
   - Checkout, syntax validation, linting
2. **Phase 2: Testing** (Steps 4-7)
   - Unit tests, integration tests, coverage, security scan
3. **Phase 3: Build** (Steps 8-11)
   - Docker build, artifact creation, tagging, registry push
4. **Phase 4: Deployment** (Steps 12-18)
   - Staging, integration tests, smoke tests, rollback capability
5. **Phase 5: Production** (Steps 19-25)
   - Production deployment, monitoring, health checks, notifications

All steps are indexed, searchable, and traceable through both vector similarity and graph relationships.

## Technology Stack

### Core Components
- **Python 3.11+** - Main language
- **Neo4j** - Graph database for code structure
- **Qdrant** - Vector database for embeddings
- **OpenAI** - GPT-4 (answers) + text-embedding-3-small (embeddings)
- **FastAPI** - REST API framework
- **Redis** - Optional caching layer

### Parsing & Analysis
- **Python AST** - Python code parsing
- **Tree-sitter** - JavaScript parsing (coming soon)
- **Pydantic** - Data validation

### Development
- **Docker Compose** - Database orchestration
- **pytest** - Testing framework
- **uvicorn** - ASGI server

## Development

### Running Tests

```bash
# Comprehensive 25-step test
python3 scripts/test_25step_graphrag.py

# Unit tests (if available)
pytest tests/unit/

# Integration tests
pytest tests/integration/
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy .
```

## Troubleshooting

### Common Issues

**1. Qdrant shows "unhealthy" status**
```bash
docker logs flowrag-qdrant
# Wait a few more seconds, functionality usually works despite status
```

**2. DEBUG environment variable validation error**
```bash
# Always export DEBUG=true before running Python scripts
export DEBUG=true
python3 scripts/test_25step_graphrag.py
```

**3. Neo4j authentication failed**
```bash
# Check password in .env matches NEO4J_PASSWORD
# Default: "your-password-here"
```

**4. OpenAI API rate limits**
```bash
# The 25-step test creates 119 embeddings
# Ensure you have sufficient OpenAI API quota
```

**5. Web UI returns 404 or errors**
```bash
# Make sure you're in the correct directory
cd /path/to/flowrag-master
source venv/bin/activate
export DEBUG=true
python3 ui/app.py
```

### Database Access

**Neo4j Web UI**: http://localhost:7474
- Username: `neo4j`
- Password: (from `.env` file)

**Qdrant Dashboard**: http://localhost:6333/dashboard

**Query Neo4j**:
```cypher
// Show all namespaces
MATCH (n) RETURN DISTINCT n.namespace

// Count nodes by type
MATCH (n) RETURN labels(n), count(n)

// Show a specific pipeline
MATCH (n) WHERE n.namespace = 'pipeline_25step_1762675147'
RETURN n LIMIT 25
```

**Query Qdrant**:
```bash
# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/pipeline_25step_code
```

## Project Structure

```
flowrag-master/
├── agents/              # LLM/SLM agents for intent and response
├── api/                 # FastAPI REST endpoints
├── config/              # Settings and configuration
├── databases/           # Neo4j and Qdrant clients
├── docs/                # Documentation
├── ingestion/           # Code parsers and data loaders
│   ├── parsers/         # Python, JavaScript parsers
│   ├── chunkers/        # Document chunking
│   └── loaders/         # Neo4j and Qdrant loaders
├── orchestrator/        # Query routing and hybrid retrieval
│   ├── router/          # Intent classification
│   ├── retrieval/       # Hybrid retrieval strategies
│   ├── context/         # Context assembly
│   └── flow/            # Flow analysis
├── scripts/             # Test scripts
│   ├── test_25step_graphrag.py    # Recommended comprehensive test
│   ├── test_llm_graphrag.py       # LLM integration test
│   └── test_hybrid_rag.py         # Hybrid retrieval test
├── tests/               # Unit and integration tests
├── ui/                  # Web UI
│   ├── app.py           # FastAPI backend
│   └── index.html       # Frontend
├── docker-compose.yml   # Database orchestration
├── pyproject.toml       # Python dependencies
└── .env                 # Configuration (API keys)
```

## Future Enhancements

- [ ] Support for more languages (Java, Go, Rust, C++)
- [ ] Real-time code ingestion via file watchers
- [ ] Multi-repository support with cross-repo queries
- [ ] Advanced flow analysis (parallel execution detection)
- [ ] GraphQL API alongside REST
- [ ] Persistent LLM conversation context
- [ ] Code change tracking and diff analysis
- [ ] Team collaboration features

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with:
- [Neo4j](https://neo4j.com/) - Graph database
- [Qdrant](https://qdrant.tech/) - Vector database
- [OpenAI](https://openai.com/) - Embeddings and LLM
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Anthropic Claude](https://anthropic.com/) - Alternative LLM option

---

**Need help?** Check the [docs/](docs/) folder or open an issue on GitHub.
