# FlowRAG Architecture Overview

## Table of Contents
- [Introduction](#introduction)
- [High-Level Architecture](#high-level-architecture)
- [Component Architecture](#component-architecture)
- [Data Flow Architecture](#data-flow-architecture)
- [Database Architecture](#database-architecture)
- [Query Pipeline Architecture](#query-pipeline-architecture)
- [Deployment Architecture](#deployment-architecture)

---

## Introduction

FlowRAG follows a **multi-agent microservice architecture** where each component has a specific responsibility. The system is designed for:
- **Scalability**: Handle codebases from small projects to enterprise-scale
- **Extensibility**: Easy to add new language parsers and LLM providers
- **Performance**: Optimized hybrid retrieval combining graph + vector search
- **Reliability**: Production-ready with comprehensive testing

---

## High-Level Architecture

### System Overview

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[Web UI<br/>Streamlit/Gradio]
        CLI[CLI Tools<br/>Scripts]
        SDK[Python SDK<br/>Client Library]
    end

    subgraph "API Gateway Layer"
        FASTAPI[FastAPI Server<br/>Port 8000]
        MIDDLEWARE[Middleware Stack]
        AUTH[Authentication]
        RATE[Rate Limiting]
    end

    subgraph "Business Logic Layer"
        subgraph "Ingestion Services"
            PARSER[Parser Service<br/>8+ Languages]
            LOADER[Data Loader<br/>Neo4j + Qdrant]
            EMBED[Embedding Service<br/>OpenAI]
        end

        subgraph "Query Services"
            ORCHESTRATOR[Orchestrator<br/>Query Coordination]
            INTENT[Intent Classifier<br/>Route Queries]
            RETRIEVER[Hybrid Retriever<br/>Graph + Vector]
            CONTEXT[Context Assembler<br/>LLM Prep]
        end

        subgraph "Analysis Services"
            FLOW[Flow Analyzer<br/>Parallelization]
            DOCGEN[Doc Generator<br/>Auto-Docs]
            DETECTOR[Service Call Detector<br/>Inter-Service]
        end
    end

    subgraph "Data Persistence Layer"
        NEO4J[(Neo4j<br/>Graph Database<br/>Port 7687)]
        QDRANT[(Qdrant<br/>Vector Database<br/>Port 6333)]
        REDIS[(Redis<br/>Cache<br/>Port 6379)]
    end

    subgraph "External Services"
        OPENAI[OpenAI<br/>GPT-4 + Embeddings]
        ANTHROPIC[Anthropic<br/>Claude 3]
        HUGGINGFACE[HuggingFace<br/>Gemma SLM]
    end

    UI --> FASTAPI
    CLI --> FASTAPI
    SDK --> FASTAPI

    FASTAPI --> MIDDLEWARE
    MIDDLEWARE --> AUTH
    MIDDLEWARE --> RATE

    FASTAPI --> PARSER
    FASTAPI --> ORCHESTRATOR
    FASTAPI --> FLOW
    FASTAPI --> DOCGEN

    PARSER --> LOADER
    LOADER --> NEO4J
    LOADER --> EMBED
    EMBED --> QDRANT

    ORCHESTRATOR --> INTENT
    INTENT --> RETRIEVER
    RETRIEVER --> NEO4J
    RETRIEVER --> QDRANT
    RETRIEVER --> CONTEXT
    CONTEXT --> OPENAI
    CONTEXT --> ANTHROPIC

    FLOW --> NEO4J
    DOCGEN --> NEO4J
    DOCGEN --> QDRANT
    DOCGEN --> OPENAI

    ORCHESTRATOR --> REDIS
    RETRIEVER --> REDIS

    style NEO4J fill:#4581C3,color:#fff
    style QDRANT fill:#DC477D,color:#fff
    style OPENAI fill:#10A37F,color:#fff
    style ANTHROPIC fill:#D97757,color:#fff
    style REDIS fill:#DC382D,color:#fff
```

### Architecture Layers

| Layer | Components | Responsibility |
|-------|-----------|----------------|
| **Frontend** | Web UI, CLI, SDK | User interaction |
| **API Gateway** | FastAPI, Middleware, Auth | Request routing, security |
| **Business Logic** | Ingestion, Query, Analysis | Core functionality |
| **Data Persistence** | Neo4j, Qdrant, Redis | Data storage and caching |
| **External Services** | OpenAI, Anthropic, HF | LLM and embedding providers |

---

## Component Architecture

### Component Dependency Diagram

```mermaid
graph LR
    subgraph "api/"
        MAIN[main.py<br/>FastAPI App]
        ENDPOINTS[endpoints/<br/>Routes]
        SCHEMAS[schemas/<br/>Pydantic Models]
        MIDDLEWARE[middleware/<br/>CORS, Logging]
        SECURITY[security/<br/>Auth]
    end

    subgraph "orchestrator/"
        CONTROLLER[controller.py<br/>Main Orchestrator]
        ROUTER[router/<br/>Intent Classifier]
        RETRIEVAL[retrieval/<br/>Hybrid Retriever]
        CONTEXT_ASM[context/<br/>Context Assembler]
        FLOW_SVC[flow/<br/>Flow Analyzer]
        DOC_SVC[documentation/<br/>Doc Generator]
    end

    subgraph "ingestion/"
        PARSERS[parsers/<br/>15 Language Parsers]
        CHUNKERS[chunkers/<br/>Document Chunker]
        LOADERS[loaders/<br/>Neo4j + Qdrant]
        EMBEDDINGS[embeddings.py<br/>OpenAI Service]
    end

    subgraph "databases/"
        NEO4J_CLIENT[neo4j/<br/>Graph Client]
        QDRANT_CLIENT[qdrant/<br/>Vector Client]
        SCHEMAS_DB[neo4j/schema.py<br/>Graph Models]
    end

    subgraph "agents/"
        LLM[llm/<br/>GPT-4 + Claude]
        SLM[slm/<br/>Gemma Intent]
    end

    subgraph "core/"
        UTILS[utils/<br/>Helpers]
        CONFIG[config/<br/>Settings]
    end

    MAIN --> ENDPOINTS
    ENDPOINTS --> CONTROLLER
    ENDPOINTS --> PARSERS

    CONTROLLER --> ROUTER
    ROUTER --> RETRIEVAL
    RETRIEVAL --> CONTEXT_ASM
    CONTEXT_ASM --> LLM

    CONTROLLER --> FLOW_SVC
    CONTROLLER --> DOC_SVC

    PARSERS --> LOADERS
    LOADERS --> NEO4J_CLIENT
    LOADERS --> QDRANT_CLIENT
    LOADERS --> EMBEDDINGS
    EMBEDDINGS --> QDRANT_CLIENT

    RETRIEVAL --> NEO4J_CLIENT
    RETRIEVAL --> QDRANT_CLIENT

    FLOW_SVC --> NEO4J_CLIENT
    DOC_SVC --> NEO4J_CLIENT
    DOC_SVC --> LLM

    NEO4J_CLIENT --> SCHEMAS_DB

    MAIN --> MIDDLEWARE
    MAIN --> SECURITY
    ENDPOINTS --> SCHEMAS

    style CONTROLLER fill:#FFB84D
    style RETRIEVAL fill:#FFB84D
    style PARSERS fill:#4CAF50
    style LLM fill:#2196F3
```

### Module Responsibilities

#### **api/** - API Layer
- **main.py**: FastAPI application setup, CORS, middleware
- **endpoints/**: REST API route handlers
  - `ingest.py`: File/directory ingestion endpoints
  - `query.py`: Query endpoints (streaming + non-streaming)
  - `flow.py`: Flow analysis endpoints
  - `documentation.py`: Documentation generation endpoints
  - `workflows.py`: Multi-step workflow endpoints
- **schemas/**: Pydantic request/response models
- **middleware/**: Logging, error handling, CORS
- **security/**: API key authentication, rate limiting

#### **orchestrator/** - Query Coordination
- **controller.py**: Main orchestration logic
- **router/intent_classifier.py**: Query intent detection
- **retrieval/hybrid_retriever.py**: Graph + vector search
- **context/context_assembler.py**: LLM context preparation
- **flow/flow_analyzer.py**: Execution flow optimization
- **documentation/generator.py**: Auto-documentation

#### **ingestion/** - Code Processing
- **parsers/**: Language-specific AST parsers (15 languages)
- **chunkers/**: Document chunking with overlap
- **loaders/**: Database loaders (Neo4j, Qdrant)
- **embeddings.py**: OpenAI embedding generation

#### **databases/** - Data Access
- **neo4j/client.py**: Graph database operations
- **neo4j/schema.py**: Node and relationship models
- **neo4j/queries.py**: Pre-built Cypher queries
- **qdrant/client.py**: Vector database operations

#### **agents/** - LLM Integration
- **llm/response_generator.py**: GPT-4/Claude response generation
- **llm/llm_client.py**: Multi-provider abstraction
- **slm/intent_classifier_slm.py**: Gemma 270M fine-tuned

---

## Data Flow Architecture

### Ingestion Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Parser as Language Parser
    participant Loader as Data Loader
    participant Embedder as Embedding Service
    participant Neo4j as Neo4j DB
    participant Qdrant as Qdrant DB

    Client->>API: POST /api/v1/ingest/directory
    activate API
    API->>API: Validate request
    API->>API: Scan directory for files

    loop For each file
        API->>Parser: parse_file(path, namespace)
        activate Parser
        Parser->>Parser: Detect language
        Parser->>Parser: Parse AST
        Parser->>Parser: Extract code units
        Parser-->>API: ParseResult
        deactivate Parser

        API->>Loader: load_parse_result()
        activate Loader

        Loader->>Neo4j: CREATE nodes (Module, Class, Function)
        Neo4j-->>Loader: ACK

        Loader->>Neo4j: CREATE relationships (CONTAINS, CALLS)
        Neo4j-->>Loader: ACK

        Loader->>Embedder: generate_embeddings(code_units)
        activate Embedder
        Embedder->>Embedder: Combine sig + doc + code
        Embedder->>Embedder: Call OpenAI API
        Embedder-->>Loader: embeddings[]
        deactivate Embedder

        Loader->>Qdrant: upsert_vectors(embeddings, metadata)
        Qdrant-->>Loader: ACK

        Loader-->>API: success
        deactivate Loader
    end

    API-->>Client: IngestResponse {files_ingested, chunks_created}
    deactivate API
```

### Query Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Orch as Orchestrator
    participant Intent as Intent Classifier
    participant Retriever as Hybrid Retriever
    participant Neo4j as Neo4j DB
    participant Qdrant as Qdrant DB
    participant Assembler as Context Assembler
    participant LLM as GPT-4/Claude

    Client->>API: POST /api/v1/query
    activate API
    API->>Orch: orchestrate(query, namespace)
    activate Orch

    Orch->>Intent: classify_intent(query)
    activate Intent
    Intent->>Intent: Pattern matching
    Intent->>Intent: Entity extraction
    Intent-->>Orch: QueryIntent {type, entities, strategy}
    deactivate Intent

    Orch->>Retriever: retrieve(query, intent)
    activate Retriever

    par Vector Search
        Retriever->>Embedder: generate_embedding(query)
        Embedder-->>Retriever: query_vector
        Retriever->>Qdrant: search(query_vector, namespace, top_k)
        Qdrant-->>Retriever: vector_results[]
    and Graph Traversal
        Retriever->>Neo4j: execute_cypher(intent-based query)
        Neo4j-->>Retriever: graph_results[]
    end

    Retriever->>Retriever: Merge and rank results
    Retriever-->>Orch: RetrievalResult
    deactivate Retriever

    Orch->>Assembler: assemble_context(retrieval_result)
    activate Assembler
    Assembler->>Assembler: Deduplicate
    Assembler->>Assembler: Rank by relevance
    Assembler->>Assembler: Format for LLM
    Assembler-->>Orch: AssembledContext
    deactivate Assembler

    Orch->>LLM: generate_response(context)
    activate LLM
    LLM->>LLM: Build prompt
    LLM->>LLM: Call OpenAI/Anthropic API
    LLM-->>Orch: Generated response
    deactivate LLM

    Orch-->>API: OrchestrationResult
    deactivate Orch
    API-->>Client: QueryResponse {answer, sources, intent}
    deactivate API
```

### Flow Analysis Pipeline

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Analyzer as Flow Analyzer
    participant Neo4j

    Client->>API: POST /api/v1/flows/analyze
    activate API
    API->>Analyzer: analyze_flow(namespace, flow_id)
    activate Analyzer

    Analyzer->>Neo4j: MATCH (flow:ExecutionFlow)
    Neo4j-->>Analyzer: flow_node

    Analyzer->>Neo4j: MATCH (step:Step)-[:PART_OF]->(flow)
    Neo4j-->>Analyzer: steps[]

    Analyzer->>Neo4j: MATCH (s1:Step)-[:DEPENDS_ON]->(s2:Step)
    Neo4j-->>Analyzer: dependencies[]

    Analyzer->>Analyzer: Build dependency graph
    Analyzer->>Analyzer: Topological sort
    Analyzer->>Analyzer: Find independent groups

    loop For each group
        Analyzer->>Analyzer: Check if parallel-safe
        Analyzer->>Analyzer: Calculate estimated time
    end

    Analyzer->>Analyzer: Find critical path (longest)
    Analyzer->>Analyzer: Calculate speedup potential
    Analyzer->>Analyzer: Generate recommendations

    Analyzer-->>API: FlowAnalysis {parallel_groups, critical_path, speedup}
    deactivate Analyzer
    API-->>Client: FlowAnalysisResponse
    deactivate API
```

---

## Database Architecture

### Neo4j Graph Schema

```mermaid
erDiagram
    Module ||--o{ Class : CONTAINS
    Module ||--o{ Function : CONTAINS
    Class ||--o{ Method : CONTAINS
    Function ||--o{ Function : CALLS
    Method ||--o{ Method : CALLS
    Method ||--o{ Function : CALLS
    Class ||--o{ Class : INHERITS_FROM
    Module ||--o{ Module : IMPORTS
    Endpoint ||--|| Function : HANDLES
    Endpoint ||--|| Method : HANDLES

    ExecutionFlow ||--o{ Step : CONTAINS
    Step ||--o{ Step : DEPENDS_ON
    Step ||--o{ Step : PARALLEL_WITH

    Module {
        string id PK
        string name
        string file_path
        string language
        string namespace
        int total_lines
    }

    Class {
        string id PK
        string name
        string file_path
        string signature
        string docstring
        string namespace
        int line_start
        int line_end
    }

    Function {
        string id PK
        string name
        string signature
        string docstring
        int complexity
        string[] parameters
        string namespace
        int line_start
        int line_end
    }

    Method {
        string id PK
        string name
        string signature
        string docstring
        int complexity
        string[] parameters
        string class_name
        string namespace
        int line_start
        int line_end
    }

    Endpoint {
        string id PK
        string path
        string http_method
        string handler_function
        string namespace
    }

    ExecutionFlow {
        string id PK
        string name
        string description
        string namespace
        int total_steps
    }

    Step {
        string id PK
        string name
        string description
        int sequence_number
        float estimated_time
        string namespace
    }
```

### Qdrant Vector Schema

```mermaid
graph TB
    subgraph "Qdrant Collections"
        subgraph "Collection: namespace_code"
            V1[Vector 1<br/>1536 dimensions]
            V2[Vector 2<br/>1536 dimensions]
            V3[Vector N<br/>1536 dimensions]
        end
    end

    subgraph "Vector Metadata"
        M1[type: code/document<br/>code_unit_type: function/class<br/>name: string<br/>file_path: string<br/>language: string<br/>signature: string<br/>docstring: string<br/>full_code: string<br/>namespace: string<br/>complexity: int]
    end

    V1 --- M1
    V2 --- M1
    V3 --- M1

    subgraph "Embedding Source"
        E1[Text: signature + docstring + code]
        E2[OpenAI API<br/>text-embedding-3-small]
        E3[1536D Vector]
    end

    E1 --> E2
    E2 --> E3
    E3 --> V1

    style V1 fill:#DC477D,color:#fff
    style V2 fill:#DC477D,color:#fff
    style V3 fill:#DC477D,color:#fff
```

---

## Query Pipeline Architecture

### Intent-Based Routing

```mermaid
flowchart TD
    START([User Query]) --> CLASSIFY[Intent Classifier]

    CLASSIFY --> FIND_FUNC{Intent?}

    FIND_FUNC -->|FIND_FUNCTION| HYBRID1[Hybrid: Vector + Graph]
    FIND_FUNC -->|FIND_CLASS| HYBRID2[Hybrid: Vector + Graph]
    FIND_FUNC -->|EXPLAIN_CODE| HYBRID3[Full Hybrid]
    FIND_FUNC -->|FIND_USAGE| GRAPH1[Graph Only: Find Callers]
    FIND_FUNC -->|TRACE_CALLS| GRAPH2[Graph Only: Call Chain]
    FIND_FUNC -->|FIND_FLOW| HYBRID4[Hybrid: Flow Nodes]
    FIND_FUNC -->|PARALLEL_STEPS| GRAPH3[Graph: PARALLEL_WITH]
    FIND_FUNC -->|OPTIMIZE_FLOW| HYBRID5[Hybrid + Flow Analysis]

    HYBRID1 --> VECTOR1[Qdrant: Semantic Search]
    HYBRID1 --> GRAPH4[Neo4j: Get Context]
    VECTOR1 --> MERGE1[Merge Results]
    GRAPH4 --> MERGE1

    HYBRID2 --> VECTOR2[Qdrant: Class Search]
    HYBRID2 --> GRAPH5[Neo4j: Hierarchy]
    VECTOR2 --> MERGE2[Merge Results]
    GRAPH5 --> MERGE2

    HYBRID3 --> VECTOR3[Qdrant: Semantic]
    HYBRID3 --> GRAPH6[Neo4j: Relationships]
    VECTOR3 --> MERGE3[Merge Results]
    GRAPH6 --> MERGE3

    GRAPH1 --> NEO4J1[Neo4j: MATCH -[:CALLS]->]
    GRAPH2 --> NEO4J2[Neo4j: Shortest Path]
    GRAPH3 --> NEO4J3[Neo4j: PARALLEL_WITH]

    HYBRID4 --> VECTOR4[Qdrant: Flow Search]
    HYBRID4 --> GRAPH7[Neo4j: Steps + Deps]
    VECTOR4 --> MERGE4[Merge Results]
    GRAPH7 --> MERGE4

    HYBRID5 --> VECTOR5[Qdrant: Workflow]
    HYBRID5 --> GRAPH8[Neo4j: Dependency Graph]
    HYBRID5 --> ANALYZER[Flow Analyzer]
    VECTOR5 --> MERGE5[Merge Results]
    GRAPH8 --> MERGE5
    ANALYZER --> MERGE5

    MERGE1 --> ASSEMBLE[Context Assembler]
    MERGE2 --> ASSEMBLE
    MERGE3 --> ASSEMBLE
    NEO4J1 --> ASSEMBLE
    NEO4J2 --> ASSEMBLE
    NEO4J3 --> ASSEMBLE
    MERGE4 --> ASSEMBLE
    MERGE5 --> ASSEMBLE

    ASSEMBLE --> LLM[LLM Response Generator]
    LLM --> END([Response to User])

    style CLASSIFY fill:#FFB84D
    style ASSEMBLE fill:#4CAF50
    style LLM fill:#2196F3
```

### Hybrid Retrieval Strategy

```mermaid
graph LR
    subgraph "Vector Search Path"
        Q1[User Query] --> EMB1[Generate Embedding]
        EMB1 --> QDRANT[Qdrant Search<br/>Cosine Similarity]
        QDRANT --> VEC_RES[Vector Results<br/>Top-K by Score]
    end

    subgraph "Graph Search Path"
        Q2[User Query + Intent] --> PARSE[Parse Entities]
        PARSE --> CYPHER[Build Cypher Query]
        CYPHER --> NEO4J[Neo4j Traversal]
        NEO4J --> GRAPH_RES[Graph Results<br/>Relationship-Based]
    end

    subgraph "Result Fusion"
        VEC_RES --> MERGE[Merge Strategy]
        GRAPH_RES --> MERGE
        MERGE --> DEDUP[Deduplicate by ID]
        DEDUP --> RANK[Rank by Relevance]
        RANK --> LIMIT[Apply Limits]
        LIMIT --> FINAL[Final Context]
    end

    Q1 -.Query.-> Q2

    style QDRANT fill:#DC477D,color:#fff
    style NEO4J fill:#4581C3,color:#fff
    style MERGE fill:#4CAF50
```

---

## Deployment Architecture

### Docker Compose Deployment

```mermaid
graph TB
    subgraph "Docker Network: flowrag-network"
        subgraph "Application Container"
            FASTAPI_APP[FastAPI App<br/>Port 8000<br/>uvicorn]
        end

        subgraph "Database Containers"
            NEO4J_CONT[Neo4j<br/>Ports 7474, 7687<br/>neo4j:5.13]
            QDRANT_CONT[Qdrant<br/>Port 6333<br/>qdrant/qdrant:latest]
            REDIS_CONT[Redis<br/>Port 6379<br/>redis:alpine]
        end

        subgraph "Volumes"
            NEO4J_VOL[neo4j_data]
            QDRANT_VOL[qdrant_data]
            REDIS_VOL[redis_data]
        end
    end

    subgraph "External Services"
        OPENAI_EXT[OpenAI API<br/>api.openai.com]
        ANTHROPIC_EXT[Anthropic API<br/>api.anthropic.com]
    end

    FASTAPI_APP --> NEO4J_CONT
    FASTAPI_APP --> QDRANT_CONT
    FASTAPI_APP --> REDIS_CONT
    FASTAPI_APP -.HTTPS.-> OPENAI_EXT
    FASTAPI_APP -.HTTPS.-> ANTHROPIC_EXT

    NEO4J_CONT --> NEO4J_VOL
    QDRANT_CONT --> QDRANT_VOL
    REDIS_CONT --> REDIS_VOL

    style FASTAPI_APP fill:#009688
    style NEO4J_CONT fill:#4581C3,color:#fff
    style QDRANT_CONT fill:#DC477D,color:#fff
    style REDIS_CONT fill:#DC382D,color:#fff
```

### Production Kubernetes Deployment

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Ingress Layer"
            INGRESS[Ingress Controller<br/>NGINX/Traefik]
        end

        subgraph "Application Pods"
            API1[FlowRAG API Pod 1]
            API2[FlowRAG API Pod 2]
            API3[FlowRAG API Pod N]
        end

        subgraph "StatefulSets"
            NEO4J_SS[Neo4j StatefulSet<br/>3 Replicas]
            QDRANT_SS[Qdrant StatefulSet<br/>3 Replicas]
        end

        subgraph "Deployments"
            REDIS_DEP[Redis Deployment<br/>Master-Replica]
        end

        subgraph "Services"
            API_SVC[API Service<br/>LoadBalancer]
            NEO4J_SVC[Neo4j Service<br/>ClusterIP]
            QDRANT_SVC[Qdrant Service<br/>ClusterIP]
            REDIS_SVC[Redis Service<br/>ClusterIP]
        end

        subgraph "Persistent Volumes"
            NEO4J_PV[Neo4j PVCs]
            QDRANT_PV[Qdrant PVCs]
        end
    end

    INGRESS --> API_SVC
    API_SVC --> API1
    API_SVC --> API2
    API_SVC --> API3

    API1 --> NEO4J_SVC
    API1 --> QDRANT_SVC
    API1 --> REDIS_SVC

    NEO4J_SVC --> NEO4J_SS
    QDRANT_SVC --> QDRANT_SS
    REDIS_SVC --> REDIS_DEP

    NEO4J_SS --> NEO4J_PV
    QDRANT_SS --> QDRANT_PV

    style INGRESS fill:#FF6F00
    style API1 fill:#009688
    style API2 fill:#009688
    style API3 fill:#009688
    style NEO4J_SS fill:#4581C3,color:#fff
    style QDRANT_SS fill:#DC477D,color:#fff
```

---

## Summary

### Architecture Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Loose Coupling**: Components interact through well-defined interfaces
3. **High Cohesion**: Related functionality is grouped together
4. **Scalability**: Horizontal scaling of API servers and databases
5. **Extensibility**: Easy to add new parsers, LLM providers, retrieval strategies
6. **Observability**: Comprehensive logging and monitoring hooks

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI** | Async support, automatic OpenAPI docs, type safety |
| **Neo4j** | Native graph database for relationship queries |
| **Qdrant** | High-performance vector search with filtering |
| **OpenAI Embeddings** | Industry-standard 1536D embeddings |
| **Multi-Agent Pattern** | Modularity and testability |
| **Intent Classification** | Optimize retrieval strategy per query type |
| **Hybrid Retrieval** | Combine semantic and structural search |

### Performance Characteristics

- **Ingestion**: ~1.5 files/second (varies by file size)
- **Query Latency**: 3-8 seconds (including LLM call)
- **Vector Search**: < 100ms for top-50 results
- **Graph Traversal**: < 50ms for call chains up to depth 5
- **Concurrent Users**: 10-50 (single instance)
- **Scalability**: Horizontal scaling via load balancer

---

**Next**: [Data Flow](./05_DATA_FLOW.md) | [Back to Index](./README.md)
