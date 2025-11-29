# QBlock FlowRAG Query Results

This directory contains example query results demonstrating the FlowRAG hybrid Graph + Vector RAG system capabilities.

## Query Result Files

### Service-Level Queries

These queries focus on individual services and their specific implementations:

#### 1. [query_results_shopkeyprovider.txt](query_results_shopkeyprovider.txt)
**Question**: "What is the purpose of ShopKeyProvider?"

**Query Type**: Service-level hybrid query
**Service**: qblock-auth-service
**Demonstrates**:
- Vector search for service documentation
- Graph analysis of cross-service API calls
- Semantic code search for implementations
- LLM synthesis of comprehensive answer

**Key Insights**:
- Shows incoming/outgoing API relationships
- Identifies service role in architecture
- Maps authentication flow across services

---

#### 2. [query_results_label_creation.txt](query_results_label_creation.txt)
**Question**: "How does label creation work?"

**Query Type**: Service-level hybrid query
**Service**: qblock-label-service
**Demonstrates**:
- Documentation retrieval from vector store
- Graph traversal for service dependencies
- Component discovery and analysis
- Multi-step workflow explanation

**Key Insights**:
- Label service responsibilities
- Integration with mobile app and shop data
- Key orchestrator components

---

### Platform-Level Queries

These queries analyze the entire microservice architecture:

#### 3. [query_results_platform_flow.txt](query_results_platform_flow.txt)
**Question**: "What is the overall flow for QBlock?"

**Query Type**: Platform-level architecture analysis
**Services Analyzed**: All 6 QBlock services
**Demonstrates**:
- Multi-service discovery and documentation aggregation
- Cross-service API call pattern analysis
- Service dependency graph construction
- Service role identification (Entry Point, Middleware, Leaf)
- Mermaid architecture diagram generation
- LLM-powered architecture explanation

**Key Insights**:
- Complete service interaction map
- Request flow through the platform
- Architecture layers and patterns
- Integration points

---

#### 4. [query_results_services_integration.txt](query_results_services_integration.txt)
**Question**: "How do all the QBlock services work together?"

**Query Type**: Platform-level integration analysis
**Services Analyzed**: All 6 QBlock services
**Demonstrates**:
- Service orchestration patterns
- API communication flows
- Service dependency chains
- Architecture pattern recognition

**Key Insights**:
- Mobile-first architecture (Flutter entry point)
- Middleware layer pattern (shop-data service)
- Leaf service specialization
- Microservice communication patterns

---

## FlowRAG Query Pipeline

All queries follow this hybrid RAG pipeline:

```
User Question
    ↓
┌───────────────────────────────────────────────────────┐
│ STEP 1: Vector Search (Qdrant)                       │
│ • Semantic documentation search                       │
│ • Code similarity matching                            │
│ • Documentation chunk retrieval                       │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ STEP 2: Graph Analysis (Neo4j)                       │
│ • Service relationship queries                        │
│ • Cross-service API call detection                    │
│ • Component discovery                                 │
│ • Dependency mapping                                  │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ STEP 3: Semantic Code Search (Qdrant)                │
│ • Find relevant implementations                       │
│ • Match code patterns                                 │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ STEP 4: Flow Analysis (Neo4j)                        │
│ • Multi-service interaction patterns                  │
│ • Data flow through services                          │
└───────────────────────────────────────────────────────┘
    ↓
┌───────────────────────────────────────────────────────┐
│ STEP 5: LLM Synthesis (GPT-4)                        │
│ • Combine graph + vector data                         │
│ • Generate comprehensive natural language answer      │
│ • Provide architectural insights                      │
└───────────────────────────────────────────────────────┘
    ↓
Natural Language Answer
```

## Running Your Own Queries

### Service-Level Queries

```bash
cd /Users/prashanthboovaragavan/Documents/workspace/privateLLM/flowrag-master

# Query authentication
unset DEBUG && ./venv/bin/python3 qblock-test/query_flowrag.py "How does authentication work in QBlock?"

# Query shop data
unset DEBUG && ./venv/bin/python3 qblock-test/query_flowrag.py "What does ShopDataProvider do?"

# Query mobile app
unset DEBUG && ./venv/bin/python3 qblock-test/query_flowrag.py "What is the mobile app's role?"
```

### Platform-Level Queries

```bash
cd /Users/prashanthboovaragavan/Documents/workspace/privateLLM/flowrag-master

# Overall architecture
unset DEBUG && ./venv/bin/python3 qblock-test/query_platform_flow.py "Explain the QBlock architecture patterns"

# Data flow
unset DEBUG && ./venv/bin/python3 qblock-test/query_platform_flow.py "What is the data flow through QBlock?"
```

## Query Result Statistics

| Query Type | Services | Neo4j Queries | Qdrant Searches | LLM Calls | Avg Time |
|------------|----------|---------------|-----------------|-----------|----------|
| Service-level | 1 | 3-4 | 2-3 | 1 | 3-5s |
| Platform-level | 6 | 5-6 | 6+ | 1 | 5-8s |

## Technology Stack

- **Vector Database**: Qdrant (semantic search, embeddings)
- **Graph Database**: Neo4j (relationships, dependencies)
- **Embeddings**: OpenAI ada-002 (1536 dimensions)
- **LLM**: GPT-4 (synthesis and explanation)
- **Languages Parsed**: Dart, TypeScript, JavaScript, TSX

## Data Sources

All query results are based on:
- **865 Neo4j nodes** (classes, functions, methods)
- **905 Qdrant vectors** (code + documentation embeddings)
- **14 cross-service relationships** (CALLS_API)
- **6 services** across QBlock platform

## Key Features Demonstrated

1. **Hybrid RAG**: Combines graph structure with vector semantics
2. **Multi-Service Analysis**: Understands microservice architectures
3. **Natural Language**: Ask questions in plain English
4. **Automatic Documentation**: Generated docs from code analysis
5. **Architecture Visualization**: Mermaid diagrams of service flows
6. **LLM-Powered Insights**: AI-synthesized comprehensive answers

## Next Steps

To generate your own query results:

1. **Ask new questions**:
   ```bash
   ./venv/bin/python3 qblock-test/query_flowrag.py "Your question here"
   ```

2. **Save results**:
   ```bash
   ./venv/bin/python3 qblock-test/query_flowrag.py "Your question" > qblock-test/my_query_result.txt
   ```

3. **Compare platforms**:
   - Ingest different codebases
   - Query with same questions
   - Compare architectural patterns

---

**Generated**: 2025-11-28
**FlowRAG Version**: 1.0
**Status**: ✅ Production Ready
