# FlowRAG for QBlock Platform

## Overview

FlowRAG is a hybrid RAG (Retrieval-Augmented Generation) system that combines:
- **Vector Search** (Qdrant) - Semantic similarity search across code and documentation
- **Graph Traversal** (Neo4j) - Structural relationships, call graphs, and cross-service dependencies
- **LLM Generation** - Context-aware responses using retrieved information

## Ingested QBlock Services

| Namespace | Service | Nodes | Description |
|-----------|---------|-------|-------------|
| `qblock-mobile` | OrderManagementSystem | 185 | Flutter mobile app for order management |
| `qblock-shop-data` | ShopDataProvider | 146 | Shopify/Etsy order data integration |
| `qblock-label-service` | LabelCreationOrchestrator | 49 | Shipping label generation service |
| `qblock-auth-service` | ShopKeyProvider | 32 | Authentication and API key management |
| `qblock-transaction-data` | TransactionDataProvider | 15 | Etsy transaction data handler |
| `qblock-metrics` | MetricsJs | 5 | Metrics collection service |

**Total: 432 nodes across 6 services**

## Cross-Service Architecture

```
qblock-mobile (Flutter App)
    |
    +---> qblock-shop-data (2 API calls)
    |         |
    |         +---> qblock-label-service (1 API call)
    |                   - POST labelcreationorchestrator.app.runonflux.io/api/shipping/shipments
    |
    +---> qblock-label-service (1 API call)
    |         - POST labelcreationorchestrator.app.runonflux.io/api/shipping
    |
    +---> qblock-auth-service (1 API call)
              - GET shopkeyprovider.app.runonflux.io/api/shop-credentials

qblock-transaction-data (Standalone)
    |
    +---> External Etsy APIs only (api.etsy.com)

qblock-metrics (Standalone)
    - No external service calls
```

## API Usage

### Base URL
```
http://localhost:8000/api/v1
```

### Query Endpoint

**POST** `/api/v1/query`

```json
{
  "query": "How does OMS get orders from Shopify?",
  "namespace": "qblock-mobile",
  "max_results": 10,
  "max_context_tokens": 4000,
  "include_flow_analysis": false,
  "include_cross_service": true,
  "temperature": 0.2,
  "provider": "openai"
}
```

### Key Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Natural language question |
| `namespace` | string | required | Starting namespace to search |
| `include_cross_service` | bool | false | Search related services via CALLS_API relationships |
| `include_flow_analysis` | bool | false | Include execution flow analysis |
| `max_results` | int | 10 | Maximum retrieval results |
| `max_context_tokens` | int | 4000 | Token limit for LLM context |

### Example Queries

#### Single Service Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does OrderService work?",
    "namespace": "qblock-mobile"
  }'
```

#### Cross-Service Query
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does OMS get orders from Shopify?",
    "namespace": "qblock-mobile",
    "include_cross_service": true
  }'
```

## How Cross-Service Retrieval Works

1. **Namespace Discovery**: When `include_cross_service: true`, the system queries Neo4j for all namespaces connected via `CALLS_API` relationships

2. **Multi-Namespace Search**: Vector search is performed across all connected namespaces, not just the starting one

3. **Graph Context**: Cross-service API call information is included in the response context

### CALLS_API Relationship Schema

```cypher
(source)-[:CALLS_API {
  target_service: "qblock-shop-data",
  target_url: "https://shopdataprovider.app.runonflux.io/api/orders",
  http_method: "GET",
  source_function: "fetchOrders",
  source_file: "/path/to/file.dart"
}]->(target)
```

## Data Flow Examples

### Order Fetching Flow
```
1. OMS Flutter App (qblock-mobile)
   - OrderService.fetchOrders()

2. ShopDataProvider API Call
   - GET shopdataprovider.app.runonflux.io/api/orders

3. ShopDataProvider (qblock-shop-data)
   - ShopifyService.getOrders()
   - Calls Shopify API

4. Response flows back through the chain
```

### Label Creation Flow
```
1. OMS Flutter App (qblock-mobile)
   - LabelService.createLabel()

2. LabelCreationOrchestrator API Call
   - POST labelcreationorchestrator.app.runonflux.io/api/shipping

3. LabelCreationOrchestrator (qblock-label-service)
   - Generates shipping label
   - Returns label data
```

## Ingestion Commands

### Ingest a Single Service
```bash
curl -X POST http://localhost:8000/api/v1/ingest/directory \
  -H "Content-Type: application/json" \
  -d '{
    "directory_path": "/path/to/service",
    "namespace": "qblock-service-name",
    "recursive": true,
    "file_patterns": ["*.dart", "*.ts", "*.js"],
    "generate_documentation": true
  }'
```

### Build Cross-Service Relationships
```bash
python3 build_service_relationships.py
```

## Architecture Components

### 1. Hybrid Retriever
**File**: `orchestrator/retrieval/hybrid_retriever.py`

- Combines vector search (Qdrant) with graph traversal (Neo4j)
- `retrieve()` - Single namespace retrieval based on intent
- `retrieve_cross_service()` - Multi-namespace retrieval via CALLS_API

### 2. Intent Classifier
**File**: `orchestrator/router/intent_classifier.py`

Classifies queries into intents:
- `FIND_FUNCTION` - Looking for a specific function
- `FIND_CLASS` - Looking for a class
- `FIND_USAGE` - Finding where something is used
- `TRACE_CALLS` - Tracing call chains
- `FIND_FLOW` - Understanding execution flows
- `SEMANTIC` - General semantic search

### 3. Context Assembler
**File**: `orchestrator/context/context_assembler.py`

Assembles retrieved results into LLM-ready context with:
- Token budget management
- Source prioritization
- Citation generation

### 4. Service Dependency Extractor
**File**: `ingestion/parsers/service_dependency_extractor.py`

Extracts cross-service API calls from code:
- Detects `fetch()`, `http.get/post`, etc.
- Maps URLs to service namespaces
- Creates CALLS_API relationships in Neo4j

## Known Limitations

1. **Cross-Service Scope**: Currently searches ALL connected namespaces. Future improvement: restrict to namespaces mentioned in the query.

2. **TransactionDataProvider**: Standalone service with no CALLS_API relationships to other QBlock services (only calls external Etsy APIs).

3. **Service Mapping**: Cross-service detection relies on URL pattern matching. Custom services need URL mappings in `service_mappings.json`.

## Files Structure

```
flowrag-master/
├── api/
│   ├── endpoints/
│   │   └── query.py          # Query API endpoints
│   └── schemas/
│       └── query.py          # Request/Response schemas
├── orchestrator/
│   ├── controller.py         # Main orchestration logic
│   ├── retrieval/
│   │   └── hybrid_retriever.py
│   ├── router/
│   │   └── intent_classifier.py
│   └── context/
│       └── context_assembler.py
├── databases/
│   ├── neo4j/               # Graph database client
│   └── qdrant/              # Vector database client
└── ingestion/
    └── parsers/
        └── service_dependency_extractor.py
```
