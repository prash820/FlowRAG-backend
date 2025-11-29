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
import logging
from typing import Optional, List
from pydantic import BaseModel, Field

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
