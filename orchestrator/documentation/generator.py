"""
Documentation Generator - Creates comprehensive service documentation.

Generates high-level design documents with Mermaid diagrams, component documentation,
API documentation, and data model documentation.
"""

import logging
from typing import List, Dict, Any, Optional
from databases.neo4j.client import get_neo4j_client
from databases.qdrant.client import get_qdrant_client
from agents.llm import get_response_generator, ResponseRequest
from orchestrator import get_orchestrator, OrchestrationRequest
from orchestrator.context.context_assembler import AssembledContext, ContextItem
from orchestrator.router.intent_classifier import QueryIntent
from orchestrator.controller import OrchestrationResult
from .inter_service_detector import get_inter_service_detector

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """
    Generates comprehensive documentation for ingested codebases.

    Uses graph analysis, semantic search, and LLM to create:
    - Architecture overviews
    - Mermaid diagrams (architecture, sequence, data flow)
    - Component documentation
    - API documentation
    - Data model documentation
    - Inter-service call documentation
    """

    def __init__(self):
        """Initialize documentation generator."""
        self.neo4j_client = get_neo4j_client()
        self.qdrant_client = get_qdrant_client()
        self.orchestrator = get_orchestrator()
        self.response_generator = get_response_generator()
        self.service_call_detector = get_inter_service_detector()

    async def generate(
        self,
        namespace: str,
        include_diagrams: bool = True,
        include_api_docs: bool = True,
        include_data_models: bool = True,
        include_architecture: bool = True,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Generate comprehensive documentation.

        Args:
            namespace: Namespace to document
            include_diagrams: Include Mermaid diagrams
            include_api_docs: Include API documentation
            include_data_models: Include data model documentation
            include_architecture: Include architecture overview
            max_depth: Analysis depth

        Returns:
            Complete documentation result
        """
        logger.info(f"Generating documentation for namespace: {namespace}")

        # Step 1: Analyze codebase structure
        structure = self._analyze_structure(namespace)

        # Step 2: Get service overview
        service_info = await self._get_service_overview(namespace, structure)

        # Step 3: Generate architecture diagrams
        diagrams = []
        if include_diagrams:
            diagrams = await self._generate_diagrams(namespace, structure)

        # Step 4: Document components
        components = self._document_components(namespace, structure)

        # Step 5: Document APIs
        api_endpoints = []
        if include_api_docs:
            api_endpoints = self._document_apis(namespace, structure)

        # Step 6: Document data models
        data_models = []
        if include_data_models:
            data_models = self._document_data_models(namespace, structure)

        # Step 7: Detect inter-service calls
        service_calls = []
        try:
            logger.info(f"Detecting inter-service calls for namespace: {namespace}")
            service_calls_objs = self.service_call_detector.detect_service_calls(namespace)
            service_calls = [call.to_dict() for call in service_calls_objs]
            logger.info(f"Detected {len(service_calls)} inter-service calls")
        except Exception as e:
            logger.warning(f"Failed to detect inter-service calls: {e}")

        # Step 8: Add service calls to responsibilities if found
        if service_calls:
            responsibilities = service_info.get("responsibilities", [])
            service_types = set(call["call_type"] for call in service_calls)

            for service_type in service_types:
                count = sum(1 for c in service_calls if c["call_type"] == service_type)
                responsibilities.append(f"Integrates with external {service_type} services ({count} calls)")

            service_info["responsibilities"] = responsibilities

        # Step 9: Generate markdown documentation
        markdown = self._generate_markdown(
            namespace,
            service_info,
            diagrams,
            components,
            api_endpoints,
            data_models,
            service_calls
        )

        return {
            "success": True,
            "namespace": namespace,
            "service_name": service_info.get("name", namespace),
            "description": service_info.get("description", ""),
            "architecture_summary": service_info.get("architecture_summary", ""),
            "responsibilities": service_info.get("responsibilities", []),
            "diagrams": diagrams,
            "components": components,
            "api_endpoints": api_endpoints,
            "data_models": data_models,
            "service_calls": service_calls,
            "markdown_documentation": markdown,
            "total_files": structure.get("total_files", 0),
            "total_components": len(components),
            "total_service_calls": len(service_calls),
            "generation_time": 0.0,  # Will be set by endpoint
        }

    async def preview(self, namespace: str) -> Dict[str, Any]:
        """Get a quick preview of what will be documented."""
        structure = self._analyze_structure(namespace)

        return {
            "namespace": namespace,
            "total_files": structure.get("total_files", 0),
            "total_components": structure.get("total_components", 0),
            "component_types": structure.get("component_types", {}),
            "has_apis": structure.get("has_routes", False),
            "has_models": structure.get("has_models", False),
        }

    async def get_markdown(self, namespace: str) -> str:
        """Get markdown documentation (cached or generate)."""
        # For now, regenerate - could be cached in future
        result = await self.generate(namespace)
        return result.get("markdown_documentation", "")

    def _analyze_structure(self, namespace: str) -> Dict[str, Any]:
        """
        Analyze codebase structure using Neo4j graph.

        Identifies:
        - File structure
        - Component types (controllers, services, models, etc.)
        - Relationships
        - Entry points
        """
        logger.info(f"Analyzing structure for namespace: {namespace}")

        # Query Neo4j for codebase structure
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        WITH n
        OPTIONAL MATCH (n)-[r]->()
        RETURN
            n.type as node_type,
            n.name as name,
            n.file_path as file_path,
            count(r) as relationships_count
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})

            # Analyze results
            structure = {
                "total_files": len(set(r.get("file_path") for r in results if r.get("file_path"))),
                "total_components": len(results),
                "component_types": {},
                "has_routes": False,
                "has_models": False,
                "files": set(),
            }

            for result in results:
                node_type = result.get("node_type", "unknown")
                file_path = result.get("file_path")

                # Count by type
                structure["component_types"][node_type] = structure["component_types"].get(node_type, 0) + 1

                # Detect routes/APIs
                if file_path and ("route" in file_path.lower() or "controller" in file_path.lower() or "endpoint" in file_path.lower()):
                    structure["has_routes"] = True

                # Detect models
                if file_path and ("model" in file_path.lower() or "schema" in file_path.lower() or "entity" in file_path.lower()):
                    structure["has_models"] = True

                if file_path:
                    structure["files"].add(file_path)

            return structure

        except Exception as e:
            logger.error(f"Failed to analyze structure: {e}")
            return {
                "total_files": 0,
                "total_components": 0,
                "component_types": {},
                "has_routes": False,
                "has_models": False,
            }

    async def _get_service_overview(self, namespace: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get high-level service overview using LLM.

        Generates:
        - Service name
        - Description
        - Architecture summary
        - Key responsibilities
        """
        logger.info("Generating service overview")

        # First, try to get package.json or configuration files directly from Neo4j
        config_query = """
        MATCH (n)
        WHERE n.namespace = $namespace
          AND (n.file_path =~ '.*package\\.json$'
               OR n.file_path =~ '.*setup\\.py$'
               OR n.file_path =~ '.*pom\\.xml$'
               OR n.name =~ '.*Config.*'
               OR n.name =~ '.*Server.*'
               OR n.name =~ '.*Application.*'
               OR n.name =~ '.*Main.*')
        RETURN n.file_path as file_path, n.name as name, n.code as code, n.type as type
        LIMIT 10
        """

        try:
            config_results = self.neo4j_client.execute_query(config_query, {"namespace": namespace})
            logger.info(f"Found {len(config_results)} configuration/entry files")
        except Exception as e:
            logger.warning(f"Could not query Neo4j for config files: {e}")
            config_results = []

        # Use orchestrator to get additional relevant code
        queries = [
            f"package.json configuration main dependencies typescript nodejs",
            f"main application entry point server setup controllers",
            f"primary business logic services features functionality",
        ]

        all_contexts = []

        # Add config files from Neo4j as context items
        from orchestrator.context.context_assembler import ContextItem
        for config in config_results:
            if config.get('code'):
                context_item = ContextItem(
                    content=config.get('code', ''),
                    source_type=config.get('type', 'unknown'),
                    relevance_score=0.95,  # High relevance for config files
                    citation=f"{config.get('file_path', 'unknown')}:{config.get('name', 'unknown')}",
                    metadata={"file_path": config.get('file_path', '')}
                )
                all_contexts.append(context_item)

        # Get additional context via semantic search
        for query in queries:
            orch_request = OrchestrationRequest(
                query=query,
                namespace=namespace,
                max_results=5,
            )
            result = self.orchestrator.orchestrate(orch_request)
            if result.context and result.context.items:
                all_contexts.extend(result.context.items)

        logger.info(f"Collected {len(all_contexts)} context items for service overview")

        # Create combined context
        from orchestrator.context.context_assembler import AssembledContext
        combined_context = AssembledContext(
            items=all_contexts[:25],  # Increased to 25 most relevant
            total_items=len(all_contexts)
        )

        # Use the first query result for the mock
        orch_request = OrchestrationRequest(
            query=queries[0],
            namespace=namespace,
            max_results=10,
        )
        orch_result = self.orchestrator.orchestrate(orch_request)
        orch_result.context = combined_context

        # Build prompt for LLM
        prompt = f"""You are analyzing a codebase to generate comprehensive documentation. Based on the code provided below, identify the ACTUAL purpose and functionality of this service.

**Codebase Statistics:**
- Total Files: {structure.get('total_files', 0)}
- Total Components: {structure.get('total_components', 0)}
- Component Types: {structure.get('component_types', {})}

**Code Context (Configuration Files, Entry Points, Main Modules):**
{self._format_context(combined_context)}

**Critical Instructions:**
1. Look for package.json, setup.py, or similar configuration files to understand the project name and description
2. Examine import statements and dependencies to understand the tech stack
3. Analyze controller names, service names, and module structure to identify features
4. DO NOT use generic/hypothetical descriptions - be SPECIFIC based on the actual code
5. If you see AWS SDK, identify which AWS services are used
6. If you see AI libraries (openai, anthropic), mention AI capabilities
7. If you see Terraform/infrastructure code, mention infrastructure provisioning
8. If you see authentication code, mention auth features

**Your Task:**
Generate a SPECIFIC service overview including:
1. **Service Name**: Extract from package.json "name" field or project structure (NOT generic names like "GenericService")
2. **Description**: 2-3 specific sentences about what THIS PARTICULAR service does (mention actual features, technologies, and use cases)
3. **Architecture Summary**: Describe the ACTUAL architecture used (frontend/backend frameworks, databases, external services)
4. **Key Responsibilities**: List 3-5 SPECIFIC responsibilities based on the actual controllers, services, and modules found

**Output Format (JSON):**
{{
  "name": "<Actual Service Name from package.json>",
  "description": "<Specific description mentioning actual technologies and features>",
  "architecture_summary": "<Real architecture: frameworks, databases, cloud services used>",
  "responsibilities": [
    "<Specific responsibility 1 based on actual code>",
    "<Specific responsibility 2 based on actual code>",
    "..."
  ]
}}

**Example of GOOD output:**
{{
  "name": "Chart App",
  "description": "AI-powered AWS infrastructure provisioning platform that generates Terraform code, creates UML diagrams, and provides multi-tenant infrastructure deployment using Anthropic Claude and OpenAI.",
  "architecture_summary": "Full-stack TypeScript application with Next.js frontend, Express.js backend, AWS SDK for cloud operations, and Python-based Terraform runner for infrastructure provisioning",
  "responsibilities": [
    "AI-driven code generation using Anthropic Claude and OpenAI APIs",
    "UML diagram creation and visualization with Mermaid",
    "Automated Terraform infrastructure provisioning for AWS",
    "Multi-tenant project and user management with JWT authentication",
    "Cost estimation and infrastructure validation before deployment"
  ]
}}

**Example of BAD output (too generic):**
{{
  "name": "GenericService",
  "description": "A service designed to perform various operations",
  "architecture_summary": "Modern architecture",
  "responsibilities": ["Data processing", "Business logic", "API endpoints"]
}}

Generate the service overview now based on the ACTUAL code provided:"""

        # Generate with LLM
        mock_orch_result = OrchestrationResult(
            query=prompt,
            namespace=namespace,
            intent=QueryIntent.GENERAL_QUESTION,
            intent_confidence=0.9,
            context=orch_result.context,
            retrieval_result=orch_result.retrieval_result,
            total_retrieval_time=orch_result.total_retrieval_time,
        )

        response_request = ResponseRequest(
            orchestration_result=mock_orch_result,
            stream=False,
        )

        generated_response = await self.response_generator.generate_async(response_request)

        # Parse JSON response from LLM
        import json
        import re

        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            content = generated_response.content

            # Try to find JSON in code blocks first
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if not json_match:
                # Try to find any JSON object
                json_match = re.search(r'(\{[^{]*"name"[^}]*\})', content, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                parsed = json.loads(json_str)

                return {
                    "name": parsed.get("name", namespace.replace("-", " ").title()),
                    "description": parsed.get("description", "")[:1000],
                    "architecture_summary": parsed.get("architecture_summary", "Modern application architecture")[:500],
                    "responsibilities": parsed.get("responsibilities", [])[:10]
                }
            else:
                logger.warning("Could not extract JSON from LLM response, using fallback")
                # Fallback to extracting info from raw text
                return {
                    "name": namespace.replace("-", " ").title(),
                    "description": content[:500],
                    "architecture_summary": "Modern application architecture",
                    "responsibilities": []
                }

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "name": namespace.replace("-", " ").title(),
                "description": generated_response.content[:500],
                "architecture_summary": "Modern application architecture",
                "responsibilities": []
            }

    async def _generate_diagrams(self, namespace: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate Mermaid diagrams.

        Creates:
        - Architecture diagram (component relationships)
        - Sequence diagram (typical flow)
        - Data flow diagram
        """
        logger.info("Generating Mermaid diagrams")

        diagrams = []

        # 1. Architecture Diagram
        arch_diagram = await self._generate_architecture_diagram(namespace, structure)
        if arch_diagram:
            diagrams.append(arch_diagram)

        # 2. Sequence Diagram
        seq_diagram = await self._generate_sequence_diagram(namespace)
        if seq_diagram:
            diagrams.append(seq_diagram)

        # 3. Data Flow Diagram
        data_diagram = await self._generate_dataflow_diagram(namespace)
        if data_diagram:
            diagrams.append(data_diagram)

        return diagrams

    async def _generate_architecture_diagram(self, namespace: str, structure: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate architecture overview diagram."""
        # Query for component relationships
        query = """
        MATCH (n)-[r:IMPORTS|CALLS]->(m)
        WHERE n.namespace = $namespace AND m.namespace = $namespace
        RETURN DISTINCT
            n.file_path as from_file,
            m.file_path as to_file,
            type(r) as relationship_type
        LIMIT 100
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})

            if not results:
                return None

            # Build Mermaid flowchart
            mermaid_lines = ["graph TB"]

            # Extract unique files and create nodes
            files = set()
            for r in results:
                from_file = r.get("from_file", "").split("/")[-1]
                to_file = r.get("to_file", "").split("/")[-1]
                files.add(from_file)
                files.add(to_file)

            # Create simplified component groups
            components = {}
            for f in files:
                if "controller" in f.lower() or "route" in f.lower():
                    components[f] = "Controllers"
                elif "service" in f.lower():
                    components[f] = "Services"
                elif "model" in f.lower() or "schema" in f.lower():
                    components[f] = "Models"
                else:
                    components[f] = "Utilities"

            # Group by component type
            for component_type in set(components.values()):
                files_in_group = [f for f, t in components.items() if t == component_type]
                mermaid_lines.append(f"  subgraph {component_type}")
                for f in files_in_group[:5]:  # Limit to 5 per group
                    clean_name = f.replace(".", "_").replace("-", "_")
                    mermaid_lines.append(f"    {clean_name}[{f}]")
                mermaid_lines.append("  end")

            # Add relationships
            for r in results[:20]:  # Limit relationships
                from_file = r.get("from_file", "").split("/")[-1].replace(".", "_").replace("-", "_")
                to_file = r.get("to_file", "").split("/")[-1].replace(".", "_").replace("-", "_")
                mermaid_lines.append(f"  {from_file} --> {to_file}")

            diagram = "\n".join(mermaid_lines)

            return {
                "title": "System Architecture",
                "type": "flowchart",
                "diagram": diagram,
                "description": "High-level architecture showing component relationships"
            }

        except Exception as e:
            logger.error(f"Failed to generate architecture diagram: {e}")
            return None

    async def _generate_sequence_diagram(self, namespace: str) -> Optional[Dict[str, Any]]:
        """Generate sequence diagram for typical flow."""
        # Simplified sequence diagram
        diagram = """sequenceDiagram
    participant Client
    participant API
    participant Service
    participant Database

    Client->>API: HTTP Request
    API->>Service: Process Request
    Service->>Database: Query Data
    Database-->>Service: Return Data
    Service-->>API: Processed Response
    API-->>Client: HTTP Response
"""

        return {
            "title": "Typical Request Flow",
            "type": "sequence",
            "diagram": diagram,
            "description": "Sequence diagram showing typical request/response flow"
        }

    async def _generate_dataflow_diagram(self, namespace: str) -> Optional[Dict[str, Any]]:
        """Generate data flow diagram."""
        # Simplified data flow
        diagram = """graph LR
    A[User Input] --> B[Validation Layer]
    B --> C[Business Logic]
    C --> D[Data Access Layer]
    D --> E[Database]
    E --> D
    D --> C
    C --> F[Response Formatter]
    F --> G[Client]
"""

        return {
            "title": "Data Flow",
            "type": "flowchart",
            "diagram": diagram,
            "description": "Data flow through the system layers"
        }

    def _document_components(self, namespace: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Document major components."""
        logger.info("Documenting components")

        # Query for components
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        OPTIONAL MATCH (n)-[r]->(m)
        WITH n, collect(DISTINCT m.name) as dependencies
        RETURN
            n.name as name,
            n.type as type,
            n.file_path as file_path,
            dependencies
        LIMIT 50
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})

            components = []
            for r in results:
                component_type = r.get("type", "unknown")
                name = r.get("name", "Unknown")
                file_path = r.get("file_path", "")

                # Infer responsibilities based on type/name
                responsibilities = []
                if "controller" in file_path.lower():
                    responsibilities = ["Handle HTTP requests", "Route to appropriate services", "Return responses"]
                elif "service" in file_path.lower():
                    responsibilities = ["Implement business logic", "Coordinate data operations", "Process requests"]
                elif "model" in file_path.lower():
                    responsibilities = ["Define data structure", "Validate data", "Manage persistence"]

                components.append({
                    "name": name,
                    "type": component_type,
                    "description": f"{component_type} component",
                    "responsibilities": responsibilities,
                    "dependencies": r.get("dependencies", [])[:5],
                    "file_path": file_path
                })

            return components[:20]  # Limit to 20 components

        except Exception as e:
            logger.error(f"Failed to document components: {e}")
            return []

    def _document_apis(self, namespace: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Document API endpoints."""
        logger.info("Documenting APIs")

        # Query for route/controller files
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        AND (
            n.file_path CONTAINS 'route'
            OR n.file_path CONTAINS 'controller'
            OR n.file_path CONTAINS 'endpoint'
        )
        RETURN
            n.name as name,
            n.file_path as file_path,
            n.code as code
        LIMIT 20
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})

            endpoints = []
            for r in results:
                code = r.get("code", "")
                file_path = r.get("file_path", "")

                # Simple pattern matching for HTTP methods
                methods = []
                if "GET" in code or "get(" in code or "@Get" in code:
                    methods.append("GET")
                if "POST" in code or "post(" in code or "@Post" in code:
                    methods.append("POST")
                if "PUT" in code or "put(" in code or "@Put" in code:
                    methods.append("PUT")
                if "DELETE" in code or "delete(" in code or "@Delete" in code:
                    methods.append("DELETE")

                for method in methods:
                    endpoints.append({
                        "method": method,
                        "path": f"/api/{r.get('name', 'unknown')}",
                        "description": f"{method} endpoint",
                        "controller": file_path,
                        "parameters": [],
                        "responses": []
                    })

            return endpoints

        except Exception as e:
            logger.error(f"Failed to document APIs: {e}")
            return []

    def _document_data_models(self, namespace: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Document data models."""
        logger.info("Documenting data models")

        # Query for model/schema files
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        AND (
            n.file_path CONTAINS 'model'
            OR n.file_path CONTAINS 'schema'
            OR n.file_path CONTAINS 'entity'
            OR n.type = 'Class'
        )
        RETURN
            n.name as name,
            n.file_path as file_path,
            n.type as type
        LIMIT 20
        """

        try:
            results = self.neo4j_client.execute_query(query, {"namespace": namespace})

            models = []
            for r in results:
                models.append({
                    "name": r.get("name", "Unknown"),
                    "type": r.get("type", "model"),
                    "file_path": r.get("file_path", ""),
                    "fields": [],  # Would need code parsing to extract
                    "relationships": []
                })

            return models

        except Exception as e:
            logger.error(f"Failed to document data models: {e}")
            return []

    def _generate_markdown(
        self,
        namespace: str,
        service_info: Dict[str, Any],
        diagrams: List[Dict[str, Any]],
        components: List[Dict[str, Any]],
        api_endpoints: List[Dict[str, Any]],
        data_models: List[Dict[str, Any]],
        service_calls: List[Dict[str, Any]] = None
    ) -> str:
        """Generate complete markdown documentation."""
        md_lines = []

        # Title and Description
        md_lines.append(f"# {service_info.get('name', namespace)} Documentation\n")
        md_lines.append(f"{service_info.get('description', '')}\n")

        # Architecture Overview
        md_lines.append("## Architecture Overview\n")
        md_lines.append(f"{service_info.get('architecture_summary', '')}\n")

        # Diagrams
        if diagrams:
            md_lines.append("## System Diagrams\n")
            for diagram in diagrams:
                md_lines.append(f"### {diagram['title']}\n")
                md_lines.append(f"{diagram['description']}\n")
                md_lines.append("```mermaid")
                md_lines.append(diagram['diagram'])
                md_lines.append("```\n")

        # Components
        if components:
            md_lines.append("## Components\n")
            for comp in components[:10]:  # Top 10
                md_lines.append(f"### {comp['name']}\n")
                md_lines.append(f"**Type:** {comp['type']}\n")
                md_lines.append(f"**File:** `{comp['file_path']}`\n")
                if comp['responsibilities']:
                    md_lines.append("**Responsibilities:**")
                    for resp in comp['responsibilities']:
                        md_lines.append(f"- {resp}")
                md_lines.append("")

        # API Endpoints
        if api_endpoints:
            md_lines.append("## API Endpoints\n")
            for endpoint in api_endpoints[:15]:  # Top 15
                md_lines.append(f"### {endpoint['method']} {endpoint['path']}\n")
                md_lines.append(f"{endpoint['description']}\n")
                md_lines.append(f"**Controller:** `{endpoint['controller']}`\n")

        # Data Models
        if data_models:
            md_lines.append("## Data Models\n")
            for model in data_models[:10]:  # Top 10
                md_lines.append(f"### {model['name']}\n")
                md_lines.append(f"**Type:** {model['type']}\n")
                md_lines.append(f"**File:** `{model['file_path']}`\n")

        # Inter-Service Calls
        if service_calls:
            md_lines.append("## External Service Integrations\n")
            md_lines.append(f"This service integrates with {len(service_calls)} external services:\n")

            # Group by call type
            calls_by_type = {}
            for call in service_calls:
                call_type = call.get('call_type', 'unknown')
                if call_type not in calls_by_type:
                    calls_by_type[call_type] = []
                calls_by_type[call_type].append(call)

            for call_type, calls in calls_by_type.items():
                md_lines.append(f"### {call_type.upper()} ({len(calls)} calls)\n")
                for call in calls[:10]:  # Top 10 per type
                    md_lines.append(f"- **Source:** `{call.get('source_function', 'unknown')}` "
                                  f"in `{call.get('source_file', 'unknown')}`")
                    if call.get('endpoint'):
                        md_lines.append(f"  - **Endpoint:** `{call['endpoint']}`")
                    if call.get('method'):
                        md_lines.append(f"  - **Method:** `{call['method']}`")
                    if call.get('target_service'):
                        md_lines.append(f"  - **Target Service:** `{call['target_service']}`")
                md_lines.append("")

        return "\n".join(md_lines)

    def _format_context(self, context: Any) -> str:
        """Format context for LLM prompt."""
        if not context or not hasattr(context, 'items'):
            return "No context available"

        lines = []
        for i, item in enumerate(context.items[:5], 1):
            lines.append(f"\n### Context {i}:")
            lines.append(f"File: {item.citation}")
            lines.append(f"```\n{item.content[:300]}...\n```")

        return "\n".join(lines)


# Singleton instance
_generator: Optional[DocumentationGenerator] = None


def get_documentation_generator() -> DocumentationGenerator:
    """Get or create documentation generator instance."""
    global _generator

    if _generator is None:
        _generator = DocumentationGenerator()

    return _generator
