# FlowRAG - Graph RAG Backend

A Graph RAG system with flow detection capabilities, built using autonomous AI agents following the Claude Code Agent specification.

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

## Features

- **Multi-source Ingestion**: Code repositories, trace files, documents, configurations
- **Graph Knowledge**: Neo4j for relationship modeling and traversal
- **Vector Search**: Qdrant for semantic similarity
- **Flow Detection**: Identify parallel and sequential execution patterns
- **Hybrid Retrieval**: Combines graph traversal with vector search
- **Local SLM**: Gemma 3 270M for intent classification
- **LLM Integration**: OpenAI/Anthropic for answer generation

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker and Docker Compose** - For running databases
- **Poetry** - Python dependency management
- **OpenAI API Key** - For embeddings and LLM (or Anthropic)

### Installation

#### Option 1: Using Docker Compose (Recommended)

1. **Clone the repository:**
```bash
git clone https://github.com/prash820/privateLLM-backend.git graph-rag-backend
cd graph-rag-backend
```

2. **Set up environment:**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=sk-your-key-here
NEO4J_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key-here
```

3. **Start all services:**
```bash
docker-compose up -d
```

This starts:
- Neo4j (Graph Database) - http://localhost:7474
- Qdrant (Vector Database) - http://localhost:6333
- Redis (Cache) - Port 6379
- FastAPI Backend - http://localhost:8000

4. **Check health:**
```bash
curl http://localhost:8000/health
```

5. **Access API documentation:**
Open http://localhost:8000/api/v1/docs in your browser

#### Option 2: Local Development

1. **Clone and setup:**
```bash
git clone https://github.com/prash820/privateLLM-backend.git graph-rag-backend
cd graph-rag-backend
```

2. **Install dependencies:**
```bash
poetry install
```

3. **Set up environment:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Start databases only:**
```bash
docker-compose up -d neo4j qdrant redis
```

5. **Initialize databases:**
```bash
poetry run python scripts/init_databases.py
```

6. **Start the API server:**
```bash
poetry run python -m api.main
```

Or with auto-reload:
```bash
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

### Quick Test

Run the end-to-end test script to verify everything works:

```bash
poetry run python scripts/test_e2e.py
```

This will:
1. Check service health
2. Ingest a sample Python file
3. Query the codebase
4. Clean up test data

## Usage Examples

### 1. Ingest Code

**Ingest a single file:**
```bash
curl -X POST http://localhost:8000/api/v1/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/path/to/your/code.py",
    "namespace": "my_project"
  }'
```

**Ingest a directory:**
```bash
curl -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/path/to/your/project",
    "namespace": "my_project",
    "recursive": true,
    "file_patterns": ["*.py", "*.js"]
  }'
```

### 2. Query Your Codebase

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does the authentication work?",
    "namespace": "my_project"
  }'
```

**Streaming response:**
```bash
curl -X POST http://localhost:8000/api/v1/query/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain the data flow",
    "namespace": "my_project",
    "stream": true
  }'
```

### 3. Analyze Execution Flows

```bash
curl -X POST http://localhost:8000/api/v1/flows/parallelization \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "my_project"
  }'
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

## Development

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov

# Specific test file
poetry run pytest tests/unit/test_ingestion.py
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint
poetry run ruff check .

# Type check
poetry run mypy src/
```

## Agent Development Workflow

This project follows the agent specification defined in `NEW_SPEC_LLM.md`. Each agent is responsible for specific modules and follows the lifecycle:

1. **Initialize** - Load context and dependencies
2. **Plan** - Break down tasks
3. **Execute** - Implement changes
4. **Validate** - Run tests
5. **Report** - Document decisions
6. **Handoff** - Signal completion

See [Agent Specification](../NEW_SPEC_LLM.md) for details.

## License

MIT

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
