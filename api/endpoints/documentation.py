"""
Documentation Generation API endpoints.

Generates comprehensive documentation for ingested services including:
- High-level design overview
- Architecture diagrams (Mermaid)
- Component breakdowns
- API documentation
- Data flow diagrams
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import logging
from typing import Optional, List
from pydantic import BaseModel, Field
from io import BytesIO

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documentation", tags=["documentation"])


# Request schemas
class DocumentationRequest(BaseModel):
    """Request for documentation generation."""

    namespace: str = Field(..., description="Namespace to document")
    include_diagrams: bool = Field(default=True, description="Include Mermaid diagrams")
    include_api_docs: bool = Field(default=True, description="Include API endpoint documentation")
    include_data_models: bool = Field(default=True, description="Include data model documentation")
    include_architecture: bool = Field(default=True, description="Include architecture overview")
    max_depth: int = Field(default=3, ge=1, le=5, description="Analysis depth for components")


# Response schemas
class MermaidDiagram(BaseModel):
    """Mermaid diagram."""

    title: str
    type: str  # flowchart, sequence, class, erd, etc.
    diagram: str  # Mermaid syntax
    description: str


class ComponentDoc(BaseModel):
    """Component documentation."""

    name: str
    type: str  # controller, service, model, utility, etc.
    description: str
    responsibilities: List[str]
    dependencies: List[str]
    file_path: str


class APIEndpointDoc(BaseModel):
    """API endpoint documentation."""

    method: str  # GET, POST, PUT, DELETE, etc.
    path: str
    description: str
    controller: str
    parameters: List[dict]
    responses: List[dict]


class DocumentationResponse(BaseModel):
    """Response from documentation generation."""

    success: bool
    namespace: str

    # Overview
    service_name: str
    description: str
    architecture_summary: str

    # Diagrams
    diagrams: List[MermaidDiagram] = Field(default_factory=list)

    # Components
    components: List[ComponentDoc] = Field(default_factory=list)

    # API Documentation
    api_endpoints: List[APIEndpointDoc] = Field(default_factory=list)

    # Data Models
    data_models: List[dict] = Field(default_factory=list)

    # Generated markdown
    markdown_documentation: str

    # Metadata
    total_files: int
    total_components: int
    generation_time: float
    error: Optional[str] = None


@router.post("", response_model=DocumentationResponse)
async def generate_documentation(request: DocumentationRequest) -> DocumentationResponse:
    """
    Generate comprehensive documentation for an ingested service.

    This endpoint analyzes the codebase structure, generates architecture diagrams,
    documents components, APIs, and data models, and produces a complete
    markdown documentation.

    Workflow:
    1. Analyze codebase structure
    2. Generate architecture overview
    3. Create Mermaid diagrams (architecture, sequence, data flow)
    4. Document components and their relationships
    5. Extract and document API endpoints
    6. Document data models
    7. Generate complete markdown documentation
    """
    logger.info(f"Generating documentation for namespace: {request.namespace}")

    import time
    start_time = time.time()

    try:
        # Import documentation generator
        from orchestrator.documentation import get_documentation_generator

        generator = get_documentation_generator()

        # Generate documentation
        result = await generator.generate(
            namespace=request.namespace,
            include_diagrams=request.include_diagrams,
            include_api_docs=request.include_api_docs,
            include_data_models=request.include_data_models,
            include_architecture=request.include_architecture,
            max_depth=request.max_depth
        )

        # Add generation time
        result["generation_time"] = time.time() - start_time

        return DocumentationResponse(**result)

    except Exception as e:
        logger.error(f"Documentation generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documentation generation failed: {str(e)}"
        )


@router.get("/{namespace}/preview")
async def preview_documentation(namespace: str):
    """
    Get a quick preview of what will be documented.

    Returns a summary of components, APIs, and models found in the namespace
    without generating full documentation.
    """
    logger.info(f"Previewing documentation for namespace: {namespace}")

    try:
        from orchestrator.documentation import get_documentation_generator

        generator = get_documentation_generator()
        preview = await generator.preview(namespace)

        return preview

    except Exception as e:
        logger.error(f"Documentation preview failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documentation preview failed: {str(e)}"
        )


@router.get("/{namespace}/markdown")
async def get_markdown_documentation(namespace: str):
    """
    Get the generated documentation in markdown format.

    Returns the complete documentation as a markdown string that can be
    saved to a README.md or documentation file.
    """
    logger.info(f"Getting markdown documentation for namespace: {namespace}")

    try:
        from orchestrator.documentation import get_documentation_generator

        generator = get_documentation_generator()
        markdown = await generator.get_markdown(namespace)

        return {"namespace": namespace, "markdown": markdown}

    except Exception as e:
        logger.error(f"Markdown generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Markdown generation failed: {str(e)}"
        )


@router.get("/{namespace}/pdf")
async def get_pdf_documentation(namespace: str):
    """
    Generate and download documentation as PDF.

    Returns a PDF file containing the complete documentation including:
    - Cover page with service name and generation date
    - Architecture overview
    - Mermaid diagram placeholders (with syntax)
    - Component documentation
    - API documentation
    - Data model documentation
    - Inter-service call documentation
    """
    logger.info(f"Generating PDF documentation for namespace: {namespace}")

    try:
        from orchestrator.documentation import get_documentation_generator, get_pdf_generator

        # Generate markdown documentation
        doc_generator = get_documentation_generator()
        result = await doc_generator.generate(namespace)

        markdown_content = result.get("markdown_documentation", "")
        service_name = result.get("service_name", namespace)

        if not markdown_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No documentation found for namespace: {namespace}"
            )

        # Convert to PDF
        pdf_generator = get_pdf_generator()
        pdf_stream = pdf_generator.generate_pdf_stream(markdown_content, service_name)

        # Return PDF as downloadable file
        filename = f"{namespace.replace(' ', '_')}_documentation.pdf"

        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {str(e)}"
        )


class GroupDocumentationRequest(BaseModel):
    """Request for generating documentation for multiple namespaces."""

    namespaces: List[str] = Field(..., description="List of namespaces to document")
    group_name: str = Field(..., description="Name for the combined documentation")
    include_diagrams: bool = Field(default=True, description="Include Mermaid diagrams")


def _format_namespace_display(namespace: str) -> str:
    """Convert namespace to human-readable display name."""
    # Replace common separators with spaces and title case
    display = namespace.replace("-", " ").replace("_", " ")
    return display.title()


def _make_mermaid_safe(namespace: str) -> str:
    """Convert namespace to mermaid-safe identifier."""
    return namespace.replace("-", "_").replace(" ", "_").replace(".", "_")


@router.post("/group/pdf")
async def generate_group_pdf_documentation(request: GroupDocumentationRequest):
    """
    Generate business + technical documentation for a service group.

    Creates a PDF document that serves both business and technical stakeholders:
    - Executive summary for leadership
    - System overview with visual diagrams
    - Service descriptions with business purpose
    - Technical architecture details
    """
    logger.info(f"Generating group PDF for namespaces: {request.namespaces}")

    try:
        from databases import get_neo4j_client
        from orchestrator.documentation import get_pdf_generator
        from datetime import datetime

        neo4j_client = get_neo4j_client()
        combined_markdown_parts = []

        # ============================================
        # QUERY NEO4J FOR SERVICE STATS AND DESCRIPTIONS
        # ============================================
        service_stats = {}
        service_descriptions = {}
        total_components = 0

        for namespace in request.namespaces:
            # Get stats
            stats_query = """
            MATCH (n)
            WHERE n.namespace = $namespace
            RETURN
                count(*) as total_nodes,
                count(CASE WHEN n.type = 'Class' THEN 1 END) as classes,
                count(CASE WHEN n.type = 'Function' THEN 1 END) as functions,
                count(CASE WHEN n.type = 'Method' THEN 1 END) as methods
            """
            try:
                results = neo4j_client.execute_query(stats_query, {"namespace": namespace})
                if results:
                    service_stats[namespace] = results[0]
                    total_components += results[0].get("total_nodes", 0)
            except Exception as e:
                logger.warning(f"Failed to get stats for {namespace}: {e}")
                service_stats[namespace] = {"total_nodes": 0, "classes": 0, "functions": 0, "methods": 0}

            # Try to get description from root-level docstrings or README
            desc_query = """
            MATCH (n)
            WHERE n.namespace = $namespace
              AND (n.type = 'Module' OR n.type = 'File' OR n.name CONTAINS 'README')
              AND n.docstring IS NOT NULL
            RETURN n.docstring as description
            LIMIT 1
            """
            try:
                results = neo4j_client.execute_query(desc_query, {"namespace": namespace})
                if results and results[0].get("description"):
                    desc = results[0]["description"]
                    # Truncate long descriptions
                    if len(desc) > 200:
                        desc = desc[:197] + "..."
                    service_descriptions[namespace] = desc
            except Exception:
                pass

        # ============================================
        # QUERY NEO4J FOR CROSS-SERVICE RELATIONSHIPS
        # ============================================
        logger.info("Querying Neo4j for inter-service relationships...")
        namespace_list = request.namespaces

        interactions_query = """
        MATCH (a)-[r:CALLS_API]->(b)
        WHERE a.namespace IN $namespaces AND b.namespace IN $namespaces
          AND a.namespace <> b.namespace
        RETURN
            a.namespace as from_service,
            b.namespace as to_service,
            a.name as caller,
            b.name as callee,
            count(*) as call_count
        ORDER BY from_service, to_service
        """

        service_interactions = []
        interaction_edges = {}

        try:
            results = neo4j_client.execute_query(interactions_query, {"namespaces": namespace_list})
            logger.info(f"Found {len(results)} inter-service relationships")

            for row in results:
                from_svc = row.get("from_service")
                to_svc = row.get("to_service")
                caller = row.get("caller", "unknown")
                callee = row.get("callee", "unknown")
                count = row.get("call_count", 1)

                service_interactions.append({
                    "from": from_svc,
                    "to": to_svc,
                    "caller": caller,
                    "callee": callee,
                    "count": count
                })

                edge_key = (from_svc, to_svc)
                if edge_key not in interaction_edges:
                    interaction_edges[edge_key] = 0
                interaction_edges[edge_key] += count

        except Exception as e:
            logger.error(f"Failed to query inter-service relationships: {e}")

        # ============================================
        # TITLE PAGE
        # ============================================
        combined_markdown_parts.append(f"# {request.group_name}\n\n")
        combined_markdown_parts.append("## System Documentation\n\n")
        combined_markdown_parts.append(f"*Generated on {datetime.now().strftime('%B %d, %Y')}*\n\n")
        combined_markdown_parts.append("---\n\n")

        # ============================================
        # EXECUTIVE SUMMARY
        # ============================================
        combined_markdown_parts.append("## Executive Summary\n\n")
        combined_markdown_parts.append(
            f"The **{request.group_name}** platform is composed of **{len(request.namespaces)} services** "
            f"that work together to deliver the application's functionality. "
            f"This documentation provides an overview of how these services are organized and how they communicate.\n\n"
        )

        # Key metrics
        combined_markdown_parts.append("### Key Metrics\n\n")
        combined_markdown_parts.append(f"- **Total Services:** {len(request.namespaces)}\n")
        combined_markdown_parts.append(f"- **Total Components:** {total_components:,}\n")
        combined_markdown_parts.append(f"- **Service Integrations:** {len(interaction_edges)} connections\n\n")

        # Services list
        combined_markdown_parts.append("### Services\n\n")
        for ns in request.namespaces:
            display_name = _format_namespace_display(ns)
            desc = service_descriptions.get(ns, "")
            if desc:
                combined_markdown_parts.append(f"- **{display_name}:** {desc}\n")
            else:
                combined_markdown_parts.append(f"- **{display_name}**\n")

        combined_markdown_parts.append("\n")

        # ============================================
        # ARCHITECTURE DIAGRAM
        # ============================================
        combined_markdown_parts.append("## Architecture\n\n")
        combined_markdown_parts.append(
            "The diagram below shows how the services are connected. "
            "Arrows indicate which services communicate with each other.\n\n"
        )

        combined_markdown_parts.append("```mermaid\n")
        combined_markdown_parts.append("graph TB\n")
        combined_markdown_parts.append(f"    subgraph System[{request.group_name}]\n")

        # Add service nodes
        for ns in request.namespaces:
            safe_name = _make_mermaid_safe(ns)
            display_name = _format_namespace_display(ns)
            combined_markdown_parts.append(f"        {safe_name}[{display_name}]\n")

        combined_markdown_parts.append("    end\n")

        # Add interaction edges
        if interaction_edges:
            combined_markdown_parts.append("\n")
            for (from_svc, to_svc), count in interaction_edges.items():
                from_safe = _make_mermaid_safe(from_svc)
                to_safe = _make_mermaid_safe(to_svc)
                combined_markdown_parts.append(f"    {from_safe} --> {to_safe}\n")

        combined_markdown_parts.append("```\n\n")

        # ============================================
        # SERVICE COMMUNICATION
        # ============================================
        if interaction_edges:
            combined_markdown_parts.append("## Service Communication\n\n")
            combined_markdown_parts.append(
                "The following table shows which services depend on each other.\n\n"
            )

            combined_markdown_parts.append("| From | To | Calls |\n")
            combined_markdown_parts.append("|------|-----|-------|\n")

            for (from_svc, to_svc), count in sorted(interaction_edges.items()):
                from_display = _format_namespace_display(from_svc)
                to_display = _format_namespace_display(to_svc)
                combined_markdown_parts.append(f"| {from_display} | {to_display} | {count} |\n")

            combined_markdown_parts.append("\n")

            # Sequence diagram
            combined_markdown_parts.append("### Interaction Flow\n\n")
            combined_markdown_parts.append("```mermaid\n")
            combined_markdown_parts.append("sequenceDiagram\n")
            combined_markdown_parts.append("    participant User\n")

            participating_services = set()
            for (from_svc, to_svc) in interaction_edges.keys():
                participating_services.add(from_svc)
                participating_services.add(to_svc)

            for ns in request.namespaces:
                if ns in participating_services:
                    safe_name = _make_mermaid_safe(ns)
                    display_name = _format_namespace_display(ns)
                    combined_markdown_parts.append(f"    participant {safe_name} as {display_name}\n")

            if participating_services:
                first_service = list(participating_services)[0]
                first_safe = _make_mermaid_safe(first_service)
                combined_markdown_parts.append(f"    User->>+{first_safe}: Request\n")

                shown_calls = 0
                for (from_svc, to_svc), count in interaction_edges.items():
                    if shown_calls >= 4:
                        break
                    from_safe = _make_mermaid_safe(from_svc)
                    to_safe = _make_mermaid_safe(to_svc)
                    combined_markdown_parts.append(f"    {from_safe}->>+{to_safe}: Call\n")
                    combined_markdown_parts.append(f"    {to_safe}-->>-{from_safe}: Response\n")
                    shown_calls += 1

                combined_markdown_parts.append(f"    {first_safe}-->>-User: Response\n")

            combined_markdown_parts.append("```\n\n")

        # ============================================
        # SERVICE DETAILS
        # ============================================
        combined_markdown_parts.append("## Service Details\n\n")

        for namespace in request.namespaces:
            display_name = _format_namespace_display(namespace)
            combined_markdown_parts.append(f"### {display_name}\n\n")

            # Description from Neo4j if available
            desc = service_descriptions.get(namespace)
            if desc:
                combined_markdown_parts.append(f"{desc}\n\n")

            stats = service_stats.get(namespace, {})
            classes = stats.get("classes", 0)
            functions = stats.get("functions", 0)
            methods = stats.get("methods", 0)
            total = stats.get("total_nodes", 0)

            combined_markdown_parts.append(f"**Components:** {total} total ({classes} classes, {functions} functions, {methods} methods)\n\n")

            # Dependencies
            outgoing = [(to_svc, cnt) for (from_svc, to_svc), cnt in interaction_edges.items() if from_svc == namespace]
            incoming = [(from_svc, cnt) for (from_svc, to_svc), cnt in interaction_edges.items() if to_svc == namespace]

            if outgoing:
                deps = [_format_namespace_display(to_svc) for to_svc, _ in outgoing]
                combined_markdown_parts.append(f"**Depends on:** {', '.join(deps)}\n\n")

            if incoming:
                callers = [_format_namespace_display(from_svc) for from_svc, _ in incoming]
                combined_markdown_parts.append(f"**Used by:** {', '.join(callers)}\n\n")

            if not outgoing and not incoming:
                combined_markdown_parts.append("**Standalone service**\n\n")

        # ============================================
        # TECHNICAL APPENDIX
        # ============================================
        combined_markdown_parts.append("---\n\n")
        combined_markdown_parts.append("## Technical Appendix\n\n")

        # Component breakdown table
        combined_markdown_parts.append("### Component Breakdown\n\n")
        combined_markdown_parts.append("| Service | Classes | Functions | Methods | Total |\n")
        combined_markdown_parts.append("|---------|---------|-----------|---------|-------|\n")

        for namespace in request.namespaces:
            stats = service_stats.get(namespace, {})
            combined_markdown_parts.append(
                f"| {namespace} | {stats.get('classes', 0)} | {stats.get('functions', 0)} | "
                f"{stats.get('methods', 0)} | {stats.get('total_nodes', 0)} |\n"
            )

        combined_markdown_parts.append("\n")

        # API integration details
        if service_interactions:
            combined_markdown_parts.append("### API Integration Points\n\n")

            by_source = {}
            for interaction in service_interactions:
                from_svc = interaction["from"]
                if from_svc not in by_source:
                    by_source[from_svc] = []
                by_source[from_svc].append(interaction)

            for source_svc, calls in by_source.items():
                combined_markdown_parts.append(f"**{source_svc}:**\n\n")
                for call in calls[:5]:
                    combined_markdown_parts.append(
                        f"- {call['caller']} -> {call['to']}.{call['callee']}\n"
                    )
                if len(calls) > 5:
                    combined_markdown_parts.append(f"- ... and {len(calls) - 5} more\n")
                combined_markdown_parts.append("\n")

        # ============================================
        # GENERATE PDF
        # ============================================
        combined_markdown = "".join(combined_markdown_parts)

        pdf_generator = get_pdf_generator()
        pdf_stream = pdf_generator.generate_pdf_stream(combined_markdown, request.group_name)

        filename = f"{request.group_name.replace(' ', '_')}_documentation.pdf"

        return StreamingResponse(
            pdf_stream,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/pdf"
            }
        )

    except Exception as e:
        logger.error(f"Group PDF generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Group PDF generation failed: {str(e)}"
        )
