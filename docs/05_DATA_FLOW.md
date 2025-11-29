# FlowRAG Data Flow Documentation

## Table of Contents
- [Overview](#overview)
- [Ingestion Data Flow](#ingestion-data-flow)
- [Query Data Flow](#query-data-flow)
- [Flow Analysis Data Flow](#flow-analysis-data-flow)
- [Documentation Generation Data Flow](#documentation-generation-data-flow)
- [Cross-Service Relationship Building](#cross-service-relationship-building)
- [Caching Strategy](#caching-strategy)

---

## Overview

FlowRAG processes data through five main pipelines:
1. **Ingestion Pipeline**: Code → AST → Graph + Vectors
2. **Query Pipeline**: Question → Retrieval → LLM → Answer
3. **Flow Analysis Pipeline**: Workflow → Dependencies → Optimization
4. **Documentation Pipeline**: Code → Analysis → Markdown + Diagrams
5. **Relationship Building**: Services → API Calls → Cross-Service Edges

---

## Ingestion Data Flow

### Complete Ingestion Pipeline

```mermaid
flowchart TD
    START([Source Code Directory]) --> SCAN[Directory Scanner]
    SCAN --> FILTER{File Pattern<br/>Match?}

    FILTER -->|Match| DETECT[Language Detector]
    FILTER -->|No Match| SKIP[Skip File]

    DETECT --> SELECT[Parser Selector]
    SELECT --> PARSE{Parser Type}

    PARSE -->|Python| PY_PARSER[Python AST Parser]
    PARSE -->|JS/TS| JS_PARSER[JavaScript Tree-sitter Parser]
    PARSE -->|Java| JAVA_PARSER[Java Tree-sitter Parser]
    PARSE -->|Go| GO_PARSER[Go Tree-sitter Parser]
    PARSE -->|Dart| DART_PARSER[Dart AST Parser]
    PARSE -->|Other| GEN_PARSER[Generic Parser]

    PY_PARSER --> EXTRACT
    JS_PARSER --> EXTRACT
    JAVA_PARSER --> EXTRACT
    GO_PARSER --> EXTRACT
    DART_PARSER --> EXTRACT
    GEN_PARSER --> EXTRACT

    EXTRACT[Extract Code Units] --> UNITS{Unit Types}

    UNITS --> MODULES[Modules]
    UNITS --> CLASSES[Classes]
    UNITS --> FUNCTIONS[Functions]
    UNITS --> METHODS[Methods]

    MODULES --> RELATIONS[Build Relationships]
    CLASSES --> RELATIONS
    FUNCTIONS --> RELATIONS
    METHODS --> RELATIONS

    RELATIONS --> CALLS[CALLS Edges]
    RELATIONS --> CONTAINS[CONTAINS Edges]
    RELATIONS --> IMPORTS[IMPORTS Edges]

    CALLS --> NEO4J_LOAD[Neo4j Loader]
    CONTAINS --> NEO4J_LOAD
    IMPORTS --> NEO4J_LOAD

    NEO4J_LOAD --> CREATE_NODES[Create Nodes in Graph]
    CREATE_NODES --> CREATE_EDGES[Create Relationships in Graph]

    CREATE_EDGES --> EMBED_PREP[Prepare for Embedding]
    EMBED_PREP --> COMBINE[Combine: Signature +<br/>Docstring + Code]

    COMBINE --> BATCH[Batch Units<br/>100 per batch]
    BATCH --> OPENAI[OpenAI Embedding API<br/>text-embedding-3-small]

    OPENAI --> VECTORS[1536D Vectors]
    VECTORS --> QDRANT_LOAD[Qdrant Loader]

    QDRANT_LOAD --> UPSERT[Upsert Vectors<br/>with Metadata]

    UPSERT --> DOC_GEN{Generate<br/>Documentation?}
    DOC_GEN -->|Yes| DOC_PIPELINE[Documentation Pipeline]
    DOC_GEN -->|No| COMPLETE

    DOC_PIPELINE --> COMPLETE[Ingestion Complete]

    style PY_PARSER fill:#3776AB,color:#fff
    style JS_PARSER fill:#F7DF1E
    style CREATE_NODES fill:#4581C3,color:#fff
    style UPSERT fill:#DC477D,color:#fff
    style OPENAI fill:#10A37F,color:#fff
```

### Detailed Parsing Flow

```mermaid
sequenceDiagram
    participant File as Source File
    participant Detector as Language Detector
    participant Parser as Language Parser
    participant AST as AST Analyzer
    participant Extractor as Code Unit Extractor
    participant Result as ParseResult

    File->>Detector: Read file content
    Detector->>Detector: Check file extension
    Detector->>Detector: Analyze syntax patterns
    Detector-->>Parser: language = "python"

    Parser->>AST: parse(source_code)
    activate AST

    AST->>AST: Build Abstract Syntax Tree
    AST->>AST: Validate syntax

    alt Parse Success
        AST-->>Extractor: AST tree
        deactivate AST

        activate Extractor
        Extractor->>Extractor: Walk AST nodes

        loop For each node
            Extractor->>Extractor: Check node type

            alt FunctionDef
                Extractor->>Extractor: Extract function metadata
                Extractor->>Extractor: Calculate complexity
                Extractor->>Extractor: Extract docstring
                Extractor->>Extractor: Extract parameters
                Extractor->>Extractor: Find function calls
                Extractor->>Result: Add to functions[]
            else ClassDef
                Extractor->>Extractor: Extract class metadata
                Extractor->>Extractor: Extract methods
                Extractor->>Extractor: Extract inheritance
                Extractor->>Result: Add to classes[]
            else Import
                Extractor->>Extractor: Extract import statements
                Extractor->>Result: Add to imports[]
            else Call
                Extractor->>Extractor: Extract function calls
                Extractor->>Result: Add to calls[]
            end
        end

        Extractor-->>Result: ParseResult complete
        deactivate Extractor
    else Parse Error
        AST-->>Parser: SyntaxError
        Parser-->>Result: ParseResult with errors
    end

    Result-->>File: ParseResult {modules, classes, functions, methods, imports, calls}
```

### Neo4j Loading Flow

```mermaid
sequenceDiagram
    participant Loader as Neo4j Loader
    participant Builder as Query Builder
    participant Neo4j as Neo4j Database
    participant Schema as Schema Validator

    Loader->>Loader: Receive ParseResult
    Loader->>Schema: Validate against schema
    Schema-->>Loader: Valid

    Note over Loader,Neo4j: Phase 1: Create Nodes

    loop For each module
        Loader->>Builder: build_create_module_query()
        Builder-->>Loader: CREATE (m:Module {properties})
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Node created (id)
    end

    loop For each class
        Loader->>Builder: build_create_class_query()
        Builder-->>Loader: CREATE (c:Class {properties})
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Node created (id)
    end

    loop For each function
        Loader->>Builder: build_create_function_query()
        Builder-->>Loader: CREATE (f:Function {properties})
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Node created (id)
    end

    loop For each method
        Loader->>Builder: build_create_method_query()
        Builder-->>Loader: CREATE (m:Method {properties})
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Node created (id)
    end

    Note over Loader,Neo4j: Phase 2: Create Relationships

    loop For each CONTAINS relationship
        Loader->>Builder: build_contains_relationship()
        Builder-->>Loader: MATCH... CREATE ()-[:CONTAINS]->()
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Relationship created
    end

    loop For each CALLS relationship
        Loader->>Builder: build_calls_relationship()
        Builder-->>Loader: MATCH... CREATE ()-[:CALLS]->()
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Relationship created
    end

    loop For each IMPORTS relationship
        Loader->>Builder: build_imports_relationship()
        Builder-->>Loader: MATCH... CREATE ()-[:IMPORTS]->()
        Loader->>Neo4j: Execute Cypher
        Neo4j-->>Loader: Relationship created
    end

    Loader->>Neo4j: Commit transaction
    Neo4j-->>Loader: Success
```

### Qdrant Loading Flow

```mermaid
flowchart TD
    START[ParseResult with Code Units] --> PREPARE[Prepare Embedding Texts]

    PREPARE --> COMBINE[For each unit:<br/>text = signature + docstring + code]
    COMBINE --> BATCH{Batch Size<br/>< 100?}

    BATCH -->|No| BATCH_READY[Batch Ready]
    BATCH -->|Yes| ADD_TO_BATCH[Add to Current Batch]
    ADD_TO_BATCH --> BATCH

    BATCH_READY --> OPENAI_CALL[OpenAI Embeddings API]
    OPENAI_CALL --> VECTORS[Receive 1536D Vectors]

    VECTORS --> BUILD_POINTS[Build Qdrant Points]
    BUILD_POINTS --> POINT{For each vector}

    POINT --> META[Attach Metadata:<br/>- type<br/>- code_unit_type<br/>- name<br/>- file_path<br/>- language<br/>- signature<br/>- docstring<br/>- full_code<br/>- namespace<br/>- complexity]

    META --> VALIDATE[Validate Point Structure]
    VALIDATE --> UPSERT[Upsert to Qdrant]

    UPSERT --> COLLECTION{Collection<br/>Exists?}
    COLLECTION -->|No| CREATE_COLL[Create Collection<br/>vector_size: 1536<br/>distance: Cosine]
    COLLECTION -->|Yes| INSERT

    CREATE_COLL --> INSERT[Insert Points]
    INSERT --> SUCCESS[Success]

    SUCCESS --> MORE{More<br/>Batches?}
    MORE -->|Yes| BATCH_READY
    MORE -->|No| COMPLETE[Loading Complete]

    style OPENAI_CALL fill:#10A37F,color:#fff
    style INSERT fill:#DC477D,color:#fff
    style CREATE_COLL fill:#DC477D,color:#fff
```

---

## Query Data Flow

### Complete Query Pipeline

```mermaid
flowchart TD
    START([User Query:<br/>"How does authentication work?"]) --> RECEIVE[API Endpoint Receives Request]

    RECEIVE --> VALIDATE[Validate Request:<br/>- Query not empty<br/>- Namespace exists<br/>- Max results valid]

    VALIDATE --> ORCHESTRATE[Orchestrator.orchestrate()]

    ORCHESTRATE --> CLASSIFY[Intent Classifier]
    CLASSIFY --> PATTERNS[Pattern Matching]
    PATTERNS --> EXTRACT[Entity Extraction]
    EXTRACT --> INTENT{Detected Intent}

    INTENT -->|FIND_FUNCTION| STRAT1[Strategy: Hybrid<br/>Vector + Context]
    INTENT -->|EXPLAIN_CODE| STRAT2[Strategy: Full Hybrid]
    INTENT -->|TRACE_CALLS| STRAT3[Strategy: Graph Only]
    INTENT -->|FIND_FLOW| STRAT4[Strategy: Flow Hybrid]

    STRAT1 --> RETRIEVE[Hybrid Retriever]
    STRAT2 --> RETRIEVE
    STRAT3 --> GRAPH_ONLY[Graph Retriever]
    STRAT4 --> RETRIEVE

    RETRIEVE --> PARALLEL{Parallel Retrieval}

    PARALLEL -->|Thread 1| VECTOR_SEARCH[Vector Search]
    PARALLEL -->|Thread 2| GRAPH_SEARCH[Graph Traversal]

    VECTOR_SEARCH --> GEN_EMB[Generate Query Embedding]
    GEN_EMB --> QDRANT_SEARCH[Qdrant.search()]
    QDRANT_SEARCH --> VEC_RESULTS[Vector Results<br/>with Scores]

    GRAPH_SEARCH --> BUILD_CYPHER[Build Intent-Specific<br/>Cypher Query]
    BUILD_CYPHER --> NEO4J_QUERY[Neo4j.execute_query()]
    NEO4J_QUERY --> GRAPH_RESULTS[Graph Results<br/>with Relationships]

    GRAPH_ONLY --> BUILD_CYPHER

    VEC_RESULTS --> MERGE[Merge Results]
    GRAPH_RESULTS --> MERGE

    MERGE --> DEDUP[Deduplicate by ID]
    DEDUP --> RANK[Rank by Relevance:<br/>- Vector score<br/>- Graph centrality<br/>- Recency]

    RANK --> ASSEMBLE[Context Assembler]
    ASSEMBLE --> FORMAT[Format for LLM:<br/>- Add source citations<br/>- Structure context<br/>- Apply token limit]

    FORMAT --> BUILD_PROMPT[Build LLM Prompt:<br/>System + Context + Query]

    BUILD_PROMPT --> LLM_CALL[LLM API Call]
    LLM_CALL --> GPT4{LLM Provider}

    GPT4 -->|OpenAI| OPENAI[GPT-4 API]
    GPT4 -->|Anthropic| CLAUDE[Claude 3 API]

    OPENAI --> RESPONSE[Generated Response]
    CLAUDE --> RESPONSE

    RESPONSE --> ENRICH[Enrich with Metadata:<br/>- Intent<br/>- Sources used<br/>- Retrieval time<br/>- Token count]

    ENRICH --> RETURN[Return to User]

    style CLASSIFY fill:#FFB84D
    style QDRANT_SEARCH fill:#DC477D,color:#fff
    style NEO4J_QUERY fill:#4581C3,color:#fff
    style OPENAI fill:#10A37F,color:#fff
    style CLAUDE fill:#D97757,color:#fff
```

### Intent Classification Detail

```mermaid
flowchart LR
    QUERY[User Query] --> NORMALIZE[Normalize Text:<br/>- Lowercase<br/>- Remove special chars<br/>- Tokenize]

    NORMALIZE --> PATTERNS{Pattern Matching}

    PATTERNS --> P1{Contains<br/>'find function'<br/>'get function'?}
    PATTERNS --> P2{Contains<br/>'how does'<br/>'explain'?}
    PATTERNS --> P3{Contains<br/>'who calls'<br/>'usage'?}
    PATTERNS --> P4{Contains<br/>'trace'<br/>'call chain'?}
    PATTERNS --> P5{Contains<br/>'workflow'<br/>'process'?}
    PATTERNS --> P6{Contains<br/>'parallel'<br/>'concurrent'?}

    P1 -->|Yes| FIND_FUNC[Intent: FIND_FUNCTION]
    P2 -->|Yes| EXPLAIN[Intent: EXPLAIN_CODE]
    P3 -->|Yes| USAGE[Intent: FIND_USAGE]
    P4 -->|Yes| TRACE[Intent: TRACE_CALLS]
    P5 -->|Yes| FLOW[Intent: FIND_FLOW]
    P6 -->|Yes| PARALLEL[Intent: PARALLEL_STEPS]

    P1 -->|No| ENTITY_CHECK
    P2 -->|No| ENTITY_CHECK
    P3 -->|No| ENTITY_CHECK
    P4 -->|No| ENTITY_CHECK
    P5 -->|No| ENTITY_CHECK
    P6 -->|No| ENTITY_CHECK

    ENTITY_CHECK{Entity<br/>Extraction} --> HAS_FUNC{Function<br/>name found?}
    HAS_FUNC -->|Yes| FIND_FUNC
    HAS_FUNC -->|No| HAS_CLASS{Class<br/>name found?}
    HAS_CLASS -->|Yes| FIND_CLASS[Intent: FIND_CLASS]
    HAS_CLASS -->|No| DEFAULT[Intent: EXPLAIN_CODE]

    FIND_FUNC --> EXTRACT_ENT[Extract Entities]
    EXPLAIN --> EXTRACT_ENT
    USAGE --> EXTRACT_ENT
    TRACE --> EXTRACT_ENT
    FLOW --> EXTRACT_ENT
    PARALLEL --> EXTRACT_ENT
    FIND_CLASS --> EXTRACT_ENT

    EXTRACT_ENT --> CONF[Calculate Confidence<br/>0.0 - 1.0]
    CONF --> RESULT[QueryIntent:<br/>- type<br/>- entities<br/>- confidence<br/>- strategy]

    style FIND_FUNC fill:#4CAF50
    style EXPLAIN fill:#2196F3
    style USAGE fill:#FF9800
    style TRACE fill:#9C27B0
```

### Hybrid Retrieval Strategy

```mermaid
sequenceDiagram
    participant Retriever as Hybrid Retriever
    participant VectorThread as Vector Search Thread
    participant GraphThread as Graph Search Thread
    participant Qdrant
    participant Neo4j
    participant Merger as Result Merger

    Retriever->>Retriever: Receive query + intent
    Retriever->>Retriever: Determine retrieval strategy

    par Vector Search
        Retriever->>VectorThread: spawn_vector_search()
        activate VectorThread
        VectorThread->>VectorThread: Generate query embedding
        VectorThread->>Qdrant: search(vector, namespace, top_k)
        Qdrant-->>VectorThread: results with scores
        VectorThread->>VectorThread: Filter by threshold (>0.3)
        VectorThread-->>Merger: vector_results[]
        deactivate VectorThread
    and Graph Search
        Retriever->>GraphThread: spawn_graph_search()
        activate GraphThread
        GraphThread->>GraphThread: Build Cypher query based on intent

        alt FIND_FUNCTION intent
            GraphThread->>Neo4j: MATCH (f:Function) WHERE...
            GraphThread->>Neo4j: MATCH (f)-[:CALLS]->()
            GraphThread->>Neo4j: MATCH ()-[:CALLS]->(f)
        else TRACE_CALLS intent
            GraphThread->>Neo4j: MATCH path = shortestPath(...)
        else FIND_USAGE intent
            GraphThread->>Neo4j: MATCH ()-[r:CALLS]->(target)
        end

        Neo4j-->>GraphThread: graph_results[]
        GraphThread->>GraphThread: Enrich with metadata
        GraphThread-->>Merger: graph_results[]
        deactivate GraphThread
    end

    Merger->>Merger: Wait for both threads
    Merger->>Merger: Merge results by ID
    Merger->>Merger: Deduplicate (prefer graph data)
    Merger->>Merger: Rank by combined score:<br/>vector_score * 0.6 + graph_centrality * 0.4
    Merger->>Merger: Apply limits (top_k)
    Merger-->>Retriever: RetrievalResult
```

---

## Flow Analysis Data Flow

### Parallelization Detection Pipeline

```mermaid
flowchart TD
    START[Request: Analyze Flow] --> FETCH_FLOW[Fetch ExecutionFlow Node]
    FETCH_FLOW --> FETCH_STEPS[Fetch All Steps in Flow]

    FETCH_STEPS --> BUILD_GRAPH[Build Dependency Graph:<br/>nodes = steps<br/>edges = DEPENDS_ON]

    BUILD_GRAPH --> TOPO_SORT[Topological Sort]
    TOPO_SORT --> LEVELS{Assign Levels<br/>by Dependency Depth}

    LEVELS --> LEVEL_0[Level 0:<br/>No dependencies]
    LEVELS --> LEVEL_1[Level 1:<br/>Depends on Level 0]
    LEVELS --> LEVEL_N[Level N:<br/>Depends on Level N-1]

    LEVEL_0 --> GROUP_0[Parallel Group 1:<br/>All Level 0 steps]
    LEVEL_1 --> ANALYZE_1[Analyze Level 1<br/>Dependencies]
    LEVEL_N --> ANALYZE_N[Analyze Level N<br/>Dependencies]

    ANALYZE_1 --> CHECK_1{All steps at this<br/>level independent?}
    CHECK_1 -->|Yes| GROUP_1[Parallel Group]
    CHECK_1 -->|No| SUB_GROUPS_1[Split into<br/>Sub-groups]

    ANALYZE_N --> CHECK_N{Independent?}
    CHECK_N -->|Yes| GROUP_N[Parallel Group]
    CHECK_N -->|No| SUB_GROUPS_N[Split into<br/>Sub-groups]

    GROUP_0 --> CRITICAL[Find Critical Path:<br/>Longest path through graph]
    GROUP_1 --> CRITICAL
    GROUP_N --> CRITICAL
    SUB_GROUPS_1 --> CRITICAL
    SUB_GROUPS_N --> CRITICAL

    CRITICAL --> SEQ_TIME[Calculate Sequential Time:<br/>Sum all step times]
    SEQ_TIME --> PAR_TIME[Calculate Parallel Time:<br/>Max time per group<br/>+ Sum of group times]

    PAR_TIME --> SPEEDUP[Calculate Speedup:<br/>sequential_time / parallel_time]

    SPEEDUP --> RECOMMENDATIONS[Generate Recommendations:<br/>- Parallelizable groups<br/>- Critical path bottlenecks<br/>- Optimization suggestions]

    RECOMMENDATIONS --> RESULT[FlowAnalysis Result]

    style BUILD_GRAPH fill:#FFB84D
    style GROUP_0 fill:#4CAF50
    style GROUP_1 fill:#4CAF50
    style GROUP_N fill:#4CAF50
    style CRITICAL fill:#F44336,color:#fff
```

### Dependency Graph Example

```mermaid
graph TD
    subgraph "Original Sequential Flow"
        S1[Step 1: Setup] --> S2[Step 2: Build]
        S2 --> S3[Step 3: Test Unit]
        S2 --> S4[Step 4: Test Integration]
        S2 --> S5[Step 5: Lint]
        S3 --> S6[Step 6: Deploy Staging]
        S4 --> S6
        S5 --> S6
        S6 --> S7[Step 7: E2E Test]
        S7 --> S8[Step 8: Deploy Prod]
    end

    subgraph "After Analysis"
        A1[Level 0: Step 1] --> A2[Level 1: Step 2]
        A2 --> PG1[Parallel Group 1]
        PG1 --> A3[Step 3]
        PG1 --> A4[Step 4]
        PG1 --> A5[Step 5]
        A3 --> A6[Level 3: Step 6]
        A4 --> A6
        A5 --> A6
        A6 --> A7[Level 4: Step 7]
        A7 --> A8[Level 5: Step 8]
    end

    style PG1 fill:#4CAF50
    style A1 fill:#2196F3
    style A8 fill:#F44336,color:#fff
```

---

## Documentation Generation Data Flow

### Auto-Documentation Pipeline

```mermaid
flowchart TD
    START[Request: Generate Docs<br/>for Namespace] --> ANALYZE[Analyze Codebase Structure]

    ANALYZE --> QUERY_NODES[Query Neo4j:<br/>All nodes in namespace]
    QUERY_NODES --> STATS[Calculate Statistics:<br/>- Total files<br/>- Total classes<br/>- Total functions<br/>- Languages used]

    STATS --> OVERVIEW[Generate Service Overview]
    OVERVIEW --> LLM_OVERVIEW[LLM Call:<br/>Generate description based on structure]

    LLM_OVERVIEW --> DIAGRAMS{Generate Diagrams}

    DIAGRAMS --> ARCH_DIAG[Architecture Diagram]
    DIAGRAMS --> SEQ_DIAG[Sequence Diagram]
    DIAGRAMS --> DATA_DIAG[Data Flow Diagram]

    ARCH_DIAG --> MERMAID_ARCH[Mermaid: Component Graph]
    SEQ_DIAG --> MERMAID_SEQ[Mermaid: API Call Sequence]
    DATA_DIAG --> MERMAID_DATA[Mermaid: Data Layers]

    MERMAID_ARCH --> COMPONENTS[Document Components]
    MERMAID_SEQ --> COMPONENTS
    MERMAID_DATA --> COMPONENTS

    COMPONENTS --> CONTROLLERS[Find Controllers:<br/>Classes with @app.route]
    COMPONENTS --> SERVICES[Find Services:<br/>Classes with business logic]
    COMPONENTS --> MODELS[Find Models:<br/>Data classes]

    CONTROLLERS --> APIs[Document API Endpoints]
    APIS --> ENDPOINT_LOOP{For each endpoint}

    ENDPOINT_LOOP --> ENDPOINT_INFO[Extract:<br/>- HTTP method<br/>- Path<br/>- Handler function<br/>- Parameters<br/>- Response type]

    ENDPOINT_INFO --> ENDPOINT_DOC[Create Endpoint Documentation]

    SERVICES --> SERVICE_DOC[Document Service Methods]
    MODELS --> MODEL_DOC[Document Data Models]

    ENDPOINT_DOC --> INTER_SERVICE[Detect Inter-Service Calls]
    SERVICE_DOC --> INTER_SERVICE
    MODEL_DOC --> INTER_SERVICE

    INTER_SERVICE --> HTTP_CALLS[Find HTTP Client Calls:<br/>- requests.get()<br/>- axios.post()<br/>- fetch()]

    HTTP_CALLS --> SDK_CALLS[Find SDK Calls:<br/>- AWS SDK<br/>- OpenAI<br/>- Stripe]

    SDK_CALLS --> DB_CALLS[Find DB Calls:<br/>- PostgreSQL<br/>- MongoDB<br/>- Redis]

    DB_CALLS --> SERVICE_MAP[Build Service Dependency Map]

    SERVICE_MAP --> MARKDOWN[Generate Markdown]
    MARKDOWN --> SECTIONS{Combine Sections}

    SECTIONS --> SEC1[# Service Overview]
    SECTIONS --> SEC2[## Architecture]
    SECTIONS --> SEC3[## Components]
    SECTIONS --> SEC4[## API Endpoints]
    SECTIONS --> SEC5[## Data Models]
    SECTIONS --> SEC6[## Dependencies]

    SEC1 --> FINAL[Complete Markdown Document]
    SEC2 --> FINAL
    SEC3 --> FINAL
    SEC4 --> FINAL
    SEC5 --> FINAL
    SEC6 --> FINAL

    FINAL --> STORE{Store Documentation}

    STORE --> NEO4J_DOC[Store in Neo4j:<br/>Document node with metadata]
    STORE --> VECTOR_DOC[Chunk and Embed:<br/>Store in Qdrant]

    NEO4J_DOC --> COMPLETE[Documentation Complete]
    VECTOR_DOC --> COMPLETE

    style LLM_OVERVIEW fill:#10A37F,color:#fff
    style MERMAID_ARCH fill:#FF6D00
    style MERMAID_SEQ fill:#FF6D00
    style MERMAID_DATA fill:#FF6D00
    style NEO4J_DOC fill:#4581C3,color:#fff
    style VECTOR_DOC fill:#DC477D,color:#fff
```

---

## Cross-Service Relationship Building

### Service Dependency Detection

```mermaid
flowchart TD
    START[Multiple Services Ingested] --> DETECT[Service Dependency Extractor]

    DETECT --> SCAN_CALLS[Scan for API Calls<br/>in All Services]

    SCAN_CALLS --> HTTP{HTTP Client Patterns}

    HTTP --> PYTHON_HTTP[Python:<br/>requests.get/post<br/>httpx.request<br/>urllib.request]

    HTTP --> JS_HTTP[JavaScript:<br/>axios.get/post<br/>fetch()<br/>superagent]

    HTTP --> JAVA_HTTP[Java:<br/>HttpClient<br/>RestTemplate<br/>OkHttp]

    PYTHON_HTTP --> EXTRACT_URL[Extract URL Patterns]
    JS_HTTP --> EXTRACT_URL
    JAVA_HTTP --> EXTRACT_URL

    EXTRACT_URL --> PARSE_URL[Parse URL Components:<br/>- Protocol<br/>- Host<br/>- Port<br/>- Path]

    PARSE_URL --> MAPPING[Load Service Mappings<br/>JSON Config]

    MAPPING --> MATCH{Match URL<br/>to Service}

    MATCH -->|Match Found| IDENTIFY[Identify Target Service]
    MATCH -->|No Match| LOG_UNKNOWN[Log Unknown External Call]

    IDENTIFY --> FIND_SOURCE[Find Source Function in Neo4j]
    FIND_SOURCE --> FIND_TARGET[Find Target Endpoint in Neo4j]

    FIND_TARGET --> CREATE_REL[Create CALLS_API Relationship]

    CREATE_REL --> REL_PROPS[Add Relationship Properties:<br/>- target_service<br/>- target_url<br/>- http_method<br/>- detected_at]

    REL_PROPS --> NEO4J_CREATE[Neo4j: CREATE Relationship]

    NEO4J_CREATE --> MORE{More<br/>Calls?}
    MORE -->|Yes| SCAN_CALLS
    MORE -->|No| SUMMARY[Generate Summary Report]

    LOG_UNKNOWN --> SUMMARY

    SUMMARY --> RESULT[Cross-Service Map Complete]

    style IDENTIFY fill:#4CAF50
    style CREATE_REL fill:#4581C3,color:#fff
    style NEO4J_CREATE fill:#4581C3,color:#fff
```

### Service Mapping Configuration

```mermaid
graph LR
    CONFIG[Service Mappings JSON] --> MAP1["URL Pattern:<br/>'api.payment.com'<br/>→ Service: 'payment-service'"]
    CONFIG --> MAP2["URL Pattern:<br/>'auth.example.com'<br/>→ Service: 'auth-service'"]
    CONFIG --> MAP3["URL Pattern:<br/>'localhost:8001'<br/>→ Service: 'user-service'"]

    MAP1 --> DETECTOR[Service Call Detector]
    MAP2 --> DETECTOR
    MAP3 --> DETECTOR

    DETECTOR --> HTTP_CALL[HTTP Call Found:<br/>'https://api.payment.com/charge']

    HTTP_CALL --> MATCH[Pattern Matching]
    MATCH --> IDENTIFIED[Identified: payment-service]

    IDENTIFIED --> GRAPH[Create Graph Relationship:<br/>caller-function-[:CALLS_API]->payment-service]

    style CONFIG fill:#FFB84D
    style GRAPH fill:#4581C3,color:#fff
```

---

## Caching Strategy

### Multi-Level Caching

```mermaid
flowchart TD
    QUERY[User Query] --> CACHE_CHECK{Redis<br/>Cache Hit?}

    CACHE_CHECK -->|Hit| CACHED[Return Cached Response<br/>TTL: 5 minutes]
    CACHE_CHECK -->|Miss| EMBED_CACHE{Embedding<br/>Cache Hit?}

    EMBED_CACHE -->|Hit| SKIP_EMBED[Skip OpenAI Call<br/>Use Cached Embedding]
    EMBED_CACHE -->|Miss| GEN_EMBED[Generate Embedding<br/>via OpenAI]

    GEN_EMBED --> STORE_EMBED[Store in Redis<br/>TTL: 1 hour]
    STORE_EMBED --> SKIP_EMBED

    SKIP_EMBED --> RETRIEVAL[Hybrid Retrieval]
    RETRIEVAL --> RESULT_CACHE{Recent<br/>Similar Query?}

    RESULT_CACHE -->|Yes| REUSE[Reuse Retrieval Results]
    RESULT_CACHE -->|No| FULL_RETRIEVE[Full Hybrid Retrieval]

    FULL_RETRIEVE --> STORE_RESULT[Cache Retrieval Results<br/>TTL: 10 minutes]
    STORE_RESULT --> REUSE

    REUSE --> LLM[LLM Generation]
    LLM --> STORE_FINAL[Store Final Response<br/>TTL: 5 minutes]

    STORE_FINAL --> RETURN[Return to User]
    CACHED --> RETURN

    style CACHED fill:#4CAF50
    style SKIP_EMBED fill:#4CAF50
    style REUSE fill:#4CAF50
```

---

## Summary

### Data Flow Characteristics

| Pipeline | Latency | Throughput | Bottleneck |
|----------|---------|------------|------------|
| **Ingestion** | 0.5-2s per file | 1-2 files/sec | OpenAI embedding API |
| **Query (Vector)** | 50-100ms | 100 QPS | Qdrant search |
| **Query (Graph)** | 20-50ms | 200 QPS | Neo4j traversal |
| **Query (LLM)** | 2-5s | 10 QPS | GPT-4 generation |
| **Flow Analysis** | 100-500ms | 50 QPS | Graph traversal |
| **Documentation** | 10-30s | 1 per minute | LLM generation |

### Optimization Strategies

1. **Batching**: Group embeddings (100 per batch)
2. **Caching**: Multi-level (Redis for queries, in-memory for embeddings)
3. **Parallel Retrieval**: Vector + Graph search concurrently
4. **Connection Pooling**: Reuse database connections
5. **Async I/O**: Non-blocking database operations
6. **Rate Limiting**: Prevent OpenAI API throttling

---

**Next**: [Hybrid RAG Explained](./06_HYBRID_RAG.md) | [Back to Index](./README.md)
