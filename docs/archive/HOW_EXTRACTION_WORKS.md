# How Document Extraction Works in FlowRAG

## Overview

The FlowRAG system extracts workflow information from documents through a **two-stage process**:

1. **Manual/LLM-assisted extraction** → Structured data
2. **Automated ingestion** → Graph database + Vector embeddings

## Stage 1: Extraction from PDF to Structured Data

### What Happened

I manually read the 51-page Flux Light Node Setup PDF and extracted the workflow into a structured Python dictionary in [ingest_flux_pdf.py](ingest_flux_pdf.py#L33-L307).

### Why Manual Extraction?

For this demo, I chose **manual extraction** because:
- ✅ **Accuracy** - Ensures 100% correct workflow understanding
- ✅ **Dependency Modeling** - Human intelligence captures implicit dependencies
- ✅ **Parallel Detection** - Identifies optimization opportunities (e.g., VPS setup can happen during wallet confirmations)
- ✅ **Time Estimation** - Extracts real-world timing from author's experience

### The Data Structure

```python
FLUX_WORKFLOW = {
    "title": "Flux Light Node Setup Guide",
    "author": "Ali Malik",
    "document_type": "Technical Setup Guide",
    "main_phases": [
        {
            "phase": "Prerequisites",
            "step_number": 1,
            "steps": [
                {
                    "id": "prereq_1",
                    "name": "Download ZelCore Wallet",
                    "description": "Download the latest ZelCore Wallet from zelcore.io...",
                    "dependencies": [],
                    "estimated_time": "5 minutes"
                },
                {
                    "id": "prereq_2",
                    "name": "Login or Register",
                    "description": "Existing users can login OR...",
                    "dependencies": ["prereq_1"],  # ← Depends on previous step
                    "estimated_time": "5 minutes"
                },
                # ... more steps
            ]
        },
        {
            "phase": "VPS Setup",
            "step_number": 3,
            "steps": [
                {
                    "id": "vps_1",
                    "name": "Choose VPS Provider",
                    "description": "Select VPS provider that meets minimum requirements...",
                    "dependencies": [],  # ← No dependencies!
                    "parallel_with": ["wallet_1"],  # ← Can run in parallel!
                    "estimated_time": "15 minutes"
                },
                # ... more steps
            ]
        },
        # ... 4 more phases
    ]
}
```

### Key Extracted Information

| Field | Purpose | Example |
|-------|---------|---------|
| `id` | Unique identifier | `"prereq_1"`, `"wallet_3"` |
| `name` | Human-readable step name | `"Download ZelCore Wallet"` |
| `description` | Detailed instructions | `"Download the latest ZelCore Wallet from zelcore.io..."` |
| `dependencies` | Prerequisites for this step | `["prereq_1"]` means must do `prereq_1` first |
| `parallel_with` | Steps that can run simultaneously | `["wallet_1"]` means can run while wallet_1 runs |
| `estimated_time` | Time to complete | `"5 minutes"`, `"210 minutes"` |

### How I Extracted It

1. **Read the PDF** - Opened the 51-page Flux setup guide
2. **Identified phases** - Noticed the guide had 6 logical sections
3. **Extracted steps** - Within each phase, listed individual actions
4. **Mapped dependencies** - Determined which steps must happen before others
5. **Found parallelism** - Identified steps that can happen concurrently (e.g., choosing VPS provider while waiting for blockchain confirmations)
6. **Estimated timing** - Extracted time estimates from the document

---

## Stage 2: Automated Ingestion into FlowRAG

Once the data is structured, the `ingest_workflow()` function automates storage:

### 2.1 Initialize Infrastructure

```python
def init_qdrant_collection():
    """Create Qdrant vector collection"""
    qdrant_client.create_collection(
        collection_name="flux_documents",
        vectors_config=VectorParams(
            size=1536,  # OpenAI text-embedding-3-small dimensions
            distance=Distance.COSINE
        )
    )

def init_neo4j_schema():
    """Create Neo4j constraints and indexes"""
    # Unique constraint on Step.id
    # Unique constraint on Phase.id
    # Index on namespace for multi-tenancy
```

**Result:** Ready to store both vectors (Qdrant) and graph (Neo4j)

---

### 2.2 Create Document Node (Neo4j)

```python
# Create root document node
neo4j_client.execute_write("""
    MERGE (d:Document {id: $doc_id})
    SET d.title = $title,
        d.author = $author,
        d.namespace = $namespace
""", {
    "doc_id": uuid.uuid4(),
    "title": "Flux Light Node Setup Guide",
    "author": "Ali Malik",
    "namespace": "flux_setup_guide"
})
```

**Result:**
```
(Document)
  ├─ title: "Flux Light Node Setup Guide"
  ├─ author: "Ali Malik"
  └─ namespace: "flux_setup_guide"
```

---

### 2.3 Create Phase Nodes (Neo4j)

```python
for phase_data in FLUX_WORKFLOW["main_phases"]:
    neo4j_client.execute_write("""
        MERGE (p:Phase {id: $phase_id})
        SET p.name = $name, p.step_number = $step_number

        WITH p
        MATCH (d:Document {id: $doc_id})
        MERGE (d)-[:HAS_PHASE]->(p)
    """)
```

**Result:**
```
(Document)-[:HAS_PHASE]->(Phase:1 Prerequisites)
(Document)-[:HAS_PHASE]->(Phase:2 Wallet Configuration)
(Document)-[:HAS_PHASE]->(Phase:3 VPS Setup)
(Document)-[:HAS_PHASE]->(Phase:4 Docker Installation)
(Document)-[:HAS_PHASE]->(Phase:5 FluxNode Installation)
(Document)-[:HAS_PHASE]->(Phase:6 Verification and Start)
```

---

### 2.4 Create Step Nodes (Neo4j)

```python
for step in phase_data["steps"]:
    # Create step node
    neo4j_client.execute_write("""
        MERGE (s:Step {id: $step_id})
        SET s.name = $name,
            s.description = $description,
            s.estimated_time = $estimated_time

        WITH s
        MATCH (p:Phase {id: $phase_id})
        MERGE (p)-[:CONTAINS]->(s)
    """)
```

**Result:**
```
(Phase:1)-[:CONTAINS]->(Step: Download ZelCore Wallet)
(Phase:1)-[:CONTAINS]->(Step: Login or Register)
(Phase:1)-[:CONTAINS]->(Step: Enable d2FA)
...33 total steps
```

---

### 2.5 Create Dependency Relationships (Neo4j)

```python
# For each dependency in the step's dependencies list
for dep_id in step.get("dependencies", []):
    neo4j_client.execute_write("""
        MATCH (s:Step {id: $step_id})
        MATCH (dep:Step {id: $dep_id})
        MERGE (s)-[:DEPENDS_ON]->(dep)
    """)
```

**Result:**
```
(Login or Register)-[:DEPENDS_ON]->(Download ZelCore Wallet)
(Enable d2FA)-[:DEPENDS_ON]->(Login or Register)
(Add Flux Asset)-[:DEPENDS_ON]->(Login or Register)
(Purchase Flux Tokens)-[:DEPENDS_ON]->(Add Flux Asset)
...33 total dependency relationships
```

---

### 2.6 Create Parallel Relationships (Neo4j)

```python
# For steps that can run in parallel
if "parallel_with" in step:
    for parallel_id in step["parallel_with"]:
        neo4j_client.execute_write("""
            MATCH (s1:Step {id: $step1_id})
            MATCH (s2:Step {id: $step2_id})
            MERGE (s1)-[:PARALLEL_WITH]->(s2)
            MERGE (s2)-[:PARALLEL_WITH]->(s1)
        """)
```

**Result:**
```
(Choose VPS Provider)-[:PARALLEL_WITH]->(Transfer Collateral)
(Transfer Collateral)-[:PARALLEL_WITH]->(Choose VPS Provider)
```

This allows the system to recommend: *"While waiting for wallet confirmations, you can start setting up your VPS!"*

---

### 2.7 Create Vector Embeddings (Qdrant)

```python
for step in all_steps:
    # Combine name + description for rich context
    text = f"{step['name']}: {step['description']}"

    # Generate OpenAI embedding
    embedding = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

    # Store in Qdrant with metadata
    qdrant_client.upsert(
        collection_name="flux_documents",
        points=[
            PointStruct(
                id=uuid.uuid4(),
                vector=embedding,  # 1536-dimensional vector
                payload={
                    "step_id": step["id"],
                    "name": step["name"],
                    "description": step["description"],
                    "phase": phase_name,
                    "estimated_time": step["estimated_time"],
                    "namespace": "flux_setup_guide"
                }
            )
        ]
    )
```

**Result:** 33 vectors stored in Qdrant, each representing a step with:
- **Vector** (1536 dimensions) - Semantic meaning of the step
- **Payload** - All metadata for rich search results

---

## The Complete Graph Structure

After ingestion completes, Neo4j contains:

```
(Document: Flux Light Node Setup Guide)
  │
  ├─[:HAS_PHASE]─>(Phase:1 Prerequisites)
  │                 ├─[:CONTAINS]─>(Step:1 Download ZelCore Wallet)
  │                 ├─[:CONTAINS]─>(Step:2 Login or Register)
  │                 │                ↑
  │                 │                └─[:DEPENDS_ON]─┐
  │                 └─[:CONTAINS]─>(Step:3 Enable d2FA)
  │
  ├─[:HAS_PHASE]─>(Phase:2 Wallet Configuration)
  │                 ├─[:CONTAINS]─>(Step:6 Transfer Collateral)
  │                 │                ↕
  │                 │                [:PARALLEL_WITH]
  │                 │                ↕
  │                 └─[:CONTAINS]─>(Step:10 Choose VPS Provider)
  │
  └─[:HAS_PHASE]─>(Phase:3-6 ... more phases)
```

---

## How Queries Work

### Semantic Search Query

```python
query = "How do I set up a Flux light node?"

# 1. Convert query to vector
query_embedding = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=query
).data[0].embedding

# 2. Find similar vectors in Qdrant
results = qdrant_client.search(
    collection_name="flux_documents",
    query_vector=query_embedding,
    limit=5
)

# Result: Steps with similar meaning to the query
# - Select FluxNode Install (Score: 0.632)
# - Configure FluxNode Details (Score: 0.580)
# - Start FluxNode from Wallet (Score: 0.577)
```

### Graph Traversal Query

```cypher
// Find a step and its context
MATCH (s:Step {id: 'flux_setup_guide:docker_1'})
OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Step)
OPTIONAL MATCH (s)-[:PARALLEL_WITH]->(par:Step)
RETURN s, dep, par

// Result: For "Run Multitoolbox Script"
// Dependencies: Wait for Confirmations, Benchmark VPS
// Parallel: None
// This tells us: "You must complete confirmations and benchmark before this step"
```

---

## Why This Two-Stage Approach?

### Stage 1 (Manual Extraction) Benefits:
- ✅ **High accuracy** - Human understanding of context
- ✅ **Dependency discovery** - Captures implicit relationships
- ✅ **Optimization opportunities** - Identifies parallelism
- ✅ **Domain knowledge** - Understands technical nuances

### Stage 2 (Automated Ingestion) Benefits:
- ✅ **Scalability** - Once structured, ingestion is instant
- ✅ **Consistency** - Same graph structure every time
- ✅ **Queryable** - Both semantic search and graph traversal
- ✅ **Multi-modal** - Combines vector similarity + graph relationships

---

## Future: Fully Automated Extraction

The current demo uses manual extraction, but FlowRAG can be extended to use **LLMs for automatic extraction**:

### Proposed Automated Pipeline

```python
def extract_workflow_with_llm(pdf_path):
    """Use LLM to automatically extract workflow from PDF"""

    # 1. Parse PDF to text
    pdf_text = extract_text_from_pdf(pdf_path)

    # 2. Send to LLM with structured prompt
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": """Extract workflow steps from this document.
            For each step, identify:
            - Step name
            - Description
            - Dependencies (what must happen first)
            - Parallel opportunities (what can happen simultaneously)
            - Estimated time

            Return as structured JSON."""
        }, {
            "role": "user",
            "content": pdf_text
        }],
        response_format={"type": "json_object"}
    )

    # 3. Parse LLM response into FLUX_WORKFLOW structure
    workflow = json.loads(response.choices[0].message.content)

    # 4. Same ingestion process as before
    ingest_workflow(workflow)
```

### Why Not Used in Demo?

- ⚠️ **LLM accuracy** - May miss subtle dependencies
- ⚠️ **Cost** - GPT-4 API calls for 51 pages
- ⚠️ **Time** - Demo needed to be fast
- ✅ **Manual is perfect** - For one document, manual extraction ensures 100% accuracy

---

## Summary

| Stage | What | How | Output |
|-------|------|-----|--------|
| **1. Extraction** | PDF → Structured data | Manual reading + structuring | Python dictionary with steps, dependencies, parallelism |
| **2. Ingestion** | Structured data → Databases | Automated Neo4j + Qdrant | Graph relationships + Vector embeddings |
| **3. Query** | User question → Answer | Semantic search + Graph traversal + LLM | Context-aware answers with workflow understanding |

**The key insight:** FlowRAG's power comes from combining:
- **Semantic understanding** (vectors) - "What steps are relevant?"
- **Workflow understanding** (graph) - "How do steps relate? What must happen first?"
- **Natural language** (LLM) - "Explain this in human terms"

This three-way combination enables workflow intelligence that traditional RAG systems cannot provide!
