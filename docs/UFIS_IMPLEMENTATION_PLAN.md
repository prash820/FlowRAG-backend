# UFIS Implementation Plan
## From Current FlowRAG to Universal Flow Intelligence System

**Version**: 1.0.0
**Date**: 2025-11-12
**Status**: Strategic Implementation Document

---

## Executive Summary

This document provides a detailed gap analysis and implementation roadmap to transform FlowRAG (currently software-focused) into UFIS (Universal Flow Intelligence System) supporting all industries.

**Current State**: FlowRAG handles Python/JavaScript code with basic documentation support
**Target State**: UFIS handles any process flow from any industry with 20+ input formats
**Timeline**: 12-month phased rollout
**Investment**: Detailed resource requirements per phase

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Gap Analysis](#gap-analysis)
3. [Architecture Evolution](#architecture-evolution)
4. [Implementation Phases](#implementation-phases)
5. [Detailed Build Requirements](#detailed-build-requirements)
6. [Resource Requirements](#resource-requirements)
7. [Success Metrics](#success-metrics)

---

## Current State Analysis

### What We Have Today

#### ✅ **Core Infrastructure (Solid Foundation)**

**Storage Layer:**
- ✅ Neo4j integration (client, queries, schema)
- ✅ Qdrant integration (vector storage, search)
- ✅ Dual-storage architecture working

**Ingestion Pipeline:**
- ✅ Base parser framework (`ingestion/parsers/base.py`)
- ✅ Python code parser (AST-based, extracts functions, classes, imports)
- ✅ JavaScript parser (basic)
- ✅ Document chunker (text chunking with overlaps)
- ✅ Neo4j loader (loads parsed code into graph)
- ✅ Qdrant loader (loads embeddings into vectors)
- ✅ Embedding generation (OpenAI integration)

**Orchestration Layer:**
- ✅ Orchestration controller (coordinates retrieval)
- ✅ Intent classification (routes queries to appropriate handlers)
- ✅ Hybrid retriever (combines vector + graph search)
- ✅ Context assembler (assembles retrieved context)
- ✅ Flow analyzer (basic flow analysis - has FlowStep, FlowAnalysis models)

**API Layer:**
- ✅ FastAPI endpoints (query, ingest, flow, health)
- ✅ Authentication middleware
- ✅ Rate limiting
- ✅ API schemas (Pydantic models)

**Agent Layer:**
- ✅ LLM integration (OpenAI)
- ✅ SLM integration (Gemma 270M)

**Infrastructure:**
- ✅ Docker setup
- ✅ Configuration management
- ✅ Test framework (unit, integration, e2e)

**UI:**
- ✅ Basic web interface

---

### What's Currently Limited

#### ⚠️ **Software Development Only**

**Code Parsers:**
- ⚠️ Only Python and JavaScript (need: Java, Go, TypeScript, C++, etc.)
- ⚠️ No call graph extraction (critical gap - line 346-348 in python_parser.py returns empty list)
- ⚠️ No API route detection
- ⚠️ No control flow analysis (if/else, try/catch)
- ⚠️ No data flow tracking

**Document Support:**
- ⚠️ Basic text chunking only
- ⚠️ No structured workflow extraction
- ⚠️ No step numbering detection
- ⚠️ No dependency inference from text
- ⚠️ PDF support is basic (no visual element extraction)

**Flow Analysis:**
- ⚠️ Has models (FlowStep, FlowAnalysis) but limited implementation
- ⚠️ No parallel detection algorithms
- ⚠️ No critical path calculation
- ⚠️ No optimization recommendations

**Domain Support:**
- ⚠️ Only software code and basic documentation
- ⚠️ No domain-specific parsers (CAD, BOM, clinical protocols, etc.)

---

## Gap Analysis

### Critical Gaps to Fill

#### **GAP 1: Call Graph Extraction (HIGH PRIORITY)**
**Current State:** `_extract_calls()` returns empty list
**Required:**
- AST-based call detection (function invocations)
- Method call resolution
- Cross-file call tracking
- Async/await handling
- Import resolution for external calls

**Why Critical:** Without call graphs, we can't trace execution flows - the core value proposition

---

#### **GAP 2: Universal Input Parsers (HIGH PRIORITY)**
**Current State:** Only Python/JavaScript code parsers
**Required:**

**A. Code Parsers (Extend Software Support):**
- TypeScript parser (tree-sitter based)
- Java parser (tree-sitter based)
- Go parser (tree-sitter based)
- C/C++ parser (tree-sitter based)
- Rust parser (tree-sitter based)
- Ruby, PHP parsers (lower priority)

**B. Structured Data Parsers (New Domains):**
- CSV/Excel parser (universal - for BOMs, schedules, resource lists)
  - Detect column relationships
  - Infer dependencies from columns like "Prerequisite", "Depends On"
  - Handle hierarchical data (parent-child in columns)
- JSON/XML parser (universal - for configs, data exports)
  - Recursive structure traversal
  - Key-value relationship extraction
- SQL database connector (universal - for ERP, transaction logs)
  - Schema extraction (tables, columns, foreign keys)
  - Transaction flow analysis from logs
  - Query pattern detection

**C. Domain-Specific Parsers (Industry Expansion):**

**Manufacturing:**
- CAD file parser (STEP, IGES, STL formats)
  - Extract assembly hierarchy (part A contains parts B, C, D)
  - Detect fasteners, welds, joints (connection points)
  - Identify assembly sequence from constraints
- BOM (Bill of Materials) parser
  - Parse CSV/Excel BOMs
  - Extract part dependencies
  - Supplier information extraction
  - Lead time data
- PLM (Product Lifecycle Management) integration
  - Siemens Teamcenter API
  - PTC Windchill API
  - Dassault ENOVIA API

**Healthcare:**
- HL7/FHIR parser (healthcare data standard)
  - Extract patient data, medications, procedures
  - Care pathway reconstruction from EHR data
  - Lab result dependencies
- Clinical protocol parser
  - Parse PDF clinical guidelines
  - Extract treatment steps with medical NLP
  - Detect contraindications (dependencies)
  - Dosage calculations and timing
- Medical image metadata parser (DICOM)
  - Extract imaging workflows
  - Pre-procedure requirements

**Supply Chain:**
- EDIFACT parser (EDI - Electronic Data Interchange)
  - Purchase orders (850)
  - Shipping notices (856)
  - Invoices (810)
  - Extract transaction flows
- ERP integration
  - SAP API (BAPI/OData)
  - Oracle ERP Cloud API
  - Microsoft Dynamics API
  - Extract order flows, inventory movements
- Shipping manifest parser
  - Container tracking data
  - Port-to-port logistics
  - Multi-modal transport flows

**Construction:**
- BIM (Building Information Modeling) parser
  - IFC (Industry Foundation Classes) format
  - Revit file parsing (via API)
  - Extract construction tasks from model
  - Spatial dependencies (can't do X until Y is built)
- Project schedule parser
  - MS Project file format
  - Primavera P6 format
  - Extract task dependencies, critical path

**Legal:**
- Contract parser (PDF, DOCX)
  - Clause extraction using legal NLP
  - Obligation detection (shall, must, will)
  - Party identification
  - Deadline extraction
  - Cross-reference resolution
- Regulatory text parser
  - Parse GDPR, HIPAA, SOX regulations
  - Requirement extraction
  - Compliance mapping

**Financial:**
- Financial report parser (10-K, 10-Q filings)
  - XBRL format support
  - Extract financial flows
  - Transaction categorization
- GL (General Ledger) integration
  - Extract account hierarchies
  - Transaction flows between accounts
  - Approval workflow reconstruction

**D. Visual/Media Parsers (Cross-Domain):**
- Video parser
  - Speech-to-text (Whisper API)
  - Frame extraction (OpenCV)
  - Object detection (YOLO/SAM)
  - Action recognition for procedure videos
  - Temporal segmentation (detect step boundaries)
- Image parser (process diagrams, flowcharts)
  - OCR for text extraction (Tesseract/Google Vision)
  - Shape detection (arrows, boxes, diamonds)
  - Flowchart reconstruction
  - Convert visual flows to graph structure
- Audio parser
  - Speech-to-text
  - Speaker diarization (who said what)
  - Extract verbal instructions

---

#### **GAP 3: Universal Flow Extraction Engine (HIGH PRIORITY)**
**Current State:** Basic FlowAnalyzer with models but minimal logic
**Required:**

**A. Pattern Recognition System:**
- Sequential pattern detector
  - Numbered lists (1, 2, 3 or Step 1, Step 2)
  - Temporal language ("after", "before", "then", "next")
  - Alphabetical sequences (a, b, c)
- Dependency pattern detector
  - Explicit dependencies ("requires", "depends on", "prerequisite")
  - Implicit dependencies (from domain knowledge)
  - Temporal dependencies ("wait for", "after completion of")
- Parallel pattern detector
  - Explicit parallel ("simultaneously", "in parallel", "at the same time")
  - Implicit parallel (no shared dependencies)
  - Concurrent language ("while", "meanwhile")
- Conditional pattern detector
  - If/then patterns
  - Switch/case logic
  - Exception handling flows
- Loop pattern detector
  - Iterative processes ("repeat until", "for each")
  - Recursive dependencies

**B. Domain-Specific Flow Inference:**
- Manufacturing flow rules
  - Physical constraints (can't assemble before parts arrive)
  - Tool availability (only one robot can use Tool X at a time)
  - Quality gates (inspection must follow production)
- Clinical flow rules
  - Medical safety constraints (drug interactions)
  - Timing requirements (antibiotic within 1 hour of incision)
  - Prerequisite tests (ECG before cardiac surgery)
- Supply chain flow rules
  - Lead time calculations
  - Shipping route optimization
  - Inventory level triggers
- Legal flow rules
  - Regulatory deadlines
  - Sequential filing requirements
  - Party action dependencies

**C. LLM-Enhanced Inference:**
- Context understanding
  - Domain detection (is this manufacturing or healthcare?)
  - Terminology disambiguation (same word, different meaning)
- Implicit dependency extraction
  - "Before X can happen, Y must be done" (even if not explicitly stated)
  - Common sense reasoning ("can't paint before surface is clean")
- Ambiguity resolution
  - Multiple valid interpretations → ask clarifying questions
  - Confidence scoring

**D. Graph Construction Logic:**
- Node creation rules
  - When to create a Process node vs Resource node
  - Attribute extraction (duration, cost, risk)
  - Metadata population
- Relationship creation rules
  - REQUIRES vs PARALLEL_WITH vs USES
  - Confidence scoring for inferred relationships
- Validation rules
  - Detect circular dependencies
  - Detect unreachable nodes
  - Consistency checking

---

#### **GAP 4: Universal Graph Schema (MEDIUM PRIORITY)**
**Current State:** Schema is code-centric (CodeUnit, Function, Class)
**Required:**

**A. Universal Node Types:**
- Extend NodeLabel enum to support:
  - `Process` (universal step/task)
  - `Resource` (material, equipment, person, data)
  - `Constraint` (safety, regulatory, business rules)
  - `Document` (source documentation)
  - `Domain` (manufacturing, healthcare, etc.)

**B. Universal Properties:**
- Add domain-agnostic properties:
  - `domain: string` (manufacturing, healthcare, supply_chain, etc.)
  - `type: string` (domain-specific type)
  - `estimated_duration: duration`
  - `cost: decimal`
  - `risk_level: enum(low, medium, high, critical)`
  - `compliance_required: boolean`

**C. Universal Relationships:**
- Add relationship types:
  - `REQUIRES` (generic dependency)
  - `PARALLEL_WITH` (can run concurrently)
  - `USES` (uses a resource)
  - `CONSTRAINED_BY` (subject to constraint)
  - `DOCUMENTED_IN` (links to documentation)
  - `ALTERNATIVE_TO` (alternative path)

**D. Domain Metadata:**
- Store domain-specific attributes in flexible JSON properties
- Maintain schema versioning
- Support schema evolution

---

#### **GAP 5: API Simulator (NEW CAPABILITY)**
**Current State:** Doesn't exist
**Required:**

**A. Endpoint Analyzer:**
- Extract API routes from code graphs
  - FastAPI decorator detection
  - Flask route detection
  - Express route detection
- Analyze handler functions
  - Extract request/response schemas
  - Detect validation rules
  - Identify authentication requirements
  - Estimate latency from code complexity
- Side effect detection
  - Database writes
  - External API calls
  - Cache operations
  - Notifications

**B. Response Generator:**
- Schema-based generation
  - Pydantic model → fake data
  - JSON Schema → fake data
  - TypeScript types → fake data
- LLM-enhanced generation
  - Analyze handler logic
  - Generate contextually appropriate responses
- Flow-aware generation
  - Trace call chains
  - Simulate database queries
  - Model side effects

**C. State Manager:**
- In-memory data store for CRUD
  - Create, Read, Update, Delete operations
  - Relational consistency
  - Pagination, filtering, sorting
- Session management
  - User state tracking
  - Authentication simulation

**D. Mock Server:**
- FastAPI-based HTTP server
  - Dynamic endpoint registration
  - Middleware (CORS, auth, rate limiting)
  - OpenAPI spec generation
- Control interface
  - `/simulator/reset` - reset state
  - `/simulator/seed` - seed data
  - `/simulator/config` - configure behavior

---

#### **GAP 6: Flow Optimization Engine (NEW CAPABILITY)**
**Current State:** Basic flow models, no optimization
**Required:**

**A. Parallel Detection Algorithm:**
- Dependency graph analysis
  - Topological sort
  - Depth calculation (longest path from root)
  - Group nodes at same depth
- Resource conflict detection
  - Detect shared resources
  - Prevent simultaneous use conflicts
- Optimization scoring
  - Calculate time savings
  - Calculate cost savings

**B. Critical Path Algorithm:**
- Forward pass (earliest start times)
- Backward pass (latest finish times)
- Slack calculation (float time)
- Critical path identification

**C. Bottleneck Detection:**
- Single point of failure identification
- Resource utilization analysis
- Throughput calculation

**D. Optimization Recommendations:**
- Parallel opportunities
- Resource reallocation
- Alternative path suggestions
- Risk mitigation strategies

---

#### **GAP 7: Query Intelligence (ENHANCEMENT)**
**Current State:** Basic intent classification
**Required:**

**A. Domain-Aware Query Routing:**
- Detect domain from query context
- Route to domain-specific handlers
- Apply domain vocabulary

**B. Cross-Domain Insights:**
- Apply manufacturing optimizations to healthcare
- Benchmark against similar processes in other domains
- Best practice recommendations

**C. Natural Language Understanding:**
- Support domain-specific terminology
- Handle abbreviations and acronyms
- Context-aware interpretation

**D. Query Types:**
- Optimization queries ("how can we speed up?")
- Dependency queries ("what depends on X?")
- Risk queries ("what are single points of failure?")
- Simulation queries ("what if we skip step 5?")
- Comparison queries ("compare process A vs B")

---

#### **GAP 8: Domain Plugin System (NEW ARCHITECTURE)**
**Current State:** Monolithic codebase
**Required:**

**A. Plugin Architecture:**
- Plugin discovery mechanism
  - Scan plugins directory
  - Load plugins dynamically
  - Register parsers, analyzers, validators
- Plugin manifest
  - Define supported input formats
  - Define node/relationship types
  - Define validation rules
- Plugin versioning
  - Semantic versioning
  - Dependency management
  - Compatibility checking

**B. Domain Plugin Template:**
- Base classes for domain plugins
  - `DomainParser` (extends BaseParser)
  - `DomainFlowAnalyzer` (extends FlowAnalyzer)
  - `DomainValidator` (validation rules)
- Configuration schema
  - Domain-specific settings
  - API credentials for integrations
  - Parsing rules

**C. Plugin Marketplace:**
- Plugin registry
  - Discover available plugins
  - Install/uninstall
  - Update mechanism
- Community contributions
  - Submit new domain plugins
  - Rate and review plugins

---

#### **GAP 9: Visualization System (NEW CAPABILITY)**
**Current State:** No visualization
**Required:**

**A. Flow Visualization:**
- Interactive graph rendering
  - D3.js or Cytoscape.js for web
  - Zoom, pan, filter controls
- Layout algorithms
  - Hierarchical layout for sequential flows
  - Force-directed for complex dependencies
  - Swimlane for parallel processes
- Visual encodings
  - Color by criticality (red = critical path)
  - Size by duration
  - Shape by type

**B. Timeline View:**
- Gantt chart for sequential processes
- Highlight parallel sections
- Show dependencies with arrows

**C. Metrics Dashboard:**
- Key performance indicators
  - Total duration (sequential vs optimized)
  - Resource utilization
  - Bottleneck locations
- Real-time updates
- Export capabilities (PDF, PNG, SVG)

---

#### **GAP 10: Validation & Quality Assurance (ENHANCEMENT)**
**Current State:** Basic tests
**Required:**

**A. Flow Validation:**
- Circular dependency detection
- Unreachable node detection
- Deadlock detection (resource conflicts)
- Consistency checking

**B. Domain-Specific Validation:**
- Manufacturing: physical impossibilities
- Healthcare: medical safety checks
- Supply chain: lead time validation
- Legal: regulatory compliance

**C. Quality Metrics:**
- Parser accuracy measurement
- Dependency inference confidence
- Optimization effectiveness
- User satisfaction scoring

---

## Architecture Evolution

### Current Architecture (FlowRAG)

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT FLOWRAG                           │
└─────────────────────────────────────────────────────────────┘

Input: Python/JS Code + Basic Docs
         ↓
Parsers: PythonParser, JavaScriptParser, DocumentChunker
         ↓
Loaders: Neo4jLoader, QdrantLoader
         ↓
Storage: Neo4j (CodeUnit, Function, Class) + Qdrant (embeddings)
         ↓
Orchestrator: IntentClassifier → HybridRetriever → ContextAssembler
         ↓
API: Query, Ingest, Flow, Health endpoints
         ↓
UI: Basic web interface
```

### Target Architecture (UFIS)

```
┌─────────────────────────────────────────────────────────────┐
│          UNIVERSAL FLOW INTELLIGENCE SYSTEM (UFIS)           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      INPUT LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Universal Input Router                                      │
│  ├─ File type detection                                     │
│  ├─ Domain detection                                        │
│  └─ Route to appropriate parser                             │
│                                                              │
│  Code Parsers (Tree-sitter based)                           │
│  ├─ Python, JavaScript, TypeScript, Java, Go, C++, Rust    │
│  └─ Call graph extraction, API routes, control flow        │
│                                                              │
│  Structured Data Parsers                                    │
│  ├─ CSV/Excel (BOMs, schedules, resources)                 │
│  ├─ JSON/XML (configs, data exports)                       │
│  └─ SQL (database schemas, transactions)                    │
│                                                              │
│  Domain Plugins (Dynamically Loaded)                        │
│  ├─ Manufacturing (CAD, BOM, PLM)                          │
│  ├─ Healthcare (HL7/FHIR, clinical protocols)              │
│  ├─ Supply Chain (EDIFACT, ERP, shipping)                  │
│  ├─ Legal (contracts, regulations)                          │
│  ├─ Financial (XBRL, GL, reports)                          │
│  ├─ Construction (BIM, schedules)                           │
│  └─ Scientific (protocols, grants)                          │
│                                                              │
│  Visual/Media Parsers                                       │
│  ├─ Video (speech-to-text, action recognition)             │
│  ├─ Image (OCR, flowchart detection)                       │
│  └─ Audio (transcription, speaker detection)                │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Universal Flow Extraction Engine                           │
│  ├─ Pattern Recognition (sequential, parallel, conditional) │
│  ├─ Dependency Inference (explicit + implicit)              │
│  ├─ LLM-Enhanced Understanding (context, disambiguation)    │
│  └─ Graph Construction (nodes, relationships, validation)   │
│                                                              │
│  Domain-Specific Analyzers (Plugin-Based)                   │
│  ├─ Manufacturing Flow Rules                                │
│  ├─ Clinical Safety Rules                                   │
│  ├─ Supply Chain Optimization                               │
│  └─ Legal Compliance Checks                                 │
│                                                              │
│  Flow Optimization Engine                                   │
│  ├─ Parallel Detection Algorithm                            │
│  ├─ Critical Path Calculation                               │
│  ├─ Bottleneck Detection                                    │
│  └─ Optimization Recommendations                            │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Neo4j (Universal Graph Schema)                             │
│  ├─ Nodes: Process, Resource, Constraint, Document, Domain │
│  ├─ Relationships: REQUIRES, PARALLEL_WITH, USES, etc.     │
│  └─ Domain-specific attributes in JSON properties           │
│                                                              │
│  Qdrant (Semantic Embeddings)                               │
│  ├─ Domain-aware collections                                │
│  ├─ Metadata: domain, type, namespace                       │
│  └─ Cross-domain semantic search                            │
│                                                              │
│  Redis (Caching & Sessions)                                 │
│  └─ Query cache, API simulator state                        │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                      QUERY LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Intelligent Query Engine                                   │
│  ├─ Domain Detection                                        │
│  ├─ Intent Classification (optimization, dependency, etc.)  │
│  ├─ Query Routing (domain-specific handlers)                │
│  └─ LLM-Enhanced Explanations                               │
│                                                              │
│  Flow Query Handlers                                        │
│  ├─ Parallel Detection Queries                              │
│  ├─ Dependency Traversal                                    │
│  ├─ Risk Assessment                                         │
│  └─ Simulation (what-if scenarios)                          │
│                                                              │
│  API Simulator (Software Domain)                            │
│  ├─ Endpoint Analyzer                                       │
│  ├─ Response Generator                                      │
│  ├─ State Manager                                           │
│  └─ Mock Server                                             │
│                                                              │
│  Cross-Domain Insights                                      │
│  └─ Apply patterns from one domain to another               │
└─────────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────────┐
│                   INTERFACE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  REST API                                                    │
│  ├─ /ingest (universal - all formats)                       │
│  ├─ /query (flow-aware, domain-aware)                       │
│  ├─ /optimize (recommendations)                             │
│  ├─ /simulate (API mocking + what-if scenarios)             │
│  └─ /visualize (flow diagrams, timelines)                   │
│                                                              │
│  Web UI                                                      │
│  ├─ Domain Selector                                         │
│  ├─ Flow Visualization (interactive graphs)                 │
│  ├─ Query Interface                                         │
│  └─ Optimization Dashboard                                  │
│                                                              │
│  CLI                                                         │
│  └─ ufis ingest|query|optimize|simulate                     │
│                                                              │
│  Plugin Marketplace                                          │
│  └─ Discover, install, manage domain plugins                │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 0: Foundation Fixes (Weeks 1-2)
**Goal:** Fix critical gaps in existing code

**Tasks:**
1. Implement call graph extraction in Python parser
2. Add API route detection
3. Enhance flow analyzer with basic algorithms
4. Add integration tests for core functionality

**Deliverables:**
- Working call graph extraction
- API endpoint detection working
- Flow analyzer can detect parallel opportunities

---

### Phase 1: Universal Core (Weeks 3-6)
**Goal:** Build universal extraction engine

**Tasks:**
1. Design universal graph schema
2. Build pattern recognition system
3. Create universal flow extraction engine
4. Implement dependency inference
5. Add LLM-enhanced understanding

**Deliverables:**
- Universal graph schema implemented
- Pattern recognition working across domains
- Flow extraction engine operational

---

### Phase 2: First Non-Software Domain (Weeks 7-10)
**Goal:** Prove UFIS works beyond software (Manufacturing pilot)

**Tasks:**
1. Build CSV/Excel parser (for BOMs, schedules)
2. Create manufacturing plugin template
3. Implement manufacturing flow rules
4. Run pilot with automotive assembly line
5. Document case study

**Deliverables:**
- Manufacturing plugin working
- Pilot shows measurable improvement
- Case study demonstrates value

---

### Phase 3: Multi-Language Code Support (Weeks 11-14)
**Goal:** Complete software domain support

**Tasks:**
1. Add TypeScript, Java, Go parsers (tree-sitter)
2. Complete call graph extraction for all languages
3. API route detection for multiple frameworks
4. Control flow analysis

**Deliverables:**
- 6+ programming languages supported
- Complete code flow analysis

---

### Phase 4: API Simulator (Weeks 15-18)
**Goal:** Build on-demand API mocking

**Tasks:**
1. Endpoint analyzer
2. Response generator (schema-based + LLM)
3. State manager
4. Mock server with FastAPI

**Deliverables:**
- Working API simulator
- Can mock any analyzed API

---

### Phase 5: Healthcare Domain (Weeks 19-22)
**Goal:** Expand to second major domain

**Tasks:**
1. HL7/FHIR parser
2. Clinical protocol parser (medical NLP)
3. Healthcare flow rules (safety constraints)
4. Pilot with surgical protocol

**Deliverables:**
- Healthcare plugin working
- Clinical pathway optimization demonstrated

---

### Phase 6: Supply Chain Domain (Weeks 23-26)
**Goal:** Expand to third major domain

**Tasks:**
1. EDIFACT parser (EDI)
2. ERP integration (SAP, Oracle)
3. Supply chain flow rules
4. Pilot with electronics supply chain

**Deliverables:**
- Supply chain plugin working
- Supply chain mapping demonstrated

---

### Phase 7: Visualization System (Weeks 27-30)
**Goal:** Make flows visible and interactive

**Tasks:**
1. Interactive graph visualization
2. Timeline/Gantt view
3. Metrics dashboard
4. Export capabilities

**Deliverables:**
- Beautiful flow visualizations
- Interactive exploration

---

### Phase 8: Plugin Marketplace (Weeks 31-34)
**Goal:** Enable community contributions

**Tasks:**
1. Plugin architecture finalization
2. Plugin discovery and installation
3. Marketplace UI
4. Documentation for plugin developers

**Deliverables:**
- Plugin system working
- Marketplace launched
- 3rd party plugins possible

---

### Phase 9: Optimization Engine (Weeks 35-38)
**Goal:** Automated flow optimization

**Tasks:**
1. Parallel detection algorithm
2. Critical path calculation
3. Bottleneck detection
4. Optimization recommendations

**Deliverables:**
- Automated optimization working
- Measurable improvements in pilot projects

---

### Phase 10: Additional Domains (Weeks 39-48)
**Goal:** Expand to 5+ domains

**Tasks:**
1. Legal domain plugin
2. Financial domain plugin
3. Construction domain plugin
4. Scientific research plugin
5. Energy/utilities plugin

**Deliverables:**
- 8+ domains supported
- Cross-domain insights working

---

### Phase 11: Production Hardening (Weeks 49-52)
**Goal:** Enterprise-ready platform

**Tasks:**
1. Performance optimization
2. Security hardening
3. Multi-tenancy support
4. SSO integration
5. Audit logging
6. Compliance certifications

**Deliverables:**
- Production-ready platform
- SOC 2 compliance
- Enterprise customers onboarded

---

## Detailed Build Requirements

### 1. Universal Input Router

**Purpose:** Detect file type and domain, route to appropriate parser

**Requirements:**
- File extension detection (.py, .csv, .step, .pdf, etc.)
- Content-based type detection (magic bytes, file headers)
- Domain hint system (user can specify domain)
- Auto-domain detection (analyze content to infer domain)
- Parser registry (map file types to parsers)
- Error handling (unsupported format → friendly message)

**Inputs:**
- File path or file content
- Optional domain hint
- Optional parser override

**Outputs:**
- Detected file type
- Detected domain
- Selected parser instance

**Integration Points:**
- Used by all ingest endpoints
- Called before any parsing

---

### 2. Tree-sitter Parser Framework

**Purpose:** Unified parser for multiple programming languages

**Requirements:**
- Tree-sitter bindings for Python
- Grammar files for: TypeScript, Java, Go, C++, Rust
- AST traversal utilities
- Call site extraction (function invocations)
- Import resolution
- Symbol table building

**Inputs:**
- Source code string
- Language identifier

**Outputs:**
- AST (abstract syntax tree)
- Symbol table (functions, classes, variables)
- Call graph edges (caller → callee)

**Integration Points:**
- Extends BaseParser
- Used by language-specific parsers

---

### 3. CSV/Excel Structured Parser

**Purpose:** Parse tabular data (BOMs, schedules, resource lists)

**Requirements:**
- Read CSV, Excel (.xlsx, .xls), TSV formats
- Header detection (auto-detect or user-specified)
- Column relationship inference
  - Detect "ID" columns
  - Detect "Prerequisite" or "Depends On" columns
  - Detect "Parent" columns (hierarchical data)
- Data type inference (text, number, date, duration)
- Handle merged cells in Excel
- Multi-sheet support

**Heuristics:**
- Column named "Prerequisite", "Depends On", "Requires" → dependency
- Column named "Duration", "Time", "Estimated Time" → duration
- Column named "Step", "Task", "Phase" → process name
- Column named "Part", "Component", "Item" → resource
- Numeric sequence in first column → step order

**Inputs:**
- CSV/Excel file path
- Optional column mapping (user specifies which columns mean what)

**Outputs:**
- List of Process nodes
- List of Resource nodes
- List of REQUIRES relationships
- Attributes (duration, cost, etc.)

**Integration Points:**
- Universal parser registry
- Used across manufacturing, supply chain, project management

---

### 4. CAD File Parser (Manufacturing)

**Purpose:** Extract assembly structure from CAD files

**Requirements:**
- STEP file format support (ISO 10303)
  - Parse geometric data
  - Extract assembly tree
  - Identify parts and sub-assemblies
- Detect constraints and mates
  - Fasteners (screws, bolts)
  - Welds
  - Adhesives
  - Snap fits
- Infer assembly sequence
  - Parts with most connections = early assembly
  - Enclosed parts = must be inserted before enclosing parts

**Approach:**
- Use pythonOCC library (Open CASCADE wrapper)
- Parse STEP file to extract:
  - Product structure (assembly hierarchy)
  - Shape definitions (geometry)
  - Relationships (mates, constraints)

**Inputs:**
- STEP file path

**Outputs:**
- Assembly hierarchy graph
- Part nodes with geometry metadata
- REQUIRES relationships based on assembly order
- Resource requirements (tools needed)

**Integration Points:**
- Manufacturing plugin
- Linked to BOM data

---

### 5. HL7/FHIR Parser (Healthcare)

**Purpose:** Parse healthcare data standards

**Requirements:**
- HL7 v2 message parsing (pipe-delimited)
  - ADT messages (patient admission/discharge)
  - ORM messages (orders)
  - ORU messages (results)
- FHIR resource parsing (JSON/XML)
  - Patient resources
  - Medication resources
  - Procedure resources
  - CarePlan resources
- Extract care pathways
  - Order of procedures
  - Medication schedules
  - Lab test dependencies

**Approach:**
- Use python-hl7 library for HL7 v2
- Use fhirclient library for FHIR
- Map to universal graph:
  - Procedure → Process node
  - Medication → Resource node
  - Contraindications → Constraint node

**Inputs:**
- HL7 message or FHIR bundle

**Outputs:**
- Process nodes (procedures, medications)
- REQUIRES relationships (procedure dependencies)
- CONSTRAINED_BY (contraindications, allergies)

**Integration Points:**
- Healthcare plugin
- Clinical protocol analysis

---

### 6. Contract Parser (Legal)

**Purpose:** Extract obligations from legal contracts

**Requirements:**
- PDF/DOCX parsing
- Legal NLP for obligation detection
  - Modal verbs: "shall", "must", "will", "may"
  - Party identification: "Vendor shall...", "Client must..."
  - Action extraction: what must be done
- Deadline extraction
  - Absolute dates: "by December 31, 2025"
  - Relative dates: "within 30 days of..."
  - Event-based: "upon completion of..."
- Cross-reference resolution
  - "As specified in Section 5.2..."
  - Link obligations to referenced sections

**Approach:**
- Use spaCy with legal NLP model
- Pattern matching for obligation language
- Dependency parsing to extract subjects and actions
- Date entity recognition

**Inputs:**
- PDF or DOCX contract file

**Outputs:**
- Process nodes (obligations)
- Party nodes (vendor, client, etc.)
- REQUIRES relationships (obligation dependencies)
- Deadline attributes

**Integration Points:**
- Legal plugin
- Contract lifecycle management

---

### 7. Video Procedure Parser

**Purpose:** Extract workflows from demonstration videos

**Requirements:**
- Video transcription (speech-to-text)
  - Use OpenAI Whisper or Google Speech-to-Text
  - Speaker diarization (who is speaking)
- Frame analysis (visual understanding)
  - Extract key frames at speech boundaries
  - Object detection (tools, materials used)
  - Action recognition (cutting, assembling, testing)
- Temporal segmentation
  - Detect when a new step begins
  - Use audio cues ("First, we...", "Next, you...")
  - Use visual cues (scene changes, camera angles)
- Step extraction
  - Combine transcript + visual analysis
  - Generate step descriptions
  - Infer sequence from temporal order

**Approach:**
- Use OpenCV for frame extraction
- Use Whisper for transcription
- Use YOLO or SAM for object detection
- Use LLM to synthesize transcript + visual into steps

**Inputs:**
- Video file (MP4, AVI, MOV)

**Outputs:**
- Process nodes (steps extracted from video)
- Resource nodes (tools/materials visible)
- Sequential relationships (NEXT)

**Integration Points:**
- Training content analysis
- Manufacturing work instructions
- Medical procedure videos

---

### 8. Universal Flow Extraction Engine

**Purpose:** Core intelligence - extract flows from any source

**Architecture:**

```
UniversalFlowExtractor
├─ PatternRecognizer
│  ├─ SequentialPatternDetector
│  ├─ DependencyPatternDetector
│  ├─ ParallelPatternDetector
│  ├─ ConditionalPatternDetector
│  └─ LoopPatternDetector
├─ DomainRuleEngine
│  └─ Load rules from domain plugins
├─ LLMEnhancer
│  ├─ ContextUnderstanding
│  ├─ ImplicitInference
│  └─ AmbiguityResolution
└─ GraphConstructor
   ├─ NodeFactory
   ├─ RelationshipFactory
   └─ Validator
```

**Requirements:**

**A. SequentialPatternDetector:**
- Regex patterns for numbered lists
- NLP patterns for temporal language
- Detect step ordering

**B. DependencyPatternDetector:**
- Pattern matching: "requires", "depends on", "prerequisite"
- Parse syntax: "X requires Y" → REQUIRES(X, Y)
- Confidence scoring

**C. ParallelPatternDetector:**
- Pattern matching: "simultaneously", "in parallel", "concurrently"
- Inference: if no shared dependencies, can be parallel
- Resource conflict checking

**D. LLMEnhancer:**
- Prompt engineering for flow extraction
- Few-shot examples per domain
- Structured output (JSON with steps, dependencies)

**E. GraphConstructor:**
- Create Process nodes from extracted steps
- Create Resource nodes from extracted resources
- Create REQUIRES relationships from dependencies
- Validate: no cycles, no orphans

**Inputs:**
- Parsed data (from any parser)
- Domain identifier
- Optional user hints

**Outputs:**
- Graph structure (nodes + relationships)
- Confidence scores
- Validation warnings

**Integration Points:**
- Called by all parsers after extraction
- Outputs to Neo4j loader

---

### 9. Flow Optimization Engine

**Purpose:** Analyze flows and recommend optimizations

**Requirements:**

**A. Parallel Detection:**
- Build dependency graph
- Topological sort to find execution order
- Calculate depth for each node (longest path from start)
- Group nodes at same depth (parallel candidates)
- Check resource conflicts
- Output: list of parallel groups

**B. Critical Path:**
- Forward pass: calculate earliest start time for each node
- Backward pass: calculate latest finish time for each node
- Slack = latest finish - earliest start
- Critical path = nodes with zero slack
- Output: list of critical path nodes, total duration

**C. Bottleneck Detection:**
- Find nodes with high fan-in (many dependencies)
- Find nodes with high fan-out (many dependents)
- Find resource constraints (single resource used by many steps)
- Output: ranked list of bottlenecks

**D. Optimization Recommendations:**
- If parallel groups exist: "Steps X, Y, Z can run in parallel (saves N hours)"
- If bottleneck exists: "Step B is a bottleneck, consider adding resources"
- If critical path has slack elsewhere: "Focus on critical path steps"
- Output: list of actionable recommendations

**Inputs:**
- Flow graph (from Neo4j)
- Duration estimates per node
- Resource constraints

**Outputs:**
- Parallel groups
- Critical path
- Bottlenecks
- Recommendations
- Estimated time savings

**Integration Points:**
- Called by query engine for optimization queries
- Used in visualization (color critical path)

---

### 10. API Simulator Components

**Purpose:** Generate mock APIs from analyzed code

**Components:**

**A. Endpoint Analyzer:**
- Query Neo4j for APIEndpoint nodes
- For each endpoint:
  - Get handler function
  - Get call chain (functions called by handler)
  - Extract request/response schemas (from code or docstrings)
  - Detect authentication (look for auth decorators)
  - Estimate latency (based on call depth + DB queries)
  - Detect side effects (DB writes, external calls)

**B. Response Generator:**
- Schema-based: given JSON schema, generate fake data
  - Use Faker library for realistic data
  - Respect constraints (min/max, enum, regex)
- LLM-based: given handler code, generate contextual response
  - Analyze logic to understand what response should contain
  - Generate realistic business data
- Flow-aware: trace call chain to simulate behavior
  - If handler calls get_user(id) → simulate user lookup
  - If handler calls send_email() → log simulated email

**C. State Manager:**
- In-memory dict: {resource_type: {id: data}}
- CRUD operations:
  - Create: add to dict
  - Read: retrieve from dict
  - Update: modify in dict
  - Delete: remove from dict
- Pagination, filtering, sorting

**D. Mock Server:**
- FastAPI app instance
- Dynamically register routes from analyzed endpoints
- For each route, create async handler that:
  - Simulates latency (asyncio.sleep)
  - Generates response
  - Simulates side effects
  - Returns JSON response

**Inputs:**
- Namespace (which codebase to mock)

**Outputs:**
- Running HTTP server on specified port
- OpenAPI spec at /docs
- Control endpoints at /simulator/*

**Integration Points:**
- Uses Neo4j to query APIEndpoint nodes
- Uses LLM for intelligent response generation

---

### 11. Domain Plugin System

**Purpose:** Allow adding new domains without modifying core

**Requirements:**

**A. Plugin Structure:**
```
plugins/
├─ manufacturing/
│  ├─ plugin.yaml (manifest)
│  ├─ parsers.py (CAD, BOM parsers)
│  ├─ analyzers.py (manufacturing flow rules)
│  ├─ validators.py (physical constraint checks)
│  └─ requirements.txt (plugin dependencies)
├─ healthcare/
│  ├─ plugin.yaml
│  ├─ parsers.py (HL7, FHIR, protocols)
│  ├─ analyzers.py (clinical flow rules)
│  └─ validators.py (medical safety checks)
└─ ...
```

**B. Plugin Manifest (plugin.yaml):**
```yaml
name: manufacturing
version: 1.0.0
description: Manufacturing domain support
author: UFIS Team

parsers:
  - name: CADParser
    formats: [.step, .iges, .stl]
    class: parsers.CADParser
  - name: BOMParser
    formats: [.csv, .xlsx]
    class: parsers.BOMParser

analyzers:
  - name: ManufacturingFlowAnalyzer
    class: analyzers.ManufacturingFlowAnalyzer

validators:
  - name: PhysicalConstraintValidator
    class: validators.PhysicalConstraintValidator

dependencies:
  - pythonOCC>=7.5.0
  - pandas>=1.3.0
```

**C. Plugin Discovery:**
- Scan `plugins/` directory at startup
- Load all plugin.yaml files
- Validate manifest structure
- Check dependency availability
- Register parsers, analyzers, validators

**D. Plugin API:**
- Base classes that plugins extend:
  - `DomainParser(BaseParser)`
  - `DomainFlowAnalyzer(FlowAnalyzer)`
  - `DomainValidator(BaseValidator)`
- Lifecycle hooks:
  - `on_load()` - called when plugin loads
  - `on_unload()` - cleanup
  - `on_parse()` - called during parsing
  - `on_analyze()` - called during analysis

**Integration Points:**
- Plugin loader called at startup
- Parsers registered in universal router
- Analyzers called in flow extraction

---

### 12. Visualization System

**Purpose:** Make flows visible and explorable

**Requirements:**

**A. Graph Visualization:**
- Frontend: React + Cytoscape.js
- Features:
  - Zoom, pan, filter controls
  - Node clustering (group by domain, type)
  - Edge bundling (reduce visual clutter)
  - Search/highlight nodes
  - Click node → show details panel
- Layout algorithms:
  - Hierarchical (sequential flows)
  - Force-directed (complex dependencies)
  - Circular (cyclical processes)
- Visual encoding:
  - Color: by domain or criticality
  - Size: by duration or cost
  - Shape: by type (process, resource, constraint)
  - Border: critical path = red border

**B. Timeline View:**
- Gantt chart for temporal flows
- X-axis: time
- Y-axis: tasks
- Bars: task duration
- Arrows: dependencies
- Highlight parallel sections (overlapping bars)
- Interactive: drag to reschedule (what-if)

**C. Metrics Dashboard:**
- Key metrics cards:
  - Total duration (sequential)
  - Optimized duration (parallel)
  - Time savings (%)
  - Number of parallel groups
  - Bottleneck count
- Charts:
  - Resource utilization over time
  - Critical path breakdown
  - Risk heatmap
- Export: PDF report, PNG images

**Integration Points:**
- Backend API: `/visualize` endpoint
- Queries Neo4j for graph data
- Runs optimization engine for metrics
- Returns JSON for frontend

---

## Resource Requirements

### Team Composition (Full Build - 12 Months)

**Core Team (Full-time):**
- 1 Tech Lead / Architect
- 2 Backend Engineers (Python, graph databases)
- 1 Frontend Engineer (React, visualization)
- 1 ML/NLP Engineer (LLM integration, NLP)
- 1 DevOps Engineer (infrastructure, CI/CD)
- 1 QA Engineer (testing, validation)

**Domain Specialists (Part-time consultants):**
- Manufacturing expert (Phase 2 - 3 months)
- Healthcare expert (Phase 5 - 3 months)
- Supply chain expert (Phase 6 - 2 months)
- Legal expert (Phase 10 - 2 months)

**Total Team Cost (Estimated):**
- Core team: 7 FTE × $150K avg × 12 months = $1.05M
- Domain specialists: $100K consulting fees
- **Total Personnel: $1.15M**

**Infrastructure Costs:**
- Cloud hosting (AWS/GCP): $2K/month × 12 = $24K
- Neo4j Enterprise license: $15K/year
- LLM API costs (OpenAI): $5K/month × 12 = $60K
- Development tools: $5K
- **Total Infrastructure: $104K**

**Total Investment:** ~$1.25M for full build

---

### Phased Investment (Minimum Viable Build)

**Phase 0-1 (Months 1-2): Foundation + Universal Core**
- Team: 3 engineers (tech lead, 2 backend)
- Cost: $75K
- Deliverable: Universal flow extraction working

**Phase 2 (Months 3-4): Manufacturing Pilot**
- Team: 3 engineers + 1 manufacturing consultant
- Cost: $75K
- Deliverable: Manufacturing plugin, case study showing ROI

**Pause & Evaluate:**
- If manufacturing pilot shows >20% improvement → proceed
- If not → iterate on Phase 2

**Phase 3-11 (Months 5-12): Full Build**
- Team: 7 FTE
- Cost: $700K
- Deliverable: Multi-domain UFIS

**Minimum Viable Investment:** $150K (Phases 0-2) to prove concept

---

## Success Metrics

### Phase 0-1: Foundation
- ✅ Call graph extraction: 95%+ accuracy
- ✅ Pattern detection: 90%+ recall
- ✅ Flow extraction: works on test cases

### Phase 2: Manufacturing Pilot
- ✅ Time savings: >20% reduction in process duration
- ✅ Cost savings: >$1M annually for pilot customer
- ✅ Accuracy: 85%+ dependency detection
- ✅ Customer satisfaction: 8/10+ rating

### Phase 11: Full Platform
- ✅ Domains supported: 8+
- ✅ Input formats: 20+
- ✅ Paying customers: 100+
- ✅ ARR: $1M+
- ✅ User retention: 90%+

---

## Risk Mitigation

### Technical Risks

**Risk 1: Parser accuracy too low**
- Mitigation: Start with structured data (CSV, JSON) - easier to parse
- Mitigation: Use LLM as fallback for ambiguous cases
- Mitigation: Allow user corrections (supervised learning)

**Risk 2: Domain expertise gaps**
- Mitigation: Hire domain consultants per phase
- Mitigation: Partner with domain-specific software vendors
- Mitigation: Start with well-documented domains (manufacturing standards exist)

**Risk 3: Scalability issues**
- Mitigation: Design for scalability from day 1 (distributed architecture)
- Mitigation: Use Neo4j sharding, Qdrant clustering
- Mitigation: Performance testing early and often

### Business Risks

**Risk 1: Market not ready for universal platform**
- Mitigation: Start with software domain (proven market)
- Mitigation: Expand to one domain at a time (validate each)
- Mitigation: Build domain plugins - can sell separately

**Risk 2: Competition from domain-specific vendors**
- Mitigation: Differentiate on universal approach (one platform vs many tools)
- Mitigation: Speed to market (faster than custom builds)
- Mitigation: Price competitively

**Risk 3: Slow enterprise sales cycles**
- Mitigation: Offer free pilots (prove value before asking for money)
- Mitigation: Self-service tier (developers can start without approval)
- Mitigation: Build community (open source core → commercial add-ons)

---

## Next Steps

### Immediate Actions (Next 2 Weeks)

1. **Review & Approve Plan**
   - Stakeholder alignment on approach
   - Budget approval for Phase 0-2 ($150K)

2. **Hire Core Team**
   - Tech lead
   - 2 backend engineers

3. **Set Up Development Environment**
   - Repo structure for plugins
   - CI/CD pipeline updates
   - Dev/staging infrastructure

4. **Start Phase 0**
   - Fix call graph extraction
   - Implement basic flow algorithms

### Decision Points

**Week 4: After Phase 0**
- Decision: Proceed to Phase 1 (universal core)?
- Criteria: Core fixes working, tests passing

**Week 10: After Phase 2**
- Decision: Proceed to full build or pivot?
- Criteria: Manufacturing pilot shows >20% improvement, customer willing to pay

**Month 12: After Phase 11**
- Decision: Expand to more domains or consolidate?
- Criteria: 100+ customers, $1M ARR, 8+ domains proven

---

## Summary

**Current FlowRAG** is a solid foundation with working infrastructure but limited to software development.

**To become UFIS**, we need to build:

1. ✅ **Universal parsers** (20+ input formats across industries)
2. ✅ **Universal flow extraction** (pattern recognition + LLM inference)
3. ✅ **Domain plugins** (manufacturing, healthcare, supply chain, etc.)
4. ✅ **Flow optimization** (parallel detection, critical path, recommendations)
5. ✅ **API simulator** (for software domain)
6. ✅ **Visualization** (interactive graphs, timelines, dashboards)
7. ✅ **Universal schema** (process, resource, constraint nodes)

**Investment**: $1.25M full build, or $150K minimum viable (Phases 0-2)

**Timeline**: 12 months to full multi-domain platform

**Validation**: Manufacturing pilot (Phase 2) de-risks the entire approach - if it works there, it'll work everywhere.

**Market Opportunity**: $3.7B (from software-only $60M)

**Recommended Approach**: Start with Phase 0-2 ($150K), prove manufacturing value, then commit to full build.

---

## Appendices

### A. Technology Stack

**Backend:**
- Python 3.11+ (core language)
- FastAPI (API framework)
- Neo4j 5.x (graph database)
- Qdrant (vector database)
- Redis (caching, sessions)
- Tree-sitter (code parsing)
- spaCy (NLP)
- OpenAI GPT-4 (LLM)

**Frontend:**
- React 18+ (UI framework)
- Cytoscape.js (graph visualization)
- D3.js (charts, timelines)
- TailwindCSS (styling)

**Infrastructure:**
- Docker + Kubernetes (containers)
- AWS/GCP (cloud)
- GitHub Actions (CI/CD)
- Terraform (IaC)

**Domain-Specific:**
- pythonOCC (CAD parsing - manufacturing)
- python-hl7, fhirclient (healthcare)
- pandas (structured data)
- opencv-python (video/image)
- whisper (speech-to-text)

### B. Plugin Template Repository

```
ufis-plugin-template/
├─ README.md (how to create a plugin)
├─ plugin.yaml (manifest template)
├─ parsers.py (example parser)
├─ analyzers.py (example analyzer)
├─ validators.py (example validator)
├─ tests/ (test template)
└─ examples/ (sample data)
```

### C. API Endpoints (Full UFIS)

```
POST /ingest
  - Upload any file, auto-detect format
  - Body: file, domain (optional), namespace

POST /query
  - Natural language query
  - Body: query, namespace, domain (optional)

GET /flows/:namespace
  - List all flows in namespace

GET /flows/:namespace/:flow_id
  - Get specific flow details

POST /optimize
  - Get optimization recommendations
  - Body: namespace, flow_id

POST /simulate/api
  - Start API mock server
  - Body: namespace, port

POST /simulate/whatif
  - Run what-if scenario
  - Body: namespace, flow_id, modifications

GET /visualize/:namespace/:flow_id
  - Get visualization data
  - Returns: graph JSON for frontend

GET /plugins
  - List installed plugins

POST /plugins/install
  - Install new plugin
  - Body: plugin_id or plugin_url

GET /domains
  - List supported domains
```

---

**End of Implementation Plan**

This document is a living plan and will be updated as we progress through phases.
