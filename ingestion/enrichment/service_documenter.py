"""
Service Documenter - Single LLM call to generate service documentation.

Replaces the per-code-unit enrichment with a single, efficient documentation
generation that gets chunked and embedded into Qdrant.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from databases import get_neo4j_client
from agents.llm import get_llm_client, LLMRequest

logger = logging.getLogger(__name__)


@dataclass
class ServiceSummary:
    """Summary of a service from code analysis."""
    namespace: str
    files: List[str]
    functions: List[str]
    classes: List[str]
    imports: List[str]
    api_routes: List[str]
    external_calls: List[str]


class ServiceDocumenter:
    """
    Generates service documentation with a single LLM call.

    Flow:
    1. Query Neo4j for service structure (no LLM)
    2. Build a comprehensive prompt with all context
    3. Single LLM call to generate markdown documentation
    4. Return documentation for chunking and embedding
    """

    def __init__(self):
        self.neo4j = get_neo4j_client()
        self.llm = get_llm_client()

    def generate_documentation(self, namespace: str) -> Dict[str, Any]:
        """
        Generate documentation for a service with a single LLM call.

        Args:
            namespace: Service namespace to document

        Returns:
            Dict with markdown documentation and metadata
        """
        logger.info(f"Generating documentation for {namespace}")

        # Step 1: Gather all context from Neo4j (no LLM)
        summary = self._gather_service_context(namespace)

        if not summary.files:
            logger.warning(f"No code found for namespace {namespace}")
            return {
                "success": False,
                "namespace": namespace,
                "error": "No code found for this namespace",
                "documentation": "",
            }

        # Step 2: Build prompt with all context
        prompt = self._build_documentation_prompt(summary)

        # Step 3: Single LLM call
        try:
            llm_request = LLMRequest(
                system_prompt=self._get_system_prompt(),
                user_prompt=prompt,
                temperature=0.3,
                max_tokens=4000,  # Allow comprehensive response
                stream=False,
            )

            response = self.llm.generate(llm_request)
            documentation = response.content

            logger.info(f"Generated {len(documentation)} chars of documentation for {namespace}")

            return {
                "success": True,
                "namespace": namespace,
                "documentation": documentation,
                "stats": {
                    "files": len(summary.files),
                    "functions": len(summary.functions),
                    "classes": len(summary.classes),
                    "api_routes": len(summary.api_routes),
                    "external_calls": len(summary.external_calls),
                },
            }

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return basic documentation on failure
            return {
                "success": False,
                "namespace": namespace,
                "error": str(e),
                "documentation": self._generate_fallback_doc(summary),
            }

    def _gather_service_context(self, namespace: str) -> ServiceSummary:
        """Gather all service context from Neo4j."""

        # Get all code units
        query = """
        MATCH (n)
        WHERE n.namespace = $namespace
        RETURN
            n.name as name,
            n.type as type,
            n.file_path as file_path,
            n.code as code,
            n.signature as signature,
            n.imports as imports,
            n.calls as calls
        """

        results = self.neo4j.execute_query(query, {"namespace": namespace})

        files = set()
        functions = []
        classes = []
        all_imports = set()
        api_routes = []
        external_calls = []

        for r in results:
            file_path = r.get("file_path", "")
            name = r.get("name", "")
            node_type = r.get("type", "")
            code = r.get("code", "") or ""
            signature = r.get("signature", "")
            imports = r.get("imports") or []

            if file_path:
                files.add(file_path)

            # Categorize by type
            if node_type in ("function", "Function", "method", "Method"):
                func_info = f"{name}"
                if signature:
                    func_info += f": {signature}"
                functions.append(func_info)

                # Detect API routes
                if any(kw in code.lower() for kw in ["@get", "@post", "@put", "@delete", "router.", "app.get", "app.post"]):
                    api_routes.append(f"{name} in {file_path}")

                # Detect external HTTP calls
                if any(kw in code.lower() for kw in ["fetch(", "axios.", "http.", "requests."]):
                    external_calls.append(f"{name} makes HTTP calls")

            elif node_type in ("class", "Class"):
                classes.append(name)

            # Collect imports
            for imp in imports:
                all_imports.add(imp)

        return ServiceSummary(
            namespace=namespace,
            files=sorted(files),
            functions=functions[:50],  # Limit to top 50
            classes=classes[:20],
            imports=sorted(all_imports)[:30],
            api_routes=api_routes[:20],
            external_calls=external_calls[:10],
        )

    def _get_system_prompt(self) -> str:
        """System prompt for documentation generation."""
        return """You are a technical documentation expert. Generate clear, comprehensive markdown documentation for a software service based on its code structure.

Your documentation should:
1. Start with a clear service overview
2. Describe the architecture and main components
3. Document key APIs/endpoints if present
4. Explain external integrations if present
5. Be specific to THIS codebase, not generic

Use proper markdown formatting with headers, lists, and code blocks where appropriate."""

    def _build_documentation_prompt(self, summary: ServiceSummary) -> str:
        """Build the prompt with all service context."""

        sections = [
            f"# Service: {summary.namespace}\n",
            f"## Files ({len(summary.files)} total)",
            "```",
            "\n".join(summary.files[:30]),  # Show first 30 files
            "```\n",
        ]

        if summary.classes:
            sections.extend([
                f"## Classes ({len(summary.classes)})",
                ", ".join(summary.classes),
                "",
            ])

        if summary.functions:
            sections.extend([
                f"## Functions ({len(summary.functions)})",
                "\n".join(f"- {f}" for f in summary.functions[:30]),
                "",
            ])

        if summary.api_routes:
            sections.extend([
                f"## API Routes Detected ({len(summary.api_routes)})",
                "\n".join(f"- {r}" for r in summary.api_routes),
                "",
            ])

        if summary.external_calls:
            sections.extend([
                f"## External HTTP Calls ({len(summary.external_calls)})",
                "\n".join(f"- {c}" for c in summary.external_calls),
                "",
            ])

        if summary.imports:
            sections.extend([
                f"## Key Imports/Dependencies",
                ", ".join(summary.imports[:20]),
                "",
            ])

        sections.append("""
---
Based on the above code structure, generate comprehensive markdown documentation for this service.
Include:
1. **Overview**: What this service does (be specific based on the code)
2. **Architecture**: Main components and how they work together
3. **Key Features**: Based on the functions and classes found
4. **API Endpoints**: If any routes were detected
5. **External Integrations**: If external calls were detected
6. **Dependencies**: Key external libraries used

Be specific to this codebase. Do not make up features not evidenced by the code.""")

        return "\n".join(sections)

    def _generate_fallback_doc(self, summary: ServiceSummary) -> str:
        """Generate basic documentation when LLM fails."""
        lines = [
            f"# {summary.namespace}\n",
            f"Service with {len(summary.files)} files.\n",
            "## Components\n",
        ]

        if summary.classes:
            lines.append("### Classes")
            lines.extend(f"- {c}" for c in summary.classes[:10])
            lines.append("")

        if summary.functions:
            lines.append("### Functions")
            lines.extend(f"- {f}" for f in summary.functions[:10])
            lines.append("")

        return "\n".join(lines)


# Singleton
_documenter: Optional[ServiceDocumenter] = None


def get_service_documenter() -> ServiceDocumenter:
    """Get service documenter singleton."""
    global _documenter
    if _documenter is None:
        _documenter = ServiceDocumenter()
    return _documenter
