# FlowRAG Quick Start Guide

## What is FlowRAG?

FlowRAG is a **hybrid AI-powered code intelligence system** that answers questions about your codebase by combining:

- **Documentation** (semantic search via Qdrant)
- **Code** (function-level search via Qdrant)
- **Call Graph** (relationship analysis via Neo4j)
- **LLM** (natural language synthesis via GPT-4)

---

## Quick Start (5 Minutes)

### 1. Start Services

```bash
cd flowrag-master

# Start Neo4j (graph database)
docker start flowrag-neo4j

# Start Qdrant (vector database)
docker start flowrag-qdrant

# Verify both are running
docker ps | grep flowrag
```

### 2. Set OpenAI API Key

```bash
export OPENAI_API_KEY="sk-..."
```

### 3. Ask Questions!

```bash
source venv/bin/activate

# Interactive mode
python3 scripts/query/query_with_llm.py

# Single question mode
python3 scripts/query/query_with_llm.py "How does user registration work?"
```

---

## Example Questions

### Architecture Questions
```
"How does the checkout flow work?"
"What happens when a user registers?"
"Explain the payment authorization process"
"Which services are involved in order creation?"
```

### Code-Specific Questions
```
"Show me the Register function and what it calls"
"How is password hashing implemented?"
"What functions are involved in cart management?"
"Trace the execution flow of payment authorization"
```

### Cross-Service Questions
```
"How do services communicate during checkout?"
"Which services call the payment service?"
"Show me the complete order creation flow"
"How are orders stored in the database?"
```

---

## System Architecture

```
Your Question
     ↓
FlowRAG Query System
     ↓
┌────────────────────────┐
│ 1. Search Docs (Qdrant)│ → Architecture context
├────────────────────────┤
│ 2. Search Code (Qdrant)│ → Function implementations
├────────────────────────┤
│ 3. Graph (Neo4j)       │ → Call relationships
├────────────────────────┤
│ 4. LLM (GPT-4)         │ → Natural language answer
└────────────────────────┘
     ↓
Comprehensive Answer
```

---

## Current Data

### Documentation
- **27 chunks** from comprehensive Sock Shop docs
- Architecture, flows, services, databases, deployment

### Code
- **683 functions** across all services
- Go, JavaScript, Java
- All 7 Sock Shop services

### Graph
- **683 nodes** (functions, classes)
- **205 relationships** (function calls)
- Multi-language call graph

---

## Files Overview

| File | Purpose |
|------|---------|
| `query_with_llm.py` | **Main query system** with LLM integration |
| `query_system.py` | Query system without LLM (shows raw context) |
| `test_documentation_search.py` | Test documentation search only |
| `demo_complete_hybrid.py` | Demo all capabilities |
| `ingest_documentation.py` | Ingest documentation into Qdrant |
| `ingest_sock_shop.py` | Ingest code into Neo4j + Qdrant |

---

## Common Tasks

### Ask a Question
```bash
python3 scripts/query/query_with_llm.py "Your question"
```

### Interactive Mode
```bash
python3 scripts/query/query_with_llm.py
# Then type questions interactively
```

### Test Documentation Search
```bash
python3 scripts/test/test_documentation_search.py
```

### Run Full Demo
```bash
python3 scripts/demo/demo_complete_hybrid.py
```

### Re-ingest Documentation
```bash
# Edit docs/sock_shop_memory_bank.md
python3 scripts/ingestion/ingest_documentation.py
```

### Re-ingest Code
```bash
python3 scripts/ingestion/ingest_sock_shop.py
```

---

## System Health Checks

### Check Qdrant
```bash
curl http://localhost:6333/collections/code_embeddings
# Should show: points_count: 710, status: green
```

### Check Neo4j
```bash
# Open Neo4j Browser: http://localhost:7474
# Run query:
MATCH (n) RETURN count(n)
# Should return: 683
```

### Check Both Services
```bash
docker ps | grep flowrag
# Should show both containers running
```

---

## Performance

- **Query time:** 5-6 seconds end-to-end
- **Qdrant search:** ~50ms per query
- **Neo4j graph:** ~100-200ms
- **LLM generation:** ~3-4 seconds
- **Context gathered:** 3 docs + 10 code + graph relationships

---

## Troubleshooting

### "OPENAI_API_KEY not set"
```bash
export OPENAI_API_KEY="sk-..."
```

### "Qdrant connection failed"
```bash
docker start flowrag-qdrant
curl http://localhost:6333/
```

### "Neo4j connection failed"
```bash
docker start flowrag-neo4j
# Check: http://localhost:7474
```

### "No results found"
```bash
# Re-ingest data
python3 scripts/ingestion/ingest_documentation.py
python3 scripts/ingestion/ingest_sock_shop.py
```

---

## Tips for Best Results

### 1. Be Specific
❌ "Tell me about payments"
✅ "How does payment authorization work? Show me the functions involved."

### 2. Ask About Flows
❌ "What is the user service?"
✅ "What happens when a user registers? Show me the complete flow."

### 3. Request Details
❌ "How does checkout work?"
✅ "Trace the complete checkout flow including all services, database operations, and error handling."

### 4. Ask About Relationships
❌ "What functions exist?"
✅ "Which services call the payment service and how do they communicate?"

---

## What Makes FlowRAG Unique?

### Traditional Code Search
```
grep "Register" *.go
# Returns: 50 matches
# You manually read and understand each
```

### FlowRAG
```
"How does user registration work?"

# Returns:
- Documentation explaining the flow
- Register function implementations
- calculatePassHash function it calls
- Database storage logic
- Validation steps
- Complete step-by-step explanation from LLM
```

**Result:** Complete understanding in 5 seconds! 🚀

---

## Next Steps

1. **Try Example Questions** - Use the examples above
2. **Ask Your Own Questions** - About Sock Shop architecture
3. **Explore Documentation** - See docs/sock_shop_memory_bank.md
4. **Review Demo** - Run demo_complete_hybrid.py
5. **Read Full Docs** - See HYBRID_LLM_QUERY_COMPLETE.md

---

## Need Help?

- **Full documentation:** HYBRID_LLM_QUERY_COMPLETE.md
- **System overview:** DOCUMENTATION_MEMORY_BANK_COMPLETE.md
- **Qdrant fix details:** QDRANT_FIX_SUMMARY.md
- **Test results:** COMPREHENSIVE_TEST_RESULTS.md

---

**Status:** ✅ Ready to use!

Ask any question about Sock Shop and get comprehensive answers powered by hybrid intelligence! 🎉
