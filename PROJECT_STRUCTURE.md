# FlowRAG Project Structure

**Clean, organized structure for hybrid code intelligence system**

---

## Directory Layout

```
flowrag-master/
├── 📄 Main Documentation (Root)
│   ├── README.md                              ⭐ Main project overview
│   ├── QUICK_START.md                         ⭐ Quick start guide
│   ├── HYBRID_LLM_QUERY_COMPLETE.md          ⭐ LLM query system docs
│   ├── DOCUMENTATION_MEMORY_BANK_COMPLETE.md ⭐ Documentation system docs
│   ├── COMPREHENSIVE_TEST_RESULTS.md          Test results (all parsers)
│   ├── QDRANT_FIX_SUMMARY.md                 Qdrant fix details
│   ├── COMPLETE_FLOW_SUMMARY.md              Flow detection results
│   └── FINAL_FLOW_VERIFICATION.md            Flow verification
│
├── 📁 scripts/                                All executable scripts
│   ├── ingestion/                            Data ingestion
│   │   ├── ingest_sock_shop.py              ⭐ Ingest all services
│   │   ├── ingest_documentation.py          ⭐ Ingest documentation
│   │   └── ingest_flux_pdf.py                Ingest PDF documents
│   │
│   ├── query/                                Query systems
│   │   ├── query_with_llm.py                ⭐ Main LLM-powered query
│   │   ├── query_system.py                   Query without LLM
│   │   ├── query_flux.py                     Query Flux docs
│   │   └── query_workflow_flow.py            Query workflow flows
│   │
│   ├── analysis/                             Analysis tools
│   │   ├── analyze_call_graph_gaps.py        Find call graph gaps
│   │   ├── analyze_flows.py                  Analyze detected flows
│   │   ├── analyze_flux_workflow.py          Analyze Flux workflows
│   │   └── comprehensive_flowrag_test.py     Full system test
│   │
│   ├── demo/                                 Demo scripts
│   │   ├── demo_complete_hybrid.py           Full hybrid search demo
│   │   ├── demo_hybrid_search.py             Basic hybrid search
│   │   ├── demo_flow.py                      Flow detection demo
│   │   ├── demo_simple.py                    Simple demo
│   │   └── extract_detailed_steps.py         Extract workflow steps
│   │
│   └── test/                                 Test scripts
│       ├── test_documentation_search.py      Test doc search
│       └── test_qdrant_fix.py                Test Qdrant fix
│
├── 📁 docs/                                   Documentation
│   ├── sock_shop_memory_bank.md             ⭐ Main documentation source
│   ├── guides/                               User guides
│   └── archive/                              Historical docs
│       ├── DEMO_RESULTS.md
│       ├── DOCUMENT_INGESTION_STATUS.md
│       ├── FLOWRAG_VERIFICATION_RESULTS.md
│       └── ... (old documentation)
│
├── 📁 databases/                              Database clients
│   ├── neo4j/                                Neo4j graph database
│   └── qdrant/                               Qdrant vector database
│
├── 📁 ingestion/                              Ingestion pipeline
│   ├── parsers/                              Code parsers (Go, JS, Java)
│   ├── loaders/                              Database loaders
│   ├── chunkers/                             Document chunking
│   └── embeddings/                           Embedding generation
│
├── 📁 orchestrator/                           Query orchestration
│   ├── retrieval/                            Hybrid retrieval
│   └── router/                               Query routing
│
├── 📁 agents/                                 LLM agents
│   ├── llm/                                  LLM integration
│   └── slm/                                  Small language models
│
├── 📁 api/                                    API layer
│   ├── endpoints/                            REST endpoints
│   ├── middleware/                           API middleware
│   └── schemas/                              Request/response schemas
│
├── 📁 ui/                                     User interface
│   └── app.py                                Web UI (Flask)
│
└── 📁 tests/                                  Test suites
    ├── unit/                                 Unit tests
    ├── integration/                          Integration tests
    └── e2e/                                  End-to-end tests
```

---

## Quick Reference

### 🚀 Most Important Files

**Getting Started:**
1. [QUICK_START.md](QUICK_START.md) - Start here!
2. [README.md](README.md) - Project overview

**Main Scripts:**
1. `scripts/query/query_with_llm.py` - **Main query system** (LLM-powered)
2. `scripts/ingestion/ingest_sock_shop.py` - Ingest all services
3. `scripts/ingestion/ingest_documentation.py` - Ingest documentation

**Documentation:**
1. [HYBRID_LLM_QUERY_COMPLETE.md](HYBRID_LLM_QUERY_COMPLETE.md) - Complete query system docs
2. [DOCUMENTATION_MEMORY_BANK_COMPLETE.md](DOCUMENTATION_MEMORY_BANK_COMPLETE.md) - Memory bank docs

---

## Usage

### Running Main Query System

```bash
# From root directory
python3 scripts/query/query_with_llm.py "Your question"

# Interactive mode
python3 scripts/query/query_with_llm.py
```

### Data Ingestion

```bash
# Ingest all Sock Shop services
python3 scripts/ingestion/ingest_sock_shop.py

# Ingest documentation
python3 scripts/ingestion/ingest_documentation.py
```

### Running Demos

```bash
# Complete hybrid search demo
python3 scripts/demo/demo_complete_hybrid.py

# Basic hybrid search
python3 scripts/demo/demo_hybrid_search.py
```

### Running Tests

```bash
# Test documentation search
python3 scripts/test/test_documentation_search.py

# Comprehensive system test
python3 scripts/analysis/comprehensive_flowrag_test.py
```

---

## Script Categories

### 📥 Ingestion Scripts

**Purpose:** Load data into Neo4j and Qdrant

| Script | Description | When to Use |
|--------|-------------|-------------|
| `ingest_sock_shop.py` | Ingest all 7 services | After code changes |
| `ingest_documentation.py` | Ingest documentation | After doc updates |
| `ingest_flux_pdf.py` | Ingest PDF documents | For PDF docs |

### 🔍 Query Scripts

**Purpose:** Query the system

| Script | Description | Best For |
|--------|-------------|----------|
| `query_with_llm.py` ⭐ | LLM-powered queries | Natural language questions |
| `query_system.py` | Raw context only | Debugging, seeing raw data |
| `query_flux.py` | Query Flux docs | Flux-specific questions |
| `query_workflow_flow.py` | Query workflows | Workflow analysis |

### 📊 Analysis Scripts

**Purpose:** Analyze system data

| Script | Description | Output |
|--------|-------------|--------|
| `analyze_call_graph_gaps.py` | Find missing calls | Gap report |
| `analyze_flows.py` | Analyze flow detection | Flow statistics |
| `comprehensive_flowrag_test.py` | Full system test | Test report |

### 🎬 Demo Scripts

**Purpose:** Demonstrate capabilities

| Script | Description | Shows |
|--------|-------------|-------|
| `demo_complete_hybrid.py` | Full demo | All 6 capabilities |
| `demo_hybrid_search.py` | Basic demo | Hybrid search |
| `demo_flow.py` | Flow demo | Flow detection |

### 🧪 Test Scripts

**Purpose:** Verify functionality

| Script | Description | Verifies |
|--------|-------------|----------|
| `test_documentation_search.py` | Test doc search | Documentation queries |
| `test_qdrant_fix.py` | Test Qdrant | Vector storage |

---

## Documentation Categories

### 📄 Root Documentation

**Keep in root for easy access**

| Document | Purpose | Audience |
|----------|---------|----------|
| README.md | Project overview | Everyone |
| QUICK_START.md | Quick start guide | New users |
| HYBRID_LLM_QUERY_COMPLETE.md | Query system docs | Developers |
| DOCUMENTATION_MEMORY_BANK_COMPLETE.md | Memory bank docs | Developers |
| COMPREHENSIVE_TEST_RESULTS.md | Test results | QA, Developers |

### 📁 docs/archive/

**Historical documentation**

All old documentation moved here:
- Previous test results
- Old demo results
- Historical implementation docs
- Legacy guides

**Why archived:**
- Superseded by newer docs
- Historical reference only
- Not needed for daily use

---

## Common Tasks

### 1. Ask a Question

```bash
cd flowrag-master
source venv/bin/activate
export OPENAI_API_KEY="sk-..."

python3 scripts/query/query_with_llm.py "How does checkout work?"
```

### 2. Update Documentation

```bash
# Edit documentation
vim docs/sock_shop_memory_bank.md

# Re-ingest
python3 scripts/ingestion/ingest_documentation.py
```

### 3. Re-ingest Code

```bash
# After code changes in sock-shop-services/
python3 scripts/ingestion/ingest_sock_shop.py
```

### 4. Run Full Demo

```bash
python3 scripts/demo/demo_complete_hybrid.py
```

### 5. Test System

```bash
# Test documentation search
python3 scripts/test/test_documentation_search.py

# Full system test
python3 scripts/analysis/comprehensive_flowrag_test.py
```

---

## Maintenance

### Adding New Scripts

**Ingestion scripts:**
```bash
# Create in scripts/ingestion/
vim scripts/ingestion/ingest_new_data.py
```

**Query scripts:**
```bash
# Create in scripts/query/
vim scripts/query/query_new_feature.py
```

### Adding New Documentation

**Main documentation:**
```bash
# Add to root if important
vim NEW_FEATURE_DOCS.md
```

**Archived documentation:**
```bash
# Archive old docs
mv OLD_DOC.md docs/archive/
```

---

## Benefits of This Structure

### ✅ Before (Cluttered)

```
flowrag-master/
├── 25 Python files in root
├── 18 Markdown files in root
└── Hard to find anything
```

**Problems:**
- Hard to find the right script
- Unclear what's important
- Difficult to navigate
- Confusing for new users

### ✅ After (Organized)

```
flowrag-master/
├── 8 important docs in root
├── scripts/ (organized by purpose)
│   ├── query/ (4 scripts)
│   ├── ingestion/ (3 scripts)
│   ├── analysis/ (4 scripts)
│   ├── demo/ (5 scripts)
│   └── test/ (2 scripts)
└── docs/archive/ (old docs)
```

**Benefits:**
- ✅ Easy to find scripts by category
- ✅ Clear what's important (in root)
- ✅ Easy to navigate
- ✅ New user friendly
- ✅ Clean separation of concerns

---

## Navigation Tips

### Finding Scripts

**"I want to query the system"**
→ `scripts/query/query_with_llm.py`

**"I want to ingest data"**
→ `scripts/ingestion/`

**"I want to see a demo"**
→ `scripts/demo/`

**"I want to analyze something"**
→ `scripts/analysis/`

**"I want to test something"**
→ `scripts/test/`

### Finding Documentation

**"I'm new here"**
→ `QUICK_START.md`

**"I want to use the query system"**
→ `HYBRID_LLM_QUERY_COMPLETE.md`

**"I want to understand the memory bank"**
→ `DOCUMENTATION_MEMORY_BANK_COMPLETE.md`

**"I want historical docs"**
→ `docs/archive/`

---

## File Naming Conventions

### Scripts

- **ingestion:** `ingest_<what>.py`
- **query:** `query_<what>.py`
- **analysis:** `analyze_<what>.py`
- **demo:** `demo_<what>.py`
- **test:** `test_<what>.py`

### Documentation

- **Complete docs:** `<NAME>_COMPLETE.md`
- **Summaries:** `<NAME>_SUMMARY.md`
- **Results:** `<NAME>_RESULTS.md`
- **Guides:** `<NAME>_GUIDE.md`

---

## Summary

### Organization Principles

1. **Root = Important** - Only essential docs in root
2. **Scripts by Purpose** - Organized into categories
3. **Archive Old Docs** - Keep history but separate
4. **Clear Naming** - Obvious what each file does
5. **Easy Navigation** - Find what you need quickly

### Key Takeaways

- ⭐ Main query: `scripts/query/query_with_llm.py`
- ⭐ Quick start: `QUICK_START.md`
- ⭐ Documentation: `HYBRID_LLM_QUERY_COMPLETE.md`
- 📁 Scripts organized by purpose
- 📁 Old docs archived
- 🎯 Clean, navigable structure

---

**Status:** ✅ Clean and organized!

**Total Organization:**
- 8 essential docs in root
- 18 scripts in organized folders
- 10+ old docs archived
- Clear structure and navigation
