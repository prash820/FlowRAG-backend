# Document Ingestion Status - What Exists Today

## Current State: Code-Only Ingestion ⚠️

**TL;DR:** FlowRAG today **only supports CODE ingestion** (Python, JavaScript, TypeScript). **No generic document ingestion** exists yet.

---

## What Works Today ✅

### 1. Code Ingestion (Production Ready)

**Supported Languages:**
- ✅ Python (.py)
- ✅ JavaScript (.js, .jsx)
- ✅ TypeScript (.ts, .tsx)
- ⚠️ Go, Rust, Java, C++ (parsers not implemented yet)

**How it works:**
```python
# Via API
POST /api/v1/ingest/file
{
  "file_path": "/path/to/code.py",
  "namespace": "my_project",
  "language": "python"  # Optional - auto-detected
}

# Or programmatically
from ingestion import get_parser
parser = get_parser("python")
result = parser.parse_file("code.py", namespace="my_project")
```

**What gets extracted:**
- ✅ Functions and methods
- ✅ Classes and modules
- ✅ Function signatures and docstrings
- ✅ Import statements
- ✅ Call graphs (function A calls function B)
- ✅ Code complexity metrics
- ✅ Line numbers and locations

**Where it's stored:**
- **Neo4j:** Code structure as graph (Class → Method → Function relationships)
- **Qdrant:** Code embeddings for semantic search

**Example:**
```python
# Ingests all Python code in a directory
POST /api/v1/ingest/directory
{
  "directory_path": "/path/to/project",
  "namespace": "my_app",
  "recursive": true,
  "file_patterns": ["*.py", "*.js"]
}

# Result:
# - 150 functions extracted
# - 45 classes found
# - 230 call relationships created
# - 150 embeddings stored
```

---

## What Does NOT Work ❌

### 1. Generic Document Ingestion (NOT IMPLEMENTED)

**Missing capabilities:**
- ❌ PDF parsing and workflow extraction
- ❌ Markdown to workflow conversion
- ❌ Plain text document chunking
- ❌ Workflow step detection
- ❌ Dependency inference from prose
- ❌ Parallel step detection from docs

**What exists:**
- ⚠️ `DocumentChunker` class exists ([ingestion/chunkers/document_chunker.py](ingestion/chunkers/document_chunker.py))
- ⚠️ Can split text into chunks with overlap
- ⚠️ BUT: No workflow intelligence! Just dumb text chunking

**Example of what DocumentChunker does:**
```python
chunker = DocumentChunker(max_chunk_size=1000, chunk_overlap=200)
chunks = chunker.chunk_text(text, file_path="doc.md", namespace="docs")

# Result: Just text chunks, NO workflow understanding
# [
#   DocumentChunk(content="First paragraph... Second paragraph...", chunk_index=0),
#   DocumentChunk(content="Second paragraph... Third paragraph...", chunk_index=1),
# ]
```

**What it CAN'T do:**
```python
# ❌ Extract steps: "Step 1: Download wallet", "Step 2: Login"
# ❌ Detect dependencies: Step 2 depends on Step 1
# ❌ Find parallelism: Steps 5 and 6 can run together
# ❌ Create graph relationships: (Step)-[:DEPENDS_ON]->(Step)
```

---

## Gap Analysis: What's Missing for Product

### For Generic Document → Workflow Ingestion

| Feature | Status | Priority | Effort |
|---------|--------|----------|--------|
| **PDF Parsing** | ❌ Missing | 🔴 Critical | 2-3 days |
| **LLM-based Step Extraction** | ❌ Missing | 🔴 Critical | 3-5 days |
| **Dependency Inference** | ❌ Missing | 🔴 Critical | 3-5 days |
| **Parallel Step Detection** | ❌ Missing | 🟡 Medium | 2-3 days |
| **Graph Relationship Creation** | ⚠️ Partial | 🔴 Critical | 2 days |
| **API Endpoint** | ❌ Missing | 🔴 Critical | 1 day |

**Total Effort:** ~2-3 weeks for MVP document ingestion

---

## Architecture: What Needs to Be Built

### Proposed Document Ingestion Pipeline

```
┌──────────────┐
│  PDF/MD/TXT  │
│   Document   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  1. Document Parser                      │
│     - PDF → Text (pypdf/pymupdf)        │
│     - Markdown → Structured Text        │
│     - HTML → Clean Text                 │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  2. LLM Workflow Extractor (NEW)        │
│     - Identify phases/sections          │
│     - Extract steps                     │
│     - Detect dependencies               │
│     - Find parallel opportunities       │
│     - Estimate timing                   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  3. Structured Workflow Builder (NEW)   │
│     Output:                             │
│     {                                   │
│       "phases": [...],                  │
│       "steps": [                        │
│         {                               │
│           "id": "step_1",               │
│           "name": "...",                │
│           "dependencies": ["step_0"],   │
│           "parallel_with": []           │
│         }                               │
│       ]                                 │
│     }                                   │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  4. Graph + Vector Storage              │
│     - Neo4j: (Phase)-[:CONTAINS]->(Step)│
│              (Step)-[:DEPENDS_ON]->(Step)│
│     - Qdrant: Embeddings for search     │
└─────────────────────────────────────────┘
```

---

## Comparison: Demo vs Product

### What We Did in Demo (Manual)

```python
# ingest_flux_pdf.py - Lines 33-307
FLUX_WORKFLOW = {
    "phases": [
        {
            "phase": "Prerequisites",
            "steps": [
                {
                    "id": "prereq_1",
                    "name": "Download ZelCore Wallet",
                    "dependencies": [],  # ← MANUALLY SPECIFIED
                    "parallel_with": []   # ← MANUALLY SPECIFIED
                }
            ]
        }
    ]
}

# Then automated ingestion
ingest_workflow(FLUX_WORKFLOW)
```

**Problem:** Requires human to read PDF and structure data. **Not scalable.**

---

### What Product Needs (Automated)

```python
# Document ingestion API (NEEDS TO BE BUILT)
POST /api/v1/ingest/document
{
  "file_path": "/path/to/any_setup_guide.pdf",
  "namespace": "customer_123",
  "document_type": "workflow"  # or "sop", "runbook", "guide"
}

# Backend automatically:
# 1. Extracts text from PDF
# 2. Sends to LLM: "Extract workflow steps with dependencies"
# 3. LLM returns structured JSON
# 4. Stores in Neo4j + Qdrant
# 5. Returns success

# User can immediately query:
POST /api/v1/query/flow
{
  "query": "What steps can I do in parallel?",
  "namespace": "customer_123"
}
```

**Goal:** Zero manual work. Upload PDF → Query workflows.

---

## Existing Code That Can Be Reused

### 1. Database Loaders ✅
**Files:**
- [ingestion/loaders/neo4j_loader.py](ingestion/loaders/neo4j_loader.py)
- [ingestion/loaders/qdrant_loader.py](ingestion/loaders/qdrant_loader.py)

**What they do:**
- Store nodes and relationships in Neo4j
- Store embeddings in Qdrant
- Handle namespaces for multi-tenancy

**Reusable for documents:** ✅ Yes, just need to adapt for workflow nodes instead of code nodes

---

### 2. Embedding Generator ✅
**File:** [ingestion/embeddings.py](ingestion/embeddings.py)

**What it does:**
- Creates OpenAI embeddings
- Caches results

**Reusable for documents:** ✅ Yes, works for any text

---

### 3. Document Chunker ⚠️
**File:** [ingestion/chunkers/document_chunker.py](ingestion/chunkers/document_chunker.py)

**What it does:**
- Splits long documents into chunks
- Maintains overlap between chunks

**Limitation:** No workflow intelligence! Just text splitting.

**Needs:** Replace with LLM-based workflow extractor

---

### 4. API Structure ✅
**File:** [api/endpoints/ingest.py](api/endpoints/ingest.py)

**Existing endpoints:**
- `POST /ingest/file` - Ingest single code file
- `POST /ingest/directory` - Ingest code directory
- `DELETE /namespace` - Delete namespace

**Needs:** Add `POST /ingest/document` endpoint for PDFs/docs

---

## Recommended Implementation Plan

### Phase 1: Basic PDF Ingestion (Week 1)
- [ ] Install PDF parsing library (pypdf2 or pymupdf)
- [ ] Create `PDFParser` class
- [ ] Extract text from PDF
- [ ] Send full text to LLM with prompt: "Extract steps from this guide"
- [ ] Parse LLM JSON response
- [ ] Store in Neo4j + Qdrant (reuse existing loaders)
- [ ] Create API endpoint: `POST /ingest/document`

**MVP Output:** Can upload PDF, get basic step extraction

---

### Phase 2: Workflow Intelligence (Week 2)
- [ ] Enhanced LLM prompts for dependency detection
- [ ] Parallel step detection algorithm
- [ ] Phase/section identification
- [ ] Time estimation extraction
- [ ] Graph relationship creation (DEPENDS_ON, PARALLEL_WITH)

**Output:** Full workflow graph like Flux demo, but automated

---

### Phase 3: Advanced Features (Week 3)
- [ ] Markdown support
- [ ] HTML/web page support
- [ ] Multi-document workflow linking
- [ ] Workflow validation (detect circular dependencies)
- [ ] Workflow visualization API
- [ ] Batch processing

**Output:** Production-ready document ingestion system

---

## Code Skeleton for Document Ingestion

### 1. Document Parser (NEW - Needs to be built)

```python
# ingestion/parsers/document_parser.py

from typing import Dict, List
import fitz  # PyMuPDF
from openai import OpenAI

class DocumentParser:
    """Parse documents and extract workflows using LLM."""

    def __init__(self):
        self.openai = OpenAI()

    def parse_pdf(self, pdf_path: str, namespace: str) -> Dict:
        """Parse PDF and extract workflow."""
        # 1. Extract text
        text = self._extract_text_from_pdf(pdf_path)

        # 2. Send to LLM for workflow extraction
        workflow = self._extract_workflow_with_llm(text)

        # 3. Validate and structure
        return self._structure_workflow(workflow, namespace)

    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF."""
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def _extract_workflow_with_llm(self, text: str) -> Dict:
        """Use LLM to extract workflow structure."""
        response = self.openai.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": """Extract workflow from document.
                Return JSON with:
                - phases: List of workflow phases
                - steps: List of steps with name, description, dependencies
                - Identify which steps can run in parallel
                """
            }, {
                "role": "user",
                "content": text
            }],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
```

---

### 2. Workflow Loader (NEW - Needs to be built)

```python
# ingestion/loaders/workflow_loader.py

class WorkflowLoader:
    """Load workflow data into Neo4j + Qdrant."""

    def load_workflow(self, workflow: Dict, namespace: str):
        """Store workflow in databases."""
        # 1. Create document node
        doc_id = self._create_document_node(workflow, namespace)

        # 2. Create phase nodes
        for phase in workflow["phases"]:
            phase_id = self._create_phase_node(phase, doc_id, namespace)

            # 3. Create step nodes
            for step in phase["steps"]:
                step_id = self._create_step_node(step, phase_id, namespace)

                # 4. Create dependency relationships
                self._create_dependencies(step, step_id)

                # 5. Create embeddings
                self._create_embedding(step, step_id, namespace)
```

---

### 3. API Endpoint (NEW - Needs to be built)

```python
# api/endpoints/ingest.py (add to existing file)

@router.post("/document", response_model=IngestResponse)
async def ingest_document(request: IngestDocumentRequest):
    """
    Ingest a document (PDF, Markdown, etc.) and extract workflow.

    This uses LLM to automatically extract steps, dependencies, and parallelism.
    """
    # 1. Validate file
    if not Path(request.file_path).exists():
        raise HTTPException(404, "File not found")

    # 2. Parse document
    parser = DocumentParser()
    workflow = parser.parse_pdf(request.file_path, request.namespace)

    # 3. Load into databases
    loader = WorkflowLoader()
    stats = loader.load_workflow(workflow, request.namespace)

    # 4. Return stats
    return IngestResponse(
        success=True,
        message=f"Extracted {stats['step_count']} steps",
        namespace=request.namespace,
        nodes_created=stats["nodes"],
        vectors_stored=stats["vectors"]
    )
```

---

## Answer to Your Question

### "Do we have that available today?"

**NO ❌** - FlowRAG does **NOT** have generic document ingestion today.

**What exists:**
- ✅ Code ingestion (Python, JavaScript, TypeScript)
- ✅ Infrastructure (Neo4j, Qdrant, API framework)
- ⚠️ Basic text chunking (no workflow intelligence)

**What's missing:**
- ❌ PDF parsing → workflow extraction
- ❌ LLM-based step detection
- ❌ Dependency inference
- ❌ Parallel step detection
- ❌ Document ingestion API

---

### "Do we have only code ingestion working?"

**YES ✅** - Only code ingestion is production-ready.

**For the Flux demo, we manually:**
1. Read the 51-page PDF
2. Extracted 33 steps by hand
3. Identified dependencies manually
4. Spotted parallel opportunities manually
5. Coded it into a Python dictionary
6. Then used automated ingestion to store it

**To make it a product, we need to automate steps 1-5 using LLMs.**

---

## Bottom Line

**Current State:**
- FlowRAG is a **code analysis tool** today
- Can analyze Python/JavaScript codebases
- Extracts functions, classes, call graphs
- **Cannot** ingest generic documents

**To become a document workflow product:**
- Need 2-3 weeks development
- Add LLM-based document parsing
- Build workflow extraction logic
- Create document ingestion API
- Then it works for **any** PDF/doc, not just code

**The Flux demo proved the concept works**, but it's not yet packaged as an out-of-the-box solution.
