# Universal Flow Intelligence System (UFIS)

**Version**: 1.0.0
**Date**: 2025-11-11
**Status**: Design Specification

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [System Architecture](#system-architecture)
4. [Technical Design](#technical-design)
5. [On-Demand API Simulator](#on-demand-api-simulator)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Market Positioning](#market-positioning)
8. [References](#references)

---

## Executive Summary

The **Universal Flow Intelligence System (UFIS)** is a next-generation knowledge graph platform that automatically extracts, unifies, and queries execution flows from both **code** (API flows, function calls) and **documentation** (process flows, procedures).

### Key Innovation

UFIS goes beyond traditional code analysis and documentation indexing by:

1. **Inferring implicit flows** - Discovers execution paths and dependencies even when not explicitly documented
2. **Unifying code and documentation** - Links code implementation to documentation procedures in a single graph
3. **Flow-aware querying** - Enables questions like "What can run in parallel?" or "What must I complete before step X?"
4. **Automated extraction** - Processes any codebase or documentation without manual annotation
5. **On-demand API simulation** - Generates realistic API mocks based on code analysis and flow understanding

### Market Impact

UFIS addresses critical pain points in:
- **DevOps/SRE**: Understanding complex deployment procedures and parallel execution opportunities
- **API Development**: Discovering service dependencies, call graphs, and automatic mock generation
- **Onboarding**: Accelerating developer ramp-up time with interactive API simulators
- **Incident Response**: Quickly understanding system behavior during outages
- **Compliance**: Documenting actual vs. intended workflows
- **Testing**: Eliminating manual mock setup with intelligent API simulation
- **Frontend Development**: Building UIs before backends are ready with realistic mocks

---

## Problem Statement

### Current FlowRAG Capabilities

FlowRAG currently provides:

✅ **Code Parsing**:
- AST-based parsing for Python, JavaScript
- Extraction of modules, classes, functions, methods
- CONTAINS relationships (Module→Class, Class→Method)
- IMPORTS relationships
- Vector embeddings for semantic search

✅ **Storage**:
- Neo4j for graph relationships
- Qdrant for semantic vectors
- Dual-storage architecture

✅ **Querying**:
- Semantic search via embeddings
- Basic graph traversal

### Critical Gaps

❌ **Missing Code Flow Analysis**:
```python
# flowrag-master/ingestion/parsers/python_parser.py:340-348
def _extract_calls(self, tree: ast.Module, file_path: str) -> List[Dict[str, str]]:
    """Extract function call relationships."""
    # This would need more sophisticated analysis
    # For now, return empty list  ← NOT IMPLEMENTED!
    return []
```

**Impact**: No execution flow tracking!

❌ **Missing Capabilities**:
- Call graph extraction (function/method invocations)
- API route detection and handler mapping
- Control flow analysis (if/else, try/catch, loops)
- Data flow tracking (variable assignments, parameters)
- Cross-file call resolution
- Async/await flow tracking

❌ **No Documentation Flow Processing**:
- Cannot extract workflows from documentation
- Cannot detect sequential vs. parallel steps
- Cannot infer dependencies from procedural text
- Cannot link code to documentation

❌ **Limited Query Intelligence**:
- Cannot answer flow-based questions
- Cannot identify parallel execution opportunities
- Cannot explain execution paths
- Cannot visualize workflows

### User Experience Problems

**Example: Flux Light Node Setup PDF (51 pages, 30+ steps)**

Current FlowRAG behavior:
1. User asks: "What steps can I do in parallel?"
2. FlowRAG returns: Generic text search results (not flow-aware)
3. User must manually analyze dependencies

Desired UFIS behavior:
1. User asks: "What steps can I do in parallel?"
2. UFIS returns: "Steps 2 and 3 can run in parallel because they have no dependencies on each other. Both only require Step 1 (Environment Preparation) to be completed."
3. UFIS shows: Visualization of parallel paths

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL FLOW INTELLIGENCE SYSTEM            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  Code Flow Analyzer  │      │ Document Flow Engine │        │
│  ├──────────────────────┤      ├──────────────────────┤        │
│  │ • AST Parser         │      │ • PDF/MD Parser      │        │
│  │ • Call Graph         │      │ • Step Detection     │        │
│  │ • API Routes         │      │ • Dependency Inference│       │
│  │ • Control Flow       │      │ • Command Extraction │        │
│  │ • Data Flow          │      │ • Parallel Detection │        │
│  └──────────────────────┘      └──────────────────────┘        │
│            │                              │                      │
│            └──────────────┬───────────────┘                      │
│                           ▼                                      │
│                  ┌─────────────────┐                            │
│                  │ Flow Unification │                            │
│                  ├─────────────────┤                            │
│                  │ • Code-to-Doc   │                            │
│                  │ • Unified Schema│                            │
│                  │ • Relationship  │                            │
│                  │   Resolution    │                            │
│                  └─────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │      Neo4j Graph     │      │   Qdrant Vectors     │        │
│  ├──────────────────────┤      ├──────────────────────┤        │
│  │ Nodes:               │      │ Collections:         │        │
│  │ • CodeUnit           │      │ • code_embeddings    │        │
│  │ • APIEndpoint        │      │ • doc_embeddings     │        │
│  │ • ProcessStep        │      │ • unified_embeddings │        │
│  │ • Command            │      │                      │        │
│  │ • DocSection         │      │ Metadata:            │        │
│  │ • Resource           │      │ • namespace          │        │
│  │                      │      │ • type               │        │
│  │ Relationships:       │      │ • file_path          │        │
│  │ • CALLS              │      │ • graph_node_id      │        │
│  │ • REQUIRES           │      │                      │        │
│  │ • DOCUMENTS          │      │                      │        │
│  │ • IMPLEMENTS         │      │                      │        │
│  │ • PARALLEL_WITH      │      │                      │        │
│  │ • NEXT               │      │                      │        │
│  │ • HANDLES            │      │                      │        │
│  └──────────────────────┘      └──────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          QUERY LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Intelligent Query Engine                       │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ • Flow-Aware Search                                       │  │
│  │ • Graph Traversal (BFS/DFS)                              │  │
│  │ • Dependency Resolution                                   │  │
│  │ • Parallel Path Detection                                │  │
│  │ • Visualization Generator                                │  │
│  │ • LLM-Enhanced Explanations                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Query Interfaces                         │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ • REST API                                                │  │
│  │ • GraphQL                                                 │  │
│  │ • CLI                                                     │  │
│  │ • Web UI                                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Code Files → AST Parser → Call Graph Extractor → Neo4j + Qdrant
                                    ↓
                           Relationship Builder
                                    ↓
Documentation → LLM Analyzer → Step Extractor → Neo4j + Qdrant
                                    ↓
                           Flow Unification
                                    ↓
                      Unified Knowledge Graph
                                    ↓
                    Flow-Aware Query Engine
```

---

## Technical Design

### 1. Code Flow Analyzer

#### 1.1 Enhanced Call Graph Extraction

**File**: `flowrag-master/ingestion/parsers/python_parser.py`

**Implementation**:

```python
def _extract_calls(self, tree: ast.Module, file_path: str) -> List[Dict[str, str]]:
    """
    Extract function/method call relationships.

    Tracks:
    - Direct function calls (foo())
    - Method calls (obj.method())
    - Class instantiations (MyClass())
    - Async calls (await foo())
    """
    calls = []

    class CallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_scope = None  # Track current function/method
            self.calls = []

        def visit_FunctionDef(self, node):
            previous_scope = self.current_scope
            self.current_scope = node.name
            self.generic_visit(node)
            self.current_scope = previous_scope

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_Call(self, node):
            """Extract call target."""
            call_target = None

            # Direct function call: foo()
            if isinstance(node.func, ast.Name):
                call_target = node.func.id

            # Method call: obj.method()
            elif isinstance(node.func, ast.Attribute):
                call_target = node.func.attr

            # Nested attribute: obj.module.method()
            elif isinstance(node.func, ast.Attribute):
                parts = []
                current = node.func
                while isinstance(current, ast.Attribute):
                    parts.insert(0, current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.insert(0, current.id)
                call_target = ".".join(parts)

            if call_target and self.current_scope:
                self.calls.append({
                    "caller": self.current_scope,
                    "callee": call_target,
                    "file_path": file_path,
                    "line_number": node.lineno,
                    "is_async": isinstance(node.func, ast.Attribute) and
                               hasattr(node.func, 'ctx') and
                               isinstance(node.func.ctx, ast.Load)
                })

            self.generic_visit(node)

    visitor = CallVisitor()
    visitor.visit(tree)
    return visitor.calls
```

**Graph Representation**:

```cypher
// Create CALLS relationship
MATCH (caller:Function {name: $caller_name, file_path: $file_path})
MATCH (callee:Function {name: $callee_name})
CREATE (caller)-[:CALLS {
    line_number: $line_number,
    is_async: $is_async,
    call_type: $call_type
}]->(callee)
```

#### 1.2 API Route Detection

**Supported Frameworks**:
- FastAPI (Python)
- Flask (Python)
- Express (JavaScript)
- Django REST Framework (Python)

**Implementation**:

```python
def _extract_api_routes(self, tree: ast.Module, file_path: str) -> List[Dict[str, Any]]:
    """
    Extract API endpoints and their handlers.

    Detects:
    - FastAPI: @app.get("/path")
    - Flask: @app.route("/path", methods=["GET"])
    - Decorators with HTTP methods
    """
    routes = []

    class RouteVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            for decorator in node.decorator_list:
                route_info = self._parse_decorator(decorator, node.name)
                if route_info:
                    routes.append(route_info)

        def _parse_decorator(self, decorator, handler_name):
            # FastAPI: @app.get("/users/{id}")
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr.upper()  # get, post, put, delete

                    # Extract path from first argument
                    if decorator.args:
                        path_arg = decorator.args[0]
                        if isinstance(path_arg, ast.Constant):
                            path = path_arg.value

                            return {
                                "method": method,
                                "path": path,
                                "handler": handler_name,
                                "file_path": file_path,
                                "line_number": decorator.lineno,
                                "framework": "fastapi"
                            }
            return None

    visitor = RouteVisitor()
    visitor.visit(tree)
    return routes
```

**Graph Representation**:

```cypher
// Create APIEndpoint node and link to handler
CREATE (endpoint:APIEndpoint {
    method: $method,
    path: $path,
    framework: $framework,
    file_path: $file_path
})

MATCH (handler:Function {name: $handler_name, file_path: $file_path})
CREATE (endpoint)-[:HANDLES]->(handler)
```

#### 1.3 Control Flow Analysis

**Implementation**:

```python
def _extract_control_flow(self, tree: ast.Module, file_path: str) -> List[Dict[str, Any]]:
    """
    Extract control flow structures.

    Tracks:
    - If/else branches
    - Try/except handlers
    - Loops (for, while)
    - Match/case (Python 3.10+)
    """
    control_flows = []

    class ControlFlowVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = None

        def visit_FunctionDef(self, node):
            previous = self.current_function
            self.current_function = node.name
            self.generic_visit(node)
            self.current_function = previous

        def visit_If(self, node):
            """Track if/else branches."""
            if self.current_function:
                control_flows.append({
                    "type": "conditional",
                    "structure": "if/else",
                    "function": self.current_function,
                    "line_number": node.lineno,
                    "has_else": len(node.orelse) > 0,
                    "file_path": file_path
                })
            self.generic_visit(node)

        def visit_Try(self, node):
            """Track try/except handlers."""
            if self.current_function:
                exception_types = [
                    handler.type.id if isinstance(handler.type, ast.Name) else "Exception"
                    for handler in node.handlers
                ]

                control_flows.append({
                    "type": "exception_handling",
                    "structure": "try/except",
                    "function": self.current_function,
                    "exception_types": exception_types,
                    "has_finally": len(node.finalbody) > 0,
                    "line_number": node.lineno,
                    "file_path": file_path
                })
            self.generic_visit(node)

        def visit_For(self, node):
            """Track for loops."""
            if self.current_function:
                control_flows.append({
                    "type": "loop",
                    "structure": "for",
                    "function": self.current_function,
                    "line_number": node.lineno,
                    "file_path": file_path
                })
            self.generic_visit(node)

        def visit_While(self, node):
            """Track while loops."""
            if self.current_function:
                control_flows.append({
                    "type": "loop",
                    "structure": "while",
                    "function": self.current_function,
                    "line_number": node.lineno,
                    "file_path": file_path
                })
            self.generic_visit(node)

    visitor = ControlFlowVisitor()
    visitor.visit(tree)
    return control_flows
```

**Graph Representation**:

```cypher
// Add control flow metadata to Function node
MATCH (f:Function {name: $function_name, file_path: $file_path})
SET f.has_conditionals = $has_conditionals,
    f.has_exception_handling = $has_exception_handling,
    f.has_loops = $has_loops,
    f.control_flow_complexity = $complexity
```

#### 1.4 Data Flow Tracking

**Implementation**:

```python
def _extract_data_flow(self, tree: ast.Module, file_path: str) -> List[Dict[str, Any]]:
    """
    Extract data flow relationships.

    Tracks:
    - Variable assignments
    - Function parameters
    - Return values
    - Global variables
    """
    data_flows = []

    class DataFlowVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = None
            self.variables = {}  # Track variable definitions

        def visit_FunctionDef(self, node):
            previous = self.current_function
            self.current_function = node.name

            # Track parameters
            for arg in node.args.args:
                data_flows.append({
                    "type": "parameter",
                    "variable": arg.arg,
                    "function": self.current_function,
                    "file_path": file_path
                })

            self.generic_visit(node)
            self.current_function = previous

        def visit_Assign(self, node):
            """Track variable assignments."""
            if self.current_function:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id

                        # Determine source
                        source = None
                        if isinstance(node.value, ast.Call):
                            if isinstance(node.value.func, ast.Name):
                                source = node.value.func.id
                        elif isinstance(node.value, ast.Name):
                            source = node.value.id

                        data_flows.append({
                            "type": "assignment",
                            "variable": var_name,
                            "source": source,
                            "function": self.current_function,
                            "line_number": node.lineno,
                            "file_path": file_path
                        })
            self.generic_visit(node)

        def visit_Return(self, node):
            """Track return values."""
            if self.current_function and node.value:
                return_source = None
                if isinstance(node.value, ast.Name):
                    return_source = node.value.id
                elif isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        return_source = node.value.func.id

                data_flows.append({
                    "type": "return",
                    "source": return_source,
                    "function": self.current_function,
                    "line_number": node.lineno,
                    "file_path": file_path
                })
            self.generic_visit(node)

    visitor = DataFlowVisitor()
    visitor.visit(tree)
    return data_flows
```

---

### 2. Document Flow Inference Engine

#### 2.1 Step Detection and Extraction

**Implementation**:

```python
import re
from typing import List, Dict, Any
from openai import OpenAI

class DocumentFlowInference:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client

    def extract_workflow(self, document_text: str, namespace: str) -> Dict[str, Any]:
        """
        Extract workflow from documentation.

        Uses:
        - Pattern matching for numbered steps
        - LLM for structure understanding
        - Heuristics for dependency detection
        """

        # Step 1: Extract numbered steps
        numbered_steps = self._extract_numbered_steps(document_text)

        # Step 2: Use LLM to understand structure
        workflow_structure = self._analyze_with_llm(document_text, numbered_steps)

        # Step 3: Extract dependencies
        dependencies = self._extract_dependencies(workflow_structure)

        # Step 4: Detect parallel opportunities
        parallel_groups = self._detect_parallel_steps(workflow_structure, dependencies)

        return {
            "namespace": namespace,
            "steps": workflow_structure,
            "dependencies": dependencies,
            "parallel_groups": parallel_groups,
            "metadata": {
                "total_steps": len(workflow_structure),
                "has_parallel": len(parallel_groups) > 0
            }
        }

    def _extract_numbered_steps(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract steps with numbered patterns.

        Patterns:
        - "Step 1:", "Step 2:", ...
        - "1.", "2.", "3.", ...
        - "1)", "2)", "3)", ...
        - Roman numerals: "I.", "II.", "III.", ...
        """
        patterns = [
            r"(?:Step\s+)?(\d+)[.:)\s]+([^\n]+)",  # Step 1: or 1. or 1)
            r"([IVXLCDM]+)\.\s+([^\n]+)",          # I. II. III.
        ]

        steps = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                step_number = match.group(1)
                step_text = match.group(2).strip()

                steps.append({
                    "step_number": step_number,
                    "title": step_text[:100],  # First 100 chars
                    "full_text": step_text,
                    "position": match.start()
                })

        # Sort by position in document
        steps.sort(key=lambda x: x["position"])
        return steps

    def _analyze_with_llm(self, document_text: str, numbered_steps: List[Dict]) -> List[Dict[str, Any]]:
        """
        Use LLM to understand workflow structure.
        """
        prompt = f"""Analyze this technical documentation and extract ALL detailed steps in the workflow.

Document excerpt:
{document_text[:8000]}  # First 8000 chars

Numbered steps found: {len(numbered_steps)}

For EACH step, extract:
1. Step number
2. Step title/name
3. Description (what it does)
4. Prerequisites (what must be done before)
5. Estimated time
6. Commands/actions (if any)
7. Expected outcome

Return JSON array with this structure:
[
  {{
    "step_number": "1",
    "name": "Prepare Environment",
    "description": "Install required dependencies...",
    "prerequisites": [],
    "estimated_time": "5 minutes",
    "commands": ["sudo apt update", "sudo apt install..."],
    "expected_outcome": "System ready for installation"
  }},
  ...
]

IMPORTANT: Extract ALL steps, not just high-level phases. If the document has 30 steps, return 30 entries."""

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a workflow analysis expert. Extract ALL steps comprehensively."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        import json
        workflow_data = json.loads(response.choices[0].message.content)
        return workflow_data.get("steps", [])

    def _extract_dependencies(self, steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract dependency relationships between steps.

        Uses:
        - Explicit prerequisites field
        - Temporal language ("after", "before", "once")
        - Sequential numbering
        """
        dependencies = []

        for step in steps:
            step_id = step["step_number"]

            # Explicit prerequisites
            prereqs = step.get("prerequisites", [])
            for prereq in prereqs:
                dependencies.append({
                    "from": step_id,
                    "to": prereq,
                    "type": "REQUIRES",
                    "confidence": "explicit"
                })

            # Sequential dependency (each step requires previous by default)
            try:
                current_num = int(step_id)
                if current_num > 1:
                    dependencies.append({
                        "from": step_id,
                        "to": str(current_num - 1),
                        "type": "NEXT",
                        "confidence": "sequential"
                    })
            except ValueError:
                pass

            # Temporal language analysis
            description = step.get("description", "").lower()

            temporal_patterns = [
                (r"after\s+step\s+(\d+)", "REQUIRES"),
                (r"before\s+step\s+(\d+)", "BEFORE"),
                (r"once\s+.*?step\s+(\d+)", "REQUIRES"),
                (r"following\s+step\s+(\d+)", "REQUIRES"),
            ]

            for pattern, rel_type in temporal_patterns:
                matches = re.finditer(pattern, description)
                for match in matches:
                    ref_step = match.group(1)
                    dependencies.append({
                        "from": step_id,
                        "to": ref_step,
                        "type": rel_type,
                        "confidence": "inferred"
                    })

        return dependencies

    def _detect_parallel_steps(self, steps: List[Dict], dependencies: List[Dict]) -> List[List[str]]:
        """
        Detect steps that can run in parallel.

        Algorithm:
        1. Build dependency graph
        2. Find steps at same depth level
        3. Check for shared dependencies (conflicting resources)
        4. Group independent steps
        """
        from collections import defaultdict, deque

        # Build adjacency list
        requires = defaultdict(set)  # step -> set of prerequisites
        for dep in dependencies:
            if dep["type"] == "REQUIRES":
                requires[dep["from"]].add(dep["to"])

        # Calculate depth for each step (longest path from root)
        depths = {}

        def calculate_depth(step_id):
            if step_id in depths:
                return depths[step_id]

            if not requires[step_id]:
                depths[step_id] = 0
                return 0

            max_prereq_depth = max(calculate_depth(prereq) for prereq in requires[step_id])
            depths[step_id] = max_prereq_depth + 1
            return depths[step_id]

        for step in steps:
            calculate_depth(step["step_number"])

        # Group steps by depth
        depth_groups = defaultdict(list)
        for step_id, depth in depths.items():
            depth_groups[depth].append(step_id)

        # Filter groups with 2+ steps (potential parallelism)
        parallel_groups = [
            group for group in depth_groups.values() if len(group) >= 2
        ]

        return parallel_groups
```

#### 2.2 Command Extraction

**Implementation**:

```python
def extract_commands(self, step_text: str) -> List[Dict[str, str]]:
    """
    Extract executable commands from step descriptions.

    Detects:
    - Code blocks (```bash, ```shell)
    - Inline commands (`command`)
    - Common command prefixes ($, #, sudo)
    """
    commands = []

    # Pattern 1: Code blocks
    code_block_pattern = r"```(?:bash|shell|sh)?\n(.*?)```"
    for match in re.finditer(code_block_pattern, step_text, re.DOTALL):
        block_content = match.group(1).strip()
        for line in block_content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                commands.append({
                    "command": line,
                    "type": "code_block",
                    "confidence": "high"
                })

    # Pattern 2: Inline code
    inline_pattern = r"`([^`]+)`"
    for match in re.finditer(inline_pattern, step_text):
        cmd = match.group(1).strip()
        # Filter out non-commands (variable names, etc.)
        if any(cmd.startswith(prefix) for prefix in ["sudo", "npm", "pip", "git", "docker", "curl", "wget"]):
            commands.append({
                "command": cmd,
                "type": "inline",
                "confidence": "medium"
            })

    # Pattern 3: Command-like lines (heuristic)
    command_prefixes = ["$", "#", ">", "sudo", "npm", "yarn", "pip", "python", "node", "git", "docker"]
    for line in step_text.split("\n"):
        line = line.strip()
        if any(line.startswith(prefix) for prefix in command_prefixes):
            # Remove prompt symbols
            clean_cmd = re.sub(r"^[$#>]\s*", "", line)
            commands.append({
                "command": clean_cmd,
                "type": "heuristic",
                "confidence": "low"
            })

    return commands
```

---

### 3. Flow Unification

#### 3.1 Code-to-Documentation Linking

**Implementation**:

```python
class FlowUnification:
    def __init__(self, neo4j_client, qdrant_client, openai_client):
        self.neo4j = neo4j_client
        self.qdrant = qdrant_client
        self.openai = openai_client

    def link_code_to_docs(self, code_namespace: str, doc_namespace: str) -> List[Dict]:
        """
        Link code implementations to documentation procedures.

        Strategy:
        1. Semantic similarity (embeddings)
        2. Name matching (function names in doc text)
        3. LLM-based matching
        """
        links = []

        # Get all code units
        code_query = """
        MATCH (c:CodeUnit {namespace: $namespace})
        WHERE c.type IN ['function', 'method', 'class']
        RETURN c.id as id, c.name as name, c.docstring as docstring, c.code as code
        """
        code_units = self.neo4j.execute_query(code_query, {"namespace": code_namespace})

        # Get all process steps
        step_query = """
        MATCH (s:ProcessStep {namespace: $namespace})
        RETURN s.id as id, s.name as name, s.description as description
        """
        process_steps = self.neo4j.execute_query(step_query, {"namespace": doc_namespace})

        # Strategy 1: Semantic similarity
        for code_unit in code_units:
            code_embedding = self._get_embedding(f"{code_unit['name']} {code_unit['docstring']}")

            for step in process_steps:
                step_embedding = self._get_embedding(f"{step['name']} {step['description']}")

                similarity = self._cosine_similarity(code_embedding, step_embedding)

                if similarity > 0.75:  # High similarity threshold
                    links.append({
                        "code_id": code_unit["id"],
                        "doc_id": step["id"],
                        "confidence": similarity,
                        "method": "semantic"
                    })

        # Strategy 2: Name matching
        for code_unit in code_units:
            for step in process_steps:
                # Check if function name appears in step description
                if code_unit["name"].lower() in step["description"].lower():
                    links.append({
                        "code_id": code_unit["id"],
                        "doc_id": step["id"],
                        "confidence": 0.9,
                        "method": "name_match"
                    })

        # Strategy 3: LLM-based matching (for ambiguous cases)
        # ... (omitted for brevity)

        return links

    def create_unified_graph(self, links: List[Dict]):
        """
        Create IMPLEMENTS relationships in Neo4j.
        """
        for link in links:
            query = """
            MATCH (code:CodeUnit {id: $code_id})
            MATCH (step:ProcessStep {id: $doc_id})
            MERGE (code)-[:IMPLEMENTS {
                confidence: $confidence,
                method: $method
            }]->(step)
            """
            self.neo4j.execute_query(query, {
                "code_id": link["code_id"],
                "doc_id": link["doc_id"],
                "confidence": link["confidence"],
                "method": link["method"]
            })

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
        import numpy as np
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

#### 3.2 Unified Graph Schema

**Neo4j Schema**:

```cypher
// ============================================================
// NODE TYPES
// ============================================================

// Code Nodes
(:CodeUnit {
    id: string,              // Unique identifier
    namespace: string,       // Project/repo identifier
    type: string,            // "module", "class", "function", "method"
    name: string,
    file_path: string,
    line_number: int,
    docstring: string,
    code: string,
    signature: string,
    is_async: boolean,
    complexity: int,         // Cyclomatic complexity
    created_at: timestamp
})

(:APIEndpoint {
    id: string,
    namespace: string,
    method: string,          // GET, POST, PUT, DELETE
    path: string,            // "/api/users/{id}"
    framework: string,       // "fastapi", "flask", "express"
    file_path: string,
    line_number: int,
    created_at: timestamp
})

// Documentation Nodes
(:ProcessStep {
    id: string,
    namespace: string,
    step_number: string,     // "1", "2", "3a", etc.
    name: string,
    description: string,
    estimated_time: string,
    expected_outcome: string,
    created_at: timestamp
})

(:Command {
    id: string,
    namespace: string,
    command: string,
    type: string,            // "shell", "api", "sql"
    confidence: float,       // 0.0 - 1.0
    created_at: timestamp
})

(:DocSection {
    id: string,
    namespace: string,
    title: string,
    content: string,
    file_path: string,
    page_number: int,
    created_at: timestamp
})

(:Resource {
    id: string,
    namespace: string,
    type: string,            // "url", "file", "service", "database"
    name: string,
    location: string,
    created_at: timestamp
})

// ============================================================
// RELATIONSHIP TYPES
// ============================================================

// Code Relationships
-[:CALLS {
    line_number: int,
    is_async: boolean,
    call_type: string        // "direct", "method", "constructor"
}]->

-[:CONTAINS]->               // Module contains Class, Class contains Method

-[:IMPORTS {
    alias: string
}]->

-[:HANDLES]->                // APIEndpoint handles Function

// Documentation Relationships
-[:REQUIRES {
    confidence: string       // "explicit", "inferred", "sequential"
}]->

-[:NEXT]->                   // Sequential step ordering

-[:PARALLEL_WITH]->          // Steps that can run concurrently

-[:EXECUTES]->               // ProcessStep executes Command

-[:REFERENCES]->             // ProcessStep references Resource

// Unified Relationships
-[:IMPLEMENTS {
    confidence: float,
    method: string           // "semantic", "name_match", "llm"
}]->                         // Code implements ProcessStep

-[:DOCUMENTS {
    confidence: float
}]->                         // DocSection documents CodeUnit

// ============================================================
// INDEXES AND CONSTRAINTS
// ============================================================

CREATE CONSTRAINT unique_code_unit_id IF NOT EXISTS
FOR (c:CodeUnit) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT unique_process_step_id IF NOT EXISTS
FOR (s:ProcessStep) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT unique_api_endpoint IF NOT EXISTS
FOR (e:APIEndpoint) REQUIRE (e.method, e.path, e.namespace) IS UNIQUE;

CREATE INDEX code_unit_namespace IF NOT EXISTS
FOR (c:CodeUnit) ON (c.namespace);

CREATE INDEX process_step_namespace IF NOT EXISTS
FOR (s:ProcessStep) ON (s.namespace);

CREATE INDEX api_endpoint_path IF NOT EXISTS
FOR (e:APIEndpoint) ON (e.path);
```

---

### 4. Intelligent Query Engine

#### 4.1 Flow-Aware Queries

**Implementation**:

```python
class FlowAwareQueryEngine:
    def __init__(self, neo4j_client, qdrant_client, openai_client):
        self.neo4j = neo4j_client
        self.qdrant = qdrant_client
        self.openai = openai_client

    def query(self, user_question: str, namespace: str) -> Dict[str, Any]:
        """
        Answer flow-aware questions.

        Supports:
        - "What can run in parallel?"
        - "What must be done before X?"
        - "What calls function Y?"
        - "Show me the execution path from A to B"
        """

        # Classify question type
        question_type = self._classify_question(user_question)

        if question_type == "parallel":
            return self._find_parallel_steps(namespace)
        elif question_type == "dependencies":
            return self._find_dependencies(user_question, namespace)
        elif question_type == "call_graph":
            return self._find_call_graph(user_question, namespace)
        elif question_type == "execution_path":
            return self._find_execution_path(user_question, namespace)
        else:
            return self._semantic_search(user_question, namespace)

    def _classify_question(self, question: str) -> str:
        """Classify question type using LLM."""
        prompt = f"""Classify this question into ONE category:

Question: {question}

Categories:
- parallel: Questions about concurrent execution
- dependencies: Questions about prerequisites
- call_graph: Questions about function calls
- execution_path: Questions about flow from A to B
- semantic: General questions

Return only the category name."""

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=20
        )

        return response.choices[0].message.content.strip().lower()

    def _find_parallel_steps(self, namespace: str) -> Dict[str, Any]:
        """Find steps that can run in parallel."""
        query = """
        MATCH (s:ProcessStep {namespace: $namespace})
        OPTIONAL MATCH (s)-[:REQUIRES]->(prereq)

        WITH s, collect(prereq.step_number) as prerequisites

        // Group by prerequisite set to find steps with same dependencies
        WITH prerequisites, collect(s) as steps
        WHERE size(steps) > 1

        RETURN prerequisites, [step in steps | {
            step_number: step.step_number,
            name: step.name,
            description: step.description
        }] as parallel_steps
        """

        results = self.neo4j.execute_query(query, {"namespace": namespace})

        # Generate explanation
        parallel_groups = []
        for result in results:
            prereqs = result["prerequisites"]
            steps = result["parallel_steps"]

            parallel_groups.append({
                "steps": steps,
                "shared_prerequisites": prereqs,
                "can_run_parallel": True
            })

        explanation = self._generate_parallel_explanation(parallel_groups)

        return {
            "question_type": "parallel",
            "parallel_groups": parallel_groups,
            "explanation": explanation
        }

    def _find_dependencies(self, question: str, namespace: str) -> Dict[str, Any]:
        """Find dependencies for a specific step."""

        # Extract step identifier from question
        step_pattern = r"(?:step\s+)?(\d+|[A-Za-z0-9_-]+)"
        match = re.search(step_pattern, question, re.IGNORECASE)

        if not match:
            return {"error": "Could not identify step in question"}

        step_id = match.group(1)

        # Query Neo4j for dependencies
        query = """
        MATCH (s:ProcessStep {namespace: $namespace})
        WHERE s.step_number = $step_id OR s.name CONTAINS $step_id

        // Find direct prerequisites
        OPTIONAL MATCH (s)-[:REQUIRES]->(direct_prereq:ProcessStep)

        // Find transitive prerequisites (all ancestors)
        OPTIONAL MATCH path = (s)-[:REQUIRES*]->(transitive_prereq:ProcessStep)

        RETURN s as step,
               collect(DISTINCT direct_prereq) as direct_prerequisites,
               collect(DISTINCT transitive_prereq) as all_prerequisites,
               length(path) as depth
        ORDER BY depth
        """

        result = self.neo4j.execute_query(query, {
            "namespace": namespace,
            "step_id": step_id
        })

        if not result:
            return {"error": f"Step '{step_id}' not found"}

        # Generate explanation
        explanation = self._generate_dependency_explanation(result[0])

        return {
            "question_type": "dependencies",
            "target_step": result[0]["step"],
            "direct_prerequisites": result[0]["direct_prerequisites"],
            "all_prerequisites": result[0]["all_prerequisites"],
            "explanation": explanation
        }

    def _find_call_graph(self, question: str, namespace: str) -> Dict[str, Any]:
        """Find call graph for a function."""

        # Extract function name from question
        func_pattern = r"(?:function|method)\s+['\"]?(\w+)['\"]?"
        match = re.search(func_pattern, question, re.IGNORECASE)

        if not match:
            # Try simple word extraction
            words = re.findall(r'\b[a-z_][a-z0-9_]*\b', question, re.IGNORECASE)
            if words:
                func_name = words[-1]  # Assume last identifier is function name
            else:
                return {"error": "Could not identify function in question"}
        else:
            func_name = match.group(1)

        # Query for callers and callees
        query = """
        MATCH (f:CodeUnit {namespace: $namespace})
        WHERE f.name = $func_name OR f.name CONTAINS $func_name

        // Find what calls this function (callers)
        OPTIONAL MATCH (caller:CodeUnit)-[c1:CALLS]->(f)

        // Find what this function calls (callees)
        OPTIONAL MATCH (f)-[c2:CALLS]->(callee:CodeUnit)

        RETURN f as function,
               collect(DISTINCT {
                   name: caller.name,
                   file: caller.file_path,
                   line: c1.line_number
               }) as callers,
               collect(DISTINCT {
                   name: callee.name,
                   file: callee.file_path,
                   line: c2.line_number
               }) as callees
        """

        result = self.neo4j.execute_query(query, {
            "namespace": namespace,
            "func_name": func_name
        })

        if not result:
            return {"error": f"Function '{func_name}' not found"}

        # Generate visualization
        visualization = self._generate_call_graph_viz(result[0])

        return {
            "question_type": "call_graph",
            "function": result[0]["function"],
            "callers": result[0]["callers"],
            "callees": result[0]["callees"],
            "visualization": visualization
        }

    def _find_execution_path(self, question: str, namespace: str) -> Dict[str, Any]:
        """Find execution path between two points."""

        # Extract start and end points
        # ... (pattern matching logic)

        # Use Cypher path finding
        query = """
        MATCH (start {namespace: $namespace, name: $start_name})
        MATCH (end {namespace: $namespace, name: $end_name})

        MATCH path = shortestPath((start)-[:CALLS|REQUIRES|NEXT*]->(end))

        RETURN path,
               length(path) as path_length,
               [node in nodes(path) | {
                   name: node.name,
                   type: labels(node)[0]
               }] as nodes,
               [rel in relationships(path) | type(rel)] as relationships
        """

        result = self.neo4j.execute_query(query, {
            "namespace": namespace,
            "start_name": "...",  # Extracted from question
            "end_name": "..."
        })

        return {
            "question_type": "execution_path",
            "path": result
        }

    def _semantic_search(self, question: str, namespace: str) -> Dict[str, Any]:
        """Fallback to semantic search."""

        # Generate embedding
        embedding = self._get_embedding(question)

        # Search Qdrant
        search_results = self.qdrant.search(
            collection_name=f"{namespace}_unified",
            query_vector=embedding,
            limit=5
        )

        # Get related graph nodes
        graph_context = []
        for result in search_results:
            node_id = result.payload.get("graph_node_id")
            if node_id:
                # Fetch node and neighbors from Neo4j
                node_query = """
                MATCH (n {id: $node_id})
                OPTIONAL MATCH (n)-[r]-(neighbor)
                RETURN n, collect({rel: type(r), node: neighbor}) as neighbors
                LIMIT 1
                """
                node_data = self.neo4j.execute_query(node_query, {"node_id": node_id})
                if node_data:
                    graph_context.append(node_data[0])

        # Generate answer with LLM
        context = self._build_context(search_results, graph_context)
        answer = self._generate_answer(question, context)

        return {
            "question_type": "semantic",
            "results": search_results,
            "graph_context": graph_context,
            "answer": answer
        }

    def _generate_parallel_explanation(self, parallel_groups: List[Dict]) -> str:
        """Generate human-readable explanation of parallel opportunities."""

        if not parallel_groups:
            return "No parallel execution opportunities found in this workflow."

        explanations = []
        for group in parallel_groups:
            steps = group["steps"]
            prereqs = group["shared_prerequisites"]

            step_names = ", ".join([f"Step {s['step_number']}" for s in steps])

            if prereqs:
                prereq_text = ", ".join([f"Step {p}" for p in prereqs])
                explanation = f"{step_names} can run in parallel after completing {prereq_text}."
            else:
                explanation = f"{step_names} can run in parallel from the start (no prerequisites)."

            explanations.append(explanation)

        return "\n\n".join(explanations)

    def _generate_dependency_explanation(self, result: Dict) -> str:
        """Generate explanation of dependencies."""
        step = result["step"]
        direct = result["direct_prerequisites"]
        all_prereqs = result["all_prerequisites"]

        explanation = f"**Step {step['step_number']}: {step['name']}**\n\n"

        if not direct:
            explanation += "This step has no direct prerequisites and can be started immediately."
        else:
            explanation += "**Direct Prerequisites:**\n"
            for prereq in direct:
                explanation += f"- Step {prereq['step_number']}: {prereq['name']}\n"

            if len(all_prereqs) > len(direct):
                explanation += f"\n**Total Prerequisites (including transitive):** {len(all_prereqs)} steps"

        return explanation

    def _generate_call_graph_viz(self, result: Dict) -> str:
        """Generate ASCII visualization of call graph."""
        func = result["function"]
        callers = result["callers"]
        callees = result["callees"]

        viz = []

        # Callers
        for caller in callers:
            viz.append(f"  {caller['name']} ({caller['file']}:{caller['line']})")
            viz.append(f"    ↓ CALLS")

        # Target function
        viz.append(f"  → {func['name']} ← TARGET")

        # Callees
        if callees:
            viz.append(f"    ↓ CALLS")
            for callee in callees:
                viz.append(f"  {callee['name']} ({callee['file']}:{callee['line']})")

        return "\n".join(viz)
```

---

## On-Demand API Simulator

### Overview

The **On-Demand API Simulator** is a groundbreaking feature that automatically generates realistic, intelligent API mocks based on UFIS's deep understanding of code structure, flow patterns, and business logic. Unlike traditional mocking tools that require manual configuration, UFIS can spin up a fully functional API simulator on-demand by analyzing your codebase.

### Key Capabilities

1. **Automatic Endpoint Discovery** - Scans code to identify all API routes, parameters, and response types
2. **Intelligent Response Generation** - Uses LLMs to generate realistic responses based on handler logic
3. **Flow-Aware Behavior** - Simulates call chains, database queries, and side effects
4. **State Management** - Maintains stateful behavior (CRUD operations work correctly)
5. **Performance Testing** - Simulate latency, errors, rate limits based on real code patterns
6. **Contract Validation** - Ensures mock responses match schema definitions

### Use Cases

#### 1. **Frontend Development Without Backend**
Developers can build frontends before the backend is ready, with mocks that behave like the real API.

#### 2. **Integration Testing**
Test how your service integrates with external APIs without hitting real endpoints.

#### 3. **Performance Testing**
Load test your application with realistic API responses at scale.

#### 4. **API Documentation**
Generate interactive API documentation with live examples.

#### 5. **Contract Testing**
Validate that your API implementation matches documentation/specs.

---

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    API SIMULATOR ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      1. ENDPOINT ANALYZER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: Codebase + UFIS Knowledge Graph                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Extract API Routes (FastAPI, Flask, Express)          │  │
│  │  • Parse Request/Response Schemas (Pydantic, TypeScript) │  │
│  │  • Analyze Handler Functions                             │  │
│  │  • Extract Validation Rules                              │  │
│  │  • Detect Authentication Requirements                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Output: API Specification (OpenAPI 3.0 compatible)             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   2. RESPONSE GENERATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Schema-Based Generator                                   │  │
│  │  ├─ Generate data matching Pydantic/JSON Schema          │  │
│  │  ├─ Respect constraints (min/max, regex, enum)           │  │
│  │  └─ Use realistic fake data (names, emails, IDs)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LLM-Enhanced Generator                                   │  │
│  │  ├─ Analyze handler function logic                       │  │
│  │  ├─ Understand business rules                            │  │
│  │  ├─ Generate contextually appropriate responses          │  │
│  │  └─ Simulate edge cases (errors, empty results)          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Flow-Aware Generator                                     │  │
│  │  ├─ Trace execution path through call graph              │  │
│  │  ├─ Simulate database queries                            │  │
│  │  ├─ Model side effects (notifications, cache updates)    │  │
│  │  └─ Maintain consistency across related endpoints        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    3. STATE MANAGER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  In-Memory Data Store                                     │  │
│  │  ├─ Simulate CRUD operations                             │  │
│  │  ├─ Maintain relational consistency                      │  │
│  │  ├─ Support pagination, filtering, sorting              │  │
│  │  └─ Track resource versions (for optimistic locking)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Session Management                                       │  │
│  │  ├─ Track user sessions                                  │  │
│  │  ├─ Maintain authentication state                        │  │
│  │  └─ Isolate data per test context                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  4. BEHAVIOR SIMULATOR                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Latency Simulation                                       │  │
│  │  ├─ Analyze code complexity → estimate latency          │  │
│  │  ├─ Simulate network delays                              │  │
│  │  └─ Model database query times                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Error Simulation                                         │  │
│  │  ├─ Return errors based on validation rules             │  │
│  │  ├─ Simulate exception handling paths                    │  │
│  │  ├─ Model rate limiting (429 responses)                 │  │
│  │  └─ Reproduce edge cases from code analysis             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Side Effect Simulation                                   │  │
│  │  ├─ Detect notification calls → log events              │  │
│  │  ├─ Detect cache operations → update mock cache         │  │
│  │  └─ Detect async tasks → simulate background jobs       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    5. MOCK SERVER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  HTTP Server (FastAPI-based)                             │  │
│  │  ├─ Dynamically register endpoints                       │  │
│  │  ├─ Handle authentication                                │  │
│  │  ├─ Apply middleware (CORS, rate limiting)              │  │
│  │  └─ Serve OpenAPI spec at /docs                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Control Interface                                        │  │
│  │  ├─ /simulator/reset - Reset state                      │  │
│  │  ├─ /simulator/config - Configure behavior              │  │
│  │  ├─ /simulator/scenarios - Load test scenarios          │  │
│  │  └─ /simulator/analytics - View request logs            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

### Implementation

#### 5.1 Endpoint Analyzer

```python
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class APIEndpointSpec:
    """Complete specification for an API endpoint."""
    method: str                      # GET, POST, PUT, DELETE, PATCH
    path: str                        # /api/users/{id}
    handler_function: str            # get_user
    request_schema: Optional[Dict]   # Pydantic schema or JSON schema
    response_schema: Dict            # Response schema
    status_codes: List[int]          # [200, 404, 500]
    authentication_required: bool
    rate_limit: Optional[int]        # Requests per minute
    validation_rules: List[Dict]     # Custom validation logic
    side_effects: List[str]          # ["send_email", "cache_update"]
    call_chain: List[str]            # Functions called by handler
    estimated_latency_ms: int        # Based on code complexity


class EndpointAnalyzer:
    """Analyzes codebase to extract API endpoint specifications."""

    def __init__(self, neo4j_client, qdrant_client):
        self.neo4j = neo4j_client
        self.qdrant = qdrant_client

    def analyze_endpoints(self, namespace: str) -> List[APIEndpointSpec]:
        """
        Extract all API endpoints from the knowledge graph.

        Returns:
            List of complete endpoint specifications
        """
        query = """
        MATCH (endpoint:APIEndpoint {namespace: $namespace})-[:HANDLES]->(handler:CodeUnit)

        // Get call chain
        OPTIONAL MATCH path = (handler)-[:CALLS*1..5]->(callee:CodeUnit)

        // Get request/response schemas (from decorator or docstring)
        OPTIONAL MATCH (handler)-[:HAS_SCHEMA]->(schema:Schema)

        RETURN endpoint.method as method,
               endpoint.path as path,
               endpoint.framework as framework,
               handler.name as handler_name,
               handler.code as handler_code,
               handler.docstring as docstring,
               handler.file_path as file_path,
               collect(DISTINCT callee.name) as call_chain,
               schema.request as request_schema,
               schema.response as response_schema
        """

        results = self.neo4j.execute_query(query, {"namespace": namespace})

        specs = []
        for result in results:
            # Analyze handler code to extract additional details
            spec = self._analyze_handler(result)
            specs.append(spec)

        return specs

    def _analyze_handler(self, endpoint_data: Dict) -> APIEndpointSpec:
        """
        Analyze handler function to extract behavior.

        Uses:
        - AST analysis for validation rules
        - LLM analysis for business logic
        - Call graph for side effects
        """
        handler_code = endpoint_data["handler_code"]
        docstring = endpoint_data.get("docstring", "")

        # Extract validation rules from code
        validation_rules = self._extract_validation_rules(handler_code)

        # Detect authentication requirements
        auth_required = self._detect_auth_requirements(handler_code, docstring)

        # Estimate latency based on code complexity
        estimated_latency = self._estimate_latency(
            handler_code,
            len(endpoint_data["call_chain"])
        )

        # Detect side effects
        side_effects = self._detect_side_effects(
            handler_code,
            endpoint_data["call_chain"]
        )

        # Extract or infer schemas
        request_schema = endpoint_data.get("request_schema") or \
                        self._infer_request_schema(handler_code)

        response_schema = endpoint_data.get("response_schema") or \
                         self._infer_response_schema(handler_code, docstring)

        # Determine possible status codes
        status_codes = self._extract_status_codes(handler_code)

        return APIEndpointSpec(
            method=endpoint_data["method"],
            path=endpoint_data["path"],
            handler_function=endpoint_data["handler_name"],
            request_schema=request_schema,
            response_schema=response_schema,
            status_codes=status_codes,
            authentication_required=auth_required,
            rate_limit=self._extract_rate_limit(handler_code),
            validation_rules=validation_rules,
            side_effects=side_effects,
            call_chain=endpoint_data["call_chain"],
            estimated_latency_ms=estimated_latency
        )

    def _extract_validation_rules(self, code: str) -> List[Dict]:
        """Extract validation logic from handler code."""
        import ast
        import re

        rules = []

        # Parse code
        try:
            tree = ast.parse(code)
        except:
            return rules

        # Look for validation patterns
        class ValidationVisitor(ast.NodeVisitor):
            def __init__(self):
                self.rules = []

            def visit_If(self, node):
                """Detect validation checks."""
                # Pattern: if not user: raise HTTPException(404)
                if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                    # Check if body raises exception
                    if node.body and isinstance(node.body[0], ast.Raise):
                        self.rules.append({
                            "type": "not_found_check",
                            "line": node.lineno
                        })

                self.generic_visit(node)

            def visit_Call(self, node):
                """Detect validation function calls."""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if "validate" in func_name.lower():
                        self.rules.append({
                            "type": "validation_call",
                            "function": func_name,
                            "line": node.lineno
                        })

                self.generic_visit(node)

        visitor = ValidationVisitor()
        visitor.visit(tree)
        return visitor.rules

    def _detect_auth_requirements(self, code: str, docstring: str) -> bool:
        """Detect if endpoint requires authentication."""
        auth_indicators = [
            "current_user",
            "verify_token",
            "require_auth",
            "authenticated",
            "jwt",
            "api_key",
            "Depends(get_current_user)"
        ]

        combined_text = f"{code} {docstring}".lower()
        return any(indicator.lower() in combined_text for indicator in auth_indicators)

    def _estimate_latency(self, code: str, call_chain_length: int) -> int:
        """
        Estimate endpoint latency based on code complexity.

        Heuristics:
        - Base latency: 50ms
        - +20ms per function call
        - +100ms if database query detected
        - +50ms if external API call detected
        """
        import re

        latency = 50  # Base latency

        # Add latency for call chain depth
        latency += call_chain_length * 20

        # Database queries
        db_patterns = [r"\.query\(", r"\.find\(", r"\.get\(", r"SELECT", r"INSERT", r"UPDATE"]
        db_queries = sum(len(re.findall(pattern, code, re.IGNORECASE)) for pattern in db_patterns)
        latency += db_queries * 100

        # External API calls
        api_patterns = [r"requests\.", r"httpx\.", r"fetch\(", r"axios\."]
        api_calls = sum(len(re.findall(pattern, code)) for pattern in api_patterns)
        latency += api_calls * 150

        # Loops (adds complexity)
        loop_patterns = [r"for ", r"while "]
        loops = sum(len(re.findall(pattern, code)) for pattern in loop_patterns)
        latency += loops * 30

        return latency

    def _detect_side_effects(self, code: str, call_chain: List[str]) -> List[str]:
        """Detect side effects from code analysis."""
        side_effects = []

        # Email sending
        if any(keyword in code.lower() for keyword in ["send_email", "sendmail", "smtp"]):
            side_effects.append("send_email")

        # Notifications
        if any(keyword in code.lower() for keyword in ["notify", "notification", "webhook"]):
            side_effects.append("send_notification")

        # Cache operations
        if any(keyword in code.lower() for keyword in ["cache.set", "redis.set", "memcached"]):
            side_effects.append("cache_update")

        # Background tasks
        if any(keyword in code.lower() for keyword in ["background_task", "celery", "queue"]):
            side_effects.append("enqueue_task")

        # Database writes
        if any(keyword in code.lower() for keyword in ["commit()", "save()", "insert", "update", "delete"]):
            side_effects.append("database_write")

        return side_effects

    def _infer_request_schema(self, code: str) -> Optional[Dict]:
        """Infer request schema from function signature."""
        import ast
        import re

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Look for Pydantic model in arguments
                    for arg in node.args.args:
                        if arg.annotation:
                            annotation_name = ast.unparse(arg.annotation)
                            if "Request" in annotation_name or "Body" in annotation_name:
                                # Found request model
                                return {
                                    "type": "object",
                                    "model": annotation_name,
                                    "inferred": True
                                }
        except:
            pass

        return None

    def _infer_response_schema(self, code: str, docstring: str) -> Dict:
        """Infer response schema from return type or docstring."""
        import ast

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.returns:
                    return_type = ast.unparse(node.returns)
                    return {
                        "type": "object",
                        "model": return_type,
                        "inferred": True
                    }
        except:
            pass

        # Fallback: generic response
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "data": {"type": "object"}
            }
        }

    def _extract_status_codes(self, code: str) -> List[int]:
        """Extract possible HTTP status codes from handler."""
        import re

        status_codes = [200]  # Default success

        # Look for HTTPException with status codes
        pattern = r"HTTPException\((?:status_code=)?(\d{3})"
        matches = re.findall(pattern, code)
        status_codes.extend([int(code) for code in matches])

        # Look for response.status_code = XXX
        pattern = r"status_code\s*=\s*(\d{3})"
        matches = re.findall(pattern, code)
        status_codes.extend([int(code) for code in matches])

        return sorted(set(status_codes))

    def _extract_rate_limit(self, code: str) -> Optional[int]:
        """Extract rate limit if specified."""
        import re

        # Look for @limiter.limit("100/minute") decorators
        pattern = r'@.*limit\(["\'](\d+)/(?:minute|hour|day)'
        match = re.search(pattern, code)

        if match:
            return int(match.group(1))

        return None
```

#### 5.2 Response Generator

```python
from typing import Any, Dict
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

class ResponseGenerator:
    """Generates realistic API responses based on schemas and code analysis."""

    def __init__(self, openai_client):
        self.openai = openai_client
        self.faker = Faker()

    def generate_response(
        self,
        endpoint_spec: APIEndpointSpec,
        request_data: Dict[str, Any],
        state_manager: 'StateManager'
    ) -> Dict[str, Any]:
        """
        Generate response for an API endpoint.

        Strategy:
        1. Check if endpoint has state (CRUD) → use StateManager
        2. Use schema-based generation for structured data
        3. Use LLM for complex business logic
        """

        # Handle CRUD operations
        if self._is_crud_endpoint(endpoint_spec):
            return self._handle_crud(endpoint_spec, request_data, state_manager)

        # Schema-based generation
        if endpoint_spec.response_schema:
            return self._generate_from_schema(endpoint_spec.response_schema, request_data)

        # LLM-based generation (for complex logic)
        return self._generate_with_llm(endpoint_spec, request_data)

    def _is_crud_endpoint(self, spec: APIEndpointSpec) -> bool:
        """Detect if endpoint is a CRUD operation."""
        crud_patterns = {
            "GET": ["get", "list", "find", "fetch", "retrieve"],
            "POST": ["create", "add", "insert"],
            "PUT": ["update", "edit", "modify"],
            "PATCH": ["update", "patch"],
            "DELETE": ["delete", "remove"]
        }

        handler_name = spec.handler_function.lower()
        return any(pattern in handler_name for pattern in crud_patterns.get(spec.method, []))

    def _handle_crud(
        self,
        spec: APIEndpointSpec,
        request_data: Dict,
        state_manager: 'StateManager'
    ) -> Dict[str, Any]:
        """Handle CRUD operations with stateful behavior."""

        # Extract resource type from path (/api/users/{id} → users)
        resource_type = self._extract_resource_type(spec.path)

        if spec.method == "GET":
            # Extract ID from path parameters
            if "{id}" in spec.path or "{pk}" in spec.path:
                resource_id = request_data.get("path_params", {}).get("id")
                return state_manager.get(resource_type, resource_id)
            else:
                # List operation
                return state_manager.list(resource_type, request_data.get("query_params", {}))

        elif spec.method == "POST":
            return state_manager.create(resource_type, request_data.get("body", {}))

        elif spec.method == "PUT" or spec.method == "PATCH":
            resource_id = request_data.get("path_params", {}).get("id")
            return state_manager.update(resource_type, resource_id, request_data.get("body", {}))

        elif spec.method == "DELETE":
            resource_id = request_data.get("path_params", {}).get("id")
            return state_manager.delete(resource_type, resource_id)

    def _extract_resource_type(self, path: str) -> str:
        """Extract resource type from API path."""
        import re

        # /api/v1/users/{id} → users
        # /users → users
        match = re.search(r'/([a-z_]+)(?:/\{|$)', path)
        if match:
            return match.group(1)
        return "resource"

    def _generate_from_schema(self, schema: Dict, request_data: Dict) -> Dict[str, Any]:
        """Generate response matching JSON schema."""

        if schema.get("type") == "object":
            result = {}
            properties = schema.get("properties", {})

            for prop_name, prop_schema in properties.items():
                result[prop_name] = self._generate_value(prop_schema, prop_name)

            return result

        elif schema.get("type") == "array":
            items_schema = schema.get("items", {})
            count = random.randint(1, 5)
            return [self._generate_from_schema(items_schema, request_data) for _ in range(count)]

        else:
            return self._generate_value(schema, "value")

    def _generate_value(self, schema: Dict, field_name: str) -> Any:
        """Generate a single value matching schema."""

        prop_type = schema.get("type", "string")

        # Enum
        if "enum" in schema:
            return random.choice(schema["enum"])

        # Type-specific generation
        if prop_type == "string":
            # Context-aware string generation
            if "email" in field_name.lower():
                return self.faker.email()
            elif "name" in field_name.lower():
                return self.faker.name()
            elif "phone" in field_name.lower():
                return self.faker.phone_number()
            elif "url" in field_name.lower() or "link" in field_name.lower():
                return self.faker.url()
            elif "address" in field_name.lower():
                return self.faker.address()
            elif "id" in field_name.lower():
                return str(uuid.uuid4())
            elif "date" in field_name.lower() or "time" in field_name.lower():
                return self.faker.date_time().isoformat()
            else:
                # Respect constraints
                max_length = schema.get("maxLength", 50)
                return self.faker.text(max_nb_chars=max_length)

        elif prop_type == "integer":
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", 1000)
            return random.randint(minimum, maximum)

        elif prop_type == "number":
            minimum = schema.get("minimum", 0.0)
            maximum = schema.get("maximum", 1000.0)
            return round(random.uniform(minimum, maximum), 2)

        elif prop_type == "boolean":
            return random.choice([True, False])

        elif prop_type == "null":
            return None

        return None

    def _generate_with_llm(self, spec: APIEndpointSpec, request_data: Dict) -> Dict[str, Any]:
        """Use LLM to generate contextually appropriate response."""

        prompt = f"""Generate a realistic JSON response for this API endpoint.

Endpoint: {spec.method} {spec.path}
Handler Function: {spec.handler_function}

Request Data:
{request_data}

Generate a response that:
1. Matches the expected behavior of the handler function
2. Is contextually appropriate for the request
3. Includes realistic data
4. Follows REST API best practices

Return ONLY valid JSON, no explanation."""

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        import json
        return json.loads(response.choices[0].message.content)
```

#### 5.3 State Manager

```python
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class Resource:
    """Represents a resource in the mock database."""
    id: str
    type: str
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1


class StateManager:
    """Manages stateful behavior for API simulator."""

    def __init__(self):
        self.resources: Dict[str, Dict[str, Resource]] = {}  # {type: {id: Resource}}
        self.faker = Faker()

    def create(self, resource_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new resource."""

        # Generate ID if not provided
        resource_id = data.get("id") or str(uuid.uuid4())

        # Create resource
        resource = Resource(
            id=resource_id,
            type=resource_type,
            data=data
        )

        # Store
        if resource_type not in self.resources:
            self.resources[resource_type] = {}

        self.resources[resource_type][resource_id] = resource

        return {
            "id": resource_id,
            **data,
            "created_at": resource.created_at.isoformat(),
            "updated_at": resource.updated_at.isoformat()
        }

    def get(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Get a single resource by ID."""

        if resource_type not in self.resources:
            return {"error": "Not Found", "status_code": 404}

        resource = self.resources[resource_type].get(resource_id)
        if not resource:
            return {"error": "Not Found", "status_code": 404}

        return {
            "id": resource.id,
            **resource.data,
            "created_at": resource.created_at.isoformat(),
            "updated_at": resource.updated_at.isoformat()
        }

    def list(self, resource_type: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """List resources with filtering, pagination."""

        if resource_type not in self.resources:
            return {"items": [], "total": 0}

        all_resources = list(self.resources[resource_type].values())

        # Apply filters
        filtered = all_resources
        for key, value in query_params.items():
            if key not in ["page", "limit", "sort"]:
                filtered = [r for r in filtered if r.data.get(key) == value]

        # Pagination
        page = int(query_params.get("page", 1))
        limit = int(query_params.get("limit", 10))
        start = (page - 1) * limit
        end = start + limit

        items = [
            {
                "id": r.id,
                **r.data,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat()
            }
            for r in filtered[start:end]
        ]

        return {
            "items": items,
            "total": len(filtered),
            "page": page,
            "limit": limit
        }

    def update(self, resource_type: str, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing resource."""

        if resource_type not in self.resources:
            return {"error": "Not Found", "status_code": 404}

        resource = self.resources[resource_type].get(resource_id)
        if not resource:
            return {"error": "Not Found", "status_code": 404}

        # Update data
        resource.data.update(data)
        resource.updated_at = datetime.now()
        resource.version += 1

        return {
            "id": resource.id,
            **resource.data,
            "created_at": resource.created_at.isoformat(),
            "updated_at": resource.updated_at.isoformat(),
            "version": resource.version
        }

    def delete(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Delete a resource."""

        if resource_type not in self.resources:
            return {"error": "Not Found", "status_code": 404}

        if resource_id not in self.resources[resource_type]:
            return {"error": "Not Found", "status_code": 404}

        del self.resources[resource_type][resource_id]

        return {"message": "Deleted successfully", "status_code": 204}

    def reset(self):
        """Reset all state."""
        self.resources.clear()

    def seed_data(self, resource_type: str, count: int = 10):
        """Seed mock data for a resource type."""
        for _ in range(count):
            self.create(resource_type, self._generate_mock_data(resource_type))

    def _generate_mock_data(self, resource_type: str) -> Dict[str, Any]:
        """Generate realistic mock data based on resource type."""

        if resource_type == "users":
            return {
                "name": self.faker.name(),
                "email": self.faker.email(),
                "phone": self.faker.phone_number(),
                "address": self.faker.address()
            }
        elif resource_type == "products":
            return {
                "name": self.faker.catch_phrase(),
                "price": round(random.uniform(10, 1000), 2),
                "description": self.faker.text(max_nb_chars=200),
                "in_stock": random.choice([True, False])
            }
        else:
            # Generic mock data
            return {
                "name": self.faker.word(),
                "description": self.faker.sentence(),
                "value": random.randint(1, 100)
            }
```

#### 5.4 Mock Server

```python
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import random

class APIMockServer:
    """On-demand API mock server."""

    def __init__(
        self,
        endpoint_specs: List[APIEndpointSpec],
        response_generator: ResponseGenerator,
        state_manager: StateManager
    ):
        self.app = FastAPI(title="UFIS API Simulator", version="1.0.0")
        self.specs = {f"{spec.method}:{spec.path}": spec for spec in endpoint_specs}
        self.generator = response_generator
        self.state = state_manager

        self._setup_middleware()
        self._register_endpoints()
        self._register_control_endpoints()

    def _setup_middleware(self):
        """Setup CORS and logging middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )

    def _register_endpoints(self):
        """Dynamically register all API endpoints."""

        for key, spec in self.specs.items():
            self._create_endpoint(spec)

    def _create_endpoint(self, spec: APIEndpointSpec):
        """Create a single API endpoint."""

        async def endpoint_handler(request: Request, **path_params):
            # Simulate latency
            await self._simulate_latency(spec.estimated_latency_ms)

            # Simulate errors (10% chance)
            if random.random() < 0.1 and 500 in spec.status_codes:
                raise HTTPException(status_code=500, detail="Internal Server Error (simulated)")

            # Check authentication
            if spec.authentication_required:
                auth_header = request.headers.get("Authorization")
                if not auth_header:
                    raise HTTPException(status_code=401, detail="Unauthorized")

            # Parse request data
            request_data = {
                "path_params": path_params,
                "query_params": dict(request.query_params),
                "headers": dict(request.headers)
            }

            if spec.method in ["POST", "PUT", "PATCH"]:
                request_data["body"] = await request.json()

            # Generate response
            response_data = self.generator.generate_response(
                spec,
                request_data,
                self.state
            )

            # Check for error response
            if "status_code" in response_data and response_data["status_code"] >= 400:
                raise HTTPException(
                    status_code=response_data["status_code"],
                    detail=response_data.get("error", "Error")
                )

            # Simulate side effects
            await self._simulate_side_effects(spec.side_effects)

            return JSONResponse(content=response_data)

        # Register with FastAPI
        method = spec.method.lower()
        path = spec.path.replace("{id}", "{id:path}").replace("{pk}", "{pk:path}")

        self.app.add_api_route(
            path,
            endpoint_handler,
            methods=[spec.method],
            tags=["simulated"]
        )

    async def _simulate_latency(self, latency_ms: int):
        """Simulate network latency."""
        # Add some randomness (±30%)
        actual_latency = latency_ms * random.uniform(0.7, 1.3)
        await asyncio.sleep(actual_latency / 1000.0)

    async def _simulate_side_effects(self, side_effects: List[str]):
        """Simulate side effects."""
        for effect in side_effects:
            if effect == "send_email":
                print(f"[SIMULATOR] Simulated: Email sent")
            elif effect == "send_notification":
                print(f"[SIMULATOR] Simulated: Notification sent")
            elif effect == "cache_update":
                print(f"[SIMULATOR] Simulated: Cache updated")
            elif effect == "enqueue_task":
                print(f"[SIMULATOR] Simulated: Background task enqueued")

    def _register_control_endpoints(self):
        """Register simulator control endpoints."""

        @self.app.post("/simulator/reset")
        async def reset_state():
            """Reset all simulator state."""
            self.state.reset()
            return {"message": "State reset successfully"}

        @self.app.post("/simulator/seed/{resource_type}")
        async def seed_data(resource_type: str, count: int = 10):
            """Seed mock data for a resource type."""
            self.state.seed_data(resource_type, count)
            return {"message": f"Seeded {count} {resource_type}"}

        @self.app.get("/simulator/endpoints")
        async def list_endpoints():
            """List all simulated endpoints."""
            return [
                {
                    "method": spec.method,
                    "path": spec.path,
                    "handler": spec.handler_function,
                    "authenticated": spec.authentication_required
                }
                for spec in self.specs.values()
            ]

        @self.app.get("/simulator/stats")
        async def get_stats():
            """Get simulator statistics."""
            return {
                "total_endpoints": len(self.specs),
                "resources": {
                    resource_type: len(resources)
                    for resource_type, resources in self.state.resources.items()
                }
            }

    def run(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the mock server."""
        import uvicorn
        print(f"🚀 UFIS API Simulator running on http://{host}:{port}")
        print(f"📋 Simulating {len(self.specs)} endpoints")
        print(f"📖 API docs: http://{host}:{port}/docs")
        uvicorn.run(self.app, host=host, port=port)
```

---

### Usage Examples

#### Example 1: Generate Mock Server for Your API

```python
from ufis import EndpointAnalyzer, ResponseGenerator, StateManager, APIMockServer

# Initialize UFIS
analyzer = EndpointAnalyzer(neo4j_client, qdrant_client)
generator = ResponseGenerator(openai_client)
state_manager = StateManager()

# Analyze your codebase
endpoint_specs = analyzer.analyze_endpoints(namespace="my-api")

# Create mock server
mock_server = APIMockServer(endpoint_specs, generator, state_manager)

# Seed some data
state_manager.seed_data("users", count=50)
state_manager.seed_data("products", count=100)

# Start server
mock_server.run(port=8080)
```

Now your API is available at `http://localhost:8080` with realistic behavior!

#### Example 2: Frontend Development

```javascript
// Your frontend can develop against the mock API
const response = await fetch('http://localhost:8080/api/users/123');
const user = await response.json();

console.log(user);
// Output: { id: "123", name: "John Doe", email: "john@example.com", ... }

// CRUD operations work!
const newUser = await fetch('http://localhost:8080/api/users', {
  method: 'POST',
  body: JSON.stringify({ name: "Jane Smith", email: "jane@example.com" })
});
```

#### Example 3: Integration Testing

```python
import pytest
from your_app import create_app

def test_user_flow():
    """Test complete user registration and login flow."""

    # Use mock API for external service
    mock_server.start_background()

    app = create_app()
    client = app.test_client()

    # Register user
    response = client.post('/register', json={
        "email": "test@example.com",
        "password": "secret123"
    })
    assert response.status_code == 201

    # Mock API automatically handles subsequent calls
    # Login
    response = client.post('/login', json={
        "email": "test@example.com",
        "password": "secret123"
    })
    assert response.status_code == 200
    assert "token" in response.json
```

#### Example 4: Performance Testing

```python
import asyncio
import aiohttp

async def load_test():
    """Test API under load with realistic responses."""

    async with aiohttp.ClientSession() as session:
        tasks = []

        # Simulate 1000 concurrent requests
        for i in range(1000):
            task = session.get(f'http://localhost:8080/api/users/{i}')
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # Analyze results
        success_count = sum(1 for r in responses if r.status == 200)
        print(f"Success rate: {success_count/1000*100}%")

asyncio.run(load_test())
```

---

### Benefits

| Benefit | Traditional Mocking | UFIS API Simulator |
|---------|-------------------|-------------------|
| **Setup Time** | Hours (manual config) | Minutes (automatic) |
| **Accuracy** | Low (hardcoded responses) | High (code-aware) |
| **Stateful Behavior** | No | Yes (CRUD works) |
| **Realistic Latency** | No | Yes (code-based estimates) |
| **Error Scenarios** | Manual | Automatic (from code analysis) |
| **Side Effect Simulation** | No | Yes (emails, cache, etc.) |
| **Schema Validation** | Manual | Automatic |
| **Maintenance** | High (manual updates) | Low (syncs with code) |

---

### Future Enhancements

1. **Contract Testing Integration** - Generate Pact contracts automatically
2. **Chaos Engineering** - Inject failures based on code analysis
3. **Traffic Recording** - Record real API traffic and replay in mocks
4. **Multi-Service Orchestration** - Simulate microservice interactions
5. **ML-Based Response Generation** - Learn from real API responses
6. **Performance Profiling** - Identify bottlenecks in simulated flows

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Implement core code flow analysis

**Tasks**:
1. **Week 1: Call Graph Extraction**
   - Implement `_extract_calls()` in `python_parser.py`
   - Add CALLS relationship to Neo4j loader
   - Write unit tests for call extraction
   - Test with FlowRAG codebase itself

2. **Week 2: API Route Detection**
   - Implement `_extract_api_routes()` for FastAPI/Flask
   - Create APIEndpoint node type
   - Add HANDLES relationships
   - Test with FlowRAG API endpoints

**Deliverables**:
- ✅ Working call graph extraction
- ✅ API route detection
- ✅ Updated Neo4j schema
- ✅ Test coverage >80%

**Success Metrics**:
- Extract 100% of function calls from test codebase
- Detect all API endpoints in FlowRAG

---

### Phase 2: Control & Data Flow (Weeks 3-4)

**Goal**: Add control flow and data flow analysis

**Tasks**:
1. **Week 3: Control Flow**
   - Implement `_extract_control_flow()`
   - Track if/else, try/except, loops
   - Add complexity metrics to CodeUnit nodes
   - Visualize control flow paths

2. **Week 4: Data Flow**
   - Implement `_extract_data_flow()`
   - Track variable assignments and parameters
   - Add data flow edges to graph
   - Test with data pipeline code

**Deliverables**:
- ✅ Control flow extraction
- ✅ Data flow tracking
- ✅ Enhanced CodeUnit metadata
- ✅ Flow visualization tools

**Success Metrics**:
- Detect all control structures
- Track data flow through 3+ function calls

---

### Phase 3: Document Flow Inference (Weeks 5-6)

**Goal**: Extract workflows from documentation

**Tasks**:
1. **Week 5: Step Extraction**
   - Implement `DocumentFlowInference` class
   - Pattern matching for numbered steps
   - LLM-based structure analysis
   - Handle PDF, Markdown, HTML formats

2. **Week 6: Dependency Inference**
   - Implement `_extract_dependencies()`
   - Temporal language analysis ("after", "before")
   - Parallel opportunity detection
   - Create ProcessStep nodes in Neo4j

**Deliverables**:
- ✅ Automated workflow extraction
- ✅ Dependency inference
- ✅ ProcessStep graph structure
- ✅ Test with 10+ documentation types

**Success Metrics**:
- Extract 90%+ of explicit steps from documentation
- Infer 70%+ of implicit dependencies correctly

---

### Phase 4: Unification & Querying (Weeks 7-8)

**Goal**: Link code to docs and enable flow-aware queries

**Tasks**:
1. **Week 7: Flow Unification**
   - Implement `FlowUnification` class
   - Semantic similarity matching
   - Name-based code-to-doc linking
   - Create IMPLEMENTS relationships

2. **Week 8: Query Engine**
   - Implement `FlowAwareQueryEngine`
   - Question classification
   - Parallel step detection queries
   - Dependency traversal queries
   - Call graph visualization
   - Path finding algorithms

**Deliverables**:
- ✅ Unified knowledge graph
- ✅ Flow-aware query API
- ✅ Web UI for flow queries
- ✅ Comprehensive documentation

**Success Metrics**:
- Link 80%+ of documented procedures to code
- Answer flow questions with 90%+ accuracy

---

### Phase 5: API Simulator (Weeks 9-10)

**Goal**: Build on-demand API simulation capabilities

**Tasks**:
1. **Week 9: Endpoint Analysis & Response Generation**
   - Implement `EndpointAnalyzer` class
   - Extract API routes from graph
   - Analyze handler functions for behavior
   - Implement `ResponseGenerator` with schema-based and LLM-based generation
   - Build `StateManager` for CRUD operations

2. **Week 10: Mock Server & Integration**
   - Implement `APIMockServer` with FastAPI
   - Dynamic endpoint registration
   - Latency and error simulation
   - Side effect simulation
   - Control endpoints (/simulator/reset, /simulator/seed)
   - Integration with UFIS query engine

**Deliverables**:
- ✅ Automatic endpoint discovery
- ✅ Intelligent response generation
- ✅ Stateful mock server
- ✅ Performance simulation (latency, errors)
- ✅ CLI and API for simulator control

**Success Metrics**:
- Discover 100% of API endpoints automatically
- Generate valid responses for 95%+ of endpoints
- Simulate realistic latency within 20% of actual
- Support stateful CRUD operations correctly

---

## Market Positioning

### Target Markets

#### 1. DevOps & SRE Teams
**Problem**: Complex deployment procedures, unclear dependencies
**Solution**: Automated workflow extraction, parallel execution detection
**Value**: Reduce deployment time by 40%, eliminate manual procedure documentation

#### 2. API Development Teams
**Problem**: Unclear service dependencies, undocumented API flows
**Solution**: Automatic call graph extraction, API route mapping
**Value**: Accelerate debugging, improve API documentation quality

#### 3. Enterprise Onboarding
**Problem**: Slow developer ramp-up, scattered documentation
**Solution**: Unified code + docs knowledge graph, flow-aware search
**Value**: Reduce onboarding time from months to weeks

#### 4. Incident Response
**Problem**: Understanding system behavior during outages
**Solution**: Execution path tracing, dependency visualization
**Value**: Reduce MTTR (Mean Time To Resolution) by 50%

#### 5. Compliance & Auditing
**Problem**: Proving actual vs. documented workflows
**Solution**: Automated code-to-doc linking, flow verification
**Value**: Streamline compliance audits, reduce documentation burden

---

### Competitive Analysis

| Feature | UFIS | GitHub Copilot | Sourcegraph | Swimm | Postman | WireMock |
|---------|------|----------------|-------------|-------|---------|----------|
| **Code Call Graph** | ✅ Automatic | ❌ | ⚠️ Manual | ❌ | ❌ | ❌ |
| **Doc Workflow Extraction** | ✅ Automatic | ❌ | ❌ | ⚠️ Manual | ❌ | ❌ |
| **Code-to-Doc Linking** | ✅ Semantic | ❌ | ❌ | ✅ Manual | ❌ | ❌ |
| **Flow-Aware Queries** | ✅ | ❌ | ⚠️ Basic | ❌ | ❌ | ❌ |
| **Parallel Detection** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Dependency Inference** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **API Simulator** | ✅ Auto | ❌ | ❌ | ❌ | ⚠️ Manual | ⚠️ Manual |
| **Stateful Mocks** | ✅ | ❌ | ❌ | ❌ | ⚠️ Limited | ⚠️ Limited |
| **LLM-Enhanced Responses** | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Multi-Language** | ✅ | ✅ | ✅ | ⚠️ Limited | ✅ | ✅ |

**Unique Differentiators**:
1. **Only solution that unifies code and docs** in a single graph
2. **Automatic inference** of implicit flows (no manual annotation)
3. **Flow-aware querying** (not just text search)
4. **Parallel opportunity detection** (DevOps use case)
5. **On-demand API simulation** with intelligent, code-aware mocking
6. **LLM-enhanced mock generation** for realistic, context-aware responses

---

### Go-to-Market Strategy

#### Phase 1: Open Source Launch
- Release UFIS as open-source extension to FlowRAG
- Target: Developer communities (Reddit, HackerNews, DevTo)
- Free tier: Unlimited for public repos

#### Phase 2: Enterprise Pilots
- Identify 5-10 enterprise pilot customers
- Focus: DevOps teams with complex deployment procedures
- Pricing: $500/month per team (5-10 users)

#### Phase 3: SaaS Platform
- Launch hosted version (cloud or on-premise)
- Pricing tiers:
  - **Starter**: $99/mo (1 repo, 5 users)
  - **Team**: $499/mo (10 repos, 25 users)
  - **Enterprise**: Custom (unlimited, SSO, support)

#### Phase 4: Marketplace Integrations
- GitHub App
- GitLab Integration
- Jira Plugin (link tickets to flows)
- Slack Bot (query flows from chat)

---

### Demo Script

**Scenario**: DevOps team managing Kubernetes deployment pipeline

1. **Ingest codebase**:
   ```bash
   flowrag ingest directory /path/to/k8s-pipeline --namespace prod-deploy
   ```

2. **Ingest documentation**:
   ```bash
   flowrag ingest document /docs/deployment-guide.pdf --namespace prod-deploy
   ```

3. **Query: "What steps can run in parallel?"**
   ```
   Result:
   - Step 3 (Build Docker Images) and Step 4 (Run Unit Tests) can run in parallel
   - Both only require Step 2 (Code Checkout) to complete
   - Estimated time savings: 5 minutes per deployment
   ```

4. **Query: "What functions are called during rollback?"**
   ```
   Result:
   rollback_deployment() calls:
     ├─ get_previous_version()
     ├─ validate_rollback_target()
     ├─ kubectl_apply()
     └─ notify_team()

   Documented in: "Rollback Procedures" (Section 7, page 23)
   ```

5. **Visualization**:
   ```
   [Interactive flow diagram showing deployment pipeline with parallel paths highlighted]
   ```

---

## References

### Related Systems

1. **Code Analysis**:
   - Tree-sitter (AST parsing)
   - Sourcegraph (code search)
   - CodeQL (semantic code analysis)

2. **Knowledge Graphs**:
   - Neo4j (graph database)
   - Microsoft Academic Graph
   - Google Knowledge Graph

3. **Documentation**:
   - Docusaurus (static site generation)
   - Swimm (code-coupled docs)
   - GitBook (documentation platform)

4. **Flow Analysis**:
   - Apache Airflow (DAG-based workflows)
   - Prefect (data pipeline orchestration)
   - Temporal (workflow engine)

---

### Technical Papers

1. **Call Graph Construction**:
   - "Scalable Call Graph Construction for Java" (OOPSLA 2011)
   - "Fast and Precise Call Graph Construction" (ISSTA 2016)

2. **Program Analysis**:
   - "Control Flow Analysis" (ACM Computing Surveys)
   - "Data Flow Analysis" (Principles of Program Analysis)

3. **Knowledge Graph Embeddings**:
   - "TransE: Translating Embeddings for Knowledge Graphs" (NIPS 2013)
   - "Knowledge Graph Embedding: A Survey" (IEEE 2020)

4. **NLP for Documentation**:
   - "Extracting API Usage Constraints from Documentation" (ICSE 2018)
   - "Automated Inference of API Documentation" (ASE 2019)

---

## Appendix

### A. Example Queries

```cypher
// Find all parallel execution opportunities
MATCH (s:ProcessStep {namespace: $namespace})
OPTIONAL MATCH (s)-[:REQUIRES]->(prereq)
WITH s, collect(prereq.step_number) as prerequisites
WITH prerequisites, collect(s) as steps
WHERE size(steps) > 1
RETURN prerequisites, steps

// Find execution path between two functions
MATCH (start:CodeUnit {name: $start_func})
MATCH (end:CodeUnit {name: $end_func})
MATCH path = shortestPath((start)-[:CALLS*]->(end))
RETURN path

// Find undocumented code
MATCH (c:CodeUnit)
WHERE NOT (c)-[:IMPLEMENTS]->(:ProcessStep)
  AND c.type IN ['function', 'method', 'class']
RETURN c.name, c.file_path

// Find documented procedures without code implementation
MATCH (s:ProcessStep)
WHERE NOT (s)<-[:IMPLEMENTS]-(:CodeUnit)
RETURN s.name, s.description

// Find API endpoints and their call chains
MATCH (e:APIEndpoint)-[:HANDLES]->(handler:CodeUnit)
MATCH path = (handler)-[:CALLS*1..5]->(callee:CodeUnit)
RETURN e.method, e.path, collect(callee.name) as call_chain
```

---

### B. Configuration Examples

**.env Configuration**:

```bash
# UFIS Configuration
ENABLE_CODE_FLOW_ANALYSIS=true
ENABLE_DOC_FLOW_INFERENCE=true
ENABLE_FLOW_UNIFICATION=true

# Supported Languages
SUPPORTED_CODE_LANGUAGES=python,javascript,typescript,java,go
SUPPORTED_DOC_FORMATS=pdf,markdown,html,rst

# LLM Configuration (for doc analysis)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Flow Analysis Settings
MIN_CONFIDENCE_CODE_TO_DOC=0.75
ENABLE_PARALLEL_DETECTION=true
MAX_CALL_DEPTH=10

# Performance
BATCH_SIZE=100
WORKER_THREADS=4
```

---

### C. API Examples

**REST API**:

```bash
# Ingest code
POST /api/v1/ingest/directory
{
  "directory_path": "/path/to/code",
  "namespace": "my-project",
  "enable_flow_analysis": true
}

# Ingest documentation
POST /api/v1/ingest/document
{
  "file_path": "/path/to/docs.pdf",
  "namespace": "my-project",
  "enable_workflow_extraction": true
}

# Flow-aware query
POST /api/v1/query/flow
{
  "question": "What steps can run in parallel?",
  "namespace": "my-project"
}

# Call graph query
POST /api/v1/query/callgraph
{
  "function_name": "process_data",
  "namespace": "my-project",
  "direction": "both"  # callers and callees
}

# Dependency query
POST /api/v1/query/dependencies
{
  "step_number": "5",
  "namespace": "my-project",
  "include_transitive": true
}
```

---

### D. Testing Strategy

**Unit Tests**:
- Call extraction accuracy
- API route detection
- Step pattern matching
- Dependency inference

**Integration Tests**:
- End-to-end ingestion pipeline
- Neo4j + Qdrant consistency
- Query engine accuracy

**Performance Tests**:
- Large codebase ingestion (100k+ LOC)
- Query response time (<500ms)
- Graph traversal efficiency

**Accuracy Tests**:
- Code-to-doc linking precision/recall
- Flow inference accuracy (manual validation)
- Parallel detection correctness

---

**End of Document**

---

## Next Steps

1. **Review and approve** this design document
2. **Set up development environment** for Phase 1
3. **Create GitHub issues** for each task in roadmap
4. **Begin implementation** of call graph extraction
5. **Recruit beta testers** from target markets

For questions or contributions, please contact the FlowRAG team or open an issue in the repository.
