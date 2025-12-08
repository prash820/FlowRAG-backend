"""
Semantic Enrichment API endpoints.

Provides endpoints for enriching namespaces with semantic metadata:
- Code unit summaries and purpose descriptions
- Service-level documentation
- Glossary terms and domain vocabulary

API Layer is responsible for this module.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import time

from databases import get_neo4j_client
from ingestion.loaders import get_qdrant_loader
from ingestion.enrichment import (
    get_semantic_enricher,
    get_service_documenter,
    EnrichedCodeUnit,
    ServiceDocumentation,
    GlossaryTerm,
)
from ingestion import DocumentChunker
from ingestion.parsers.base import CodeUnit
from databases.neo4j import NodeLabel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


# Request/Response schemas
class EnrichNamespaceRequest(BaseModel):
    """Request to enrich a namespace."""

    namespace: str = Field(..., description="Namespace to enrich")
    include_code_summaries: bool = Field(
        default=True,
        description="Generate semantic summaries for code units"
    )
    include_service_doc: bool = Field(
        default=True,
        description="Generate service-level documentation"
    )
    include_glossary: bool = Field(
        default=True,
        description="Extract glossary terms"
    )
    max_code_units: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum code units to enrich (for cost control)"
    )


class EnrichmentProgress(BaseModel):
    """Enrichment progress update."""

    namespace: str
    status: str  # pending, in_progress, completed, failed
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_step: str = ""
    code_units_enriched: int = 0
    total_code_units: int = 0
    error: Optional[str] = None


class EnrichmentResult(BaseModel):
    """Result of enrichment operation."""

    success: bool
    namespace: str
    code_units_enriched: int = 0
    service_documentation_created: bool = False
    glossary_terms_extracted: int = 0
    total_vectors_stored: int = 0
    enrichment_time: float = 0.0
    error: Optional[str] = None


class ServiceDocResponse(BaseModel):
    """Service documentation response."""

    namespace: str
    service_name: str
    description: str
    purpose: str
    key_features: List[str]
    main_components: List[str]
    external_dependencies: List[str]
    api_patterns: List[str]


class GlossaryResponse(BaseModel):
    """Glossary extraction response."""

    namespace: str
    terms: List[Dict[str, Any]]
    total_terms: int


# In-memory progress tracking (for simplicity)
_enrichment_progress: Dict[str, EnrichmentProgress] = {}


@router.post("/namespace", response_model=EnrichmentResult)
async def enrich_namespace(request: EnrichNamespaceRequest) -> EnrichmentResult:
    """
    Enrich a namespace with semantic metadata.

    This endpoint:
    1. Fetches code units from Neo4j
    2. Generates semantic summaries using LLM
    3. Creates service-level documentation
    4. Extracts glossary terms
    5. Stores enriched embeddings in Qdrant

    Note: This is a synchronous operation. For large namespaces,
    consider using the async endpoint with background processing.
    """
    logger.info(f"Enriching namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Initialize services
        neo4j = get_neo4j_client()
        qdrant_loader = get_qdrant_loader()
        enricher = get_semantic_enricher()

        # Fetch code units from Neo4j
        code_units = _fetch_code_units(neo4j, request.namespace, request.max_code_units)

        if not code_units:
            return EnrichmentResult(
                success=True,
                namespace=request.namespace,
                code_units_enriched=0,
                enrichment_time=time.time() - start_time,
            )

        total_vectors = 0

        # Phase 1: Enrich code units with summaries
        if request.include_code_summaries:
            logger.info(f"Enriching {len(code_units)} code units...")

            enriched_units = enricher.enrich_batch(
                code_units,
                progress_callback=lambda i, t, n: logger.info(f"  [{i}/{t}] {n}")
            )

            # Store enriched embeddings
            result = qdrant_loader.load_enriched_code_units(
                enriched_units,
                request.namespace
            )
            total_vectors += result.get("vectors_stored", 0)

        # Phase 2: Generate service documentation
        service_doc_created = False
        if request.include_service_doc:
            logger.info("Generating service documentation...")

            service_doc = enricher.generate_service_documentation(
                request.namespace,
                code_units
            )

            result = qdrant_loader.load_service_documentation(
                service_doc,
                request.namespace
            )
            total_vectors += result.get("vectors_stored", 0)
            service_doc_created = True

        # Phase 3: Extract glossary terms
        glossary_count = 0
        if request.include_glossary:
            logger.info("Extracting glossary terms...")

            terms = enricher.extract_glossary_terms(
                request.namespace,
                code_units
            )

            if terms:
                result = qdrant_loader.load_glossary_terms(
                    terms,
                    request.namespace
                )
                total_vectors += result.get("vectors_stored", 0)
                glossary_count = len(terms)

        enrichment_time = time.time() - start_time

        logger.info(
            f"Enrichment completed for {request.namespace}: "
            f"{len(code_units)} code units, {total_vectors} vectors, "
            f"{enrichment_time:.2f}s"
        )

        return EnrichmentResult(
            success=True,
            namespace=request.namespace,
            code_units_enriched=len(code_units) if request.include_code_summaries else 0,
            service_documentation_created=service_doc_created,
            glossary_terms_extracted=glossary_count,
            total_vectors_stored=total_vectors,
            enrichment_time=enrichment_time,
        )

    except Exception as e:
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment failed: {str(e)}"
        )


@router.post("/namespace/async")
async def enrich_namespace_async(
    request: EnrichNamespaceRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """
    Start async enrichment of a namespace.

    Returns immediately with a task ID. Use /enrichment/status/{namespace}
    to check progress.
    """
    # Initialize progress tracking
    _enrichment_progress[request.namespace] = EnrichmentProgress(
        namespace=request.namespace,
        status="pending",
        progress=0.0,
        current_step="Queued for processing",
    )

    # Add to background tasks
    background_tasks.add_task(
        _run_enrichment_background,
        request
    )

    return {
        "status": "accepted",
        "namespace": request.namespace,
        "message": "Enrichment started. Check /enrichment/status/{namespace} for progress."
    }


@router.get("/status/{namespace}", response_model=EnrichmentProgress)
async def get_enrichment_status(namespace: str) -> EnrichmentProgress:
    """Get the status of an ongoing or completed enrichment."""
    if namespace not in _enrichment_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No enrichment task found for namespace: {namespace}"
        )

    return _enrichment_progress[namespace]


@router.post("/service-doc/{namespace}", response_model=ServiceDocResponse)
async def generate_service_documentation(namespace: str) -> ServiceDocResponse:
    """
    Generate service-level documentation for a namespace.

    This creates a high-level overview of the service based on its code.
    """
    try:
        neo4j = get_neo4j_client()
        enricher = get_semantic_enricher()
        qdrant_loader = get_qdrant_loader()

        # Fetch code units
        code_units = _fetch_code_units(neo4j, namespace, max_units=50)

        if not code_units:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No code units found for namespace: {namespace}"
            )

        # Generate documentation
        service_doc = enricher.generate_service_documentation(namespace, code_units)

        # Store in Qdrant
        qdrant_loader.load_service_documentation(service_doc, namespace)

        return ServiceDocResponse(
            namespace=namespace,
            service_name=service_doc.service_name,
            description=service_doc.description,
            purpose=service_doc.purpose,
            key_features=service_doc.key_features,
            main_components=service_doc.main_components,
            external_dependencies=service_doc.external_dependencies,
            api_patterns=service_doc.api_patterns,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service doc generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/glossary/{namespace}", response_model=GlossaryResponse)
async def extract_glossary(namespace: str) -> GlossaryResponse:
    """
    Extract domain terms and glossary from a namespace.

    Returns acronyms, domain-specific terms, and their definitions.
    """
    try:
        neo4j = get_neo4j_client()
        enricher = get_semantic_enricher()
        qdrant_loader = get_qdrant_loader()

        # Fetch code units
        code_units = _fetch_code_units(neo4j, namespace, max_units=50)

        if not code_units:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No code units found for namespace: {namespace}"
            )

        # Extract glossary
        terms = enricher.extract_glossary_terms(namespace, code_units)

        # Store in Qdrant
        if terms:
            qdrant_loader.load_glossary_terms(terms, namespace)

        return GlossaryResponse(
            namespace=namespace,
            terms=[
                {
                    "term": t.term,
                    "full_name": t.full_name,
                    "description": t.description,
                    "usage_context": t.usage_context,
                }
                for t in terms
            ],
            total_terms=len(terms),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Glossary extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/namespaces")
async def list_enrichable_namespaces() -> Dict[str, Any]:
    """
    List all namespaces that can be enriched.

    Returns namespace names with their code unit counts.
    """
    try:
        neo4j = get_neo4j_client()

        query = """
        MATCH (n)
        WHERE n.namespace IS NOT NULL
        RETURN n.namespace as namespace, count(n) as count
        ORDER BY count DESC
        """

        results = neo4j.execute_query(query, {})

        return {
            "namespaces": [
                {"namespace": r["namespace"], "code_units": r["count"]}
                for r in results
            ],
            "total": len(results),
        }

    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Helper functions

def _fetch_code_units(
    neo4j,
    namespace: str,
    max_units: int = 100,
) -> List[CodeUnit]:
    """Fetch code units from Neo4j for enrichment."""
    query = """
    MATCH (n)
    WHERE n.namespace = $namespace
      AND (n:Function OR n:Method OR n:Class)
      AND n.code IS NOT NULL
    RETURN n.id as id,
           n.name as name,
           labels(n)[0] as type,
           n.file_path as file_path,
           n.language as language,
           n.code as code,
           n.signature as signature,
           n.docstring as docstring,
           n.line_start as line_start,
           n.line_end as line_end,
           n.parameters as parameters,
           n.decorators as decorators,
           n.calls as calls,
           n.imports as imports
    LIMIT $limit
    """

    results = neo4j.execute_query(
        query,
        {"namespace": namespace, "limit": max_units}
    )

    code_units = []
    for r in results:
        # Map label to NodeLabel enum
        type_map = {
            "Function": NodeLabel.FUNCTION,
            "Method": NodeLabel.METHOD,
            "Class": NodeLabel.CLASS,
        }
        node_type = type_map.get(r.get("type"), NodeLabel.FUNCTION)

        code_units.append(CodeUnit(
            id=r.get("id", ""),
            name=r.get("name", "unknown"),
            type=node_type,
            file_path=r.get("file_path", ""),
            language=r.get("language", "unknown"),
            code=r.get("code", ""),
            signature=r.get("signature"),
            docstring=r.get("docstring"),
            line_start=r.get("line_start", 0),
            line_end=r.get("line_end", 0),
            parameters=r.get("parameters") or [],
            decorators=r.get("decorators") or [],
            calls=r.get("calls") or [],
            imports=r.get("imports") or [],
            namespace=namespace,
        ))

    return code_units


async def _run_enrichment_background(request: EnrichNamespaceRequest):
    """Run enrichment in background."""
    namespace = request.namespace

    try:
        _enrichment_progress[namespace].status = "in_progress"
        _enrichment_progress[namespace].current_step = "Fetching code units"

        # Initialize services
        neo4j = get_neo4j_client()
        qdrant_loader = get_qdrant_loader()
        enricher = get_semantic_enricher()

        # Fetch code units
        code_units = _fetch_code_units(neo4j, namespace, request.max_code_units)
        _enrichment_progress[namespace].total_code_units = len(code_units)

        if not code_units:
            _enrichment_progress[namespace].status = "completed"
            _enrichment_progress[namespace].progress = 1.0
            _enrichment_progress[namespace].current_step = "No code units found"
            return

        total_vectors = 0

        # Phase 1: Enrich code units
        if request.include_code_summaries:
            _enrichment_progress[namespace].current_step = "Enriching code units"

            def progress_callback(i, total, name):
                _enrichment_progress[namespace].code_units_enriched = i
                _enrichment_progress[namespace].progress = i / total * 0.7

            enriched_units = enricher.enrich_batch(code_units, progress_callback)

            _enrichment_progress[namespace].current_step = "Storing embeddings"
            result = qdrant_loader.load_enriched_code_units(enriched_units, namespace)
            total_vectors += result.get("vectors_stored", 0)

        # Phase 2: Service documentation
        if request.include_service_doc:
            _enrichment_progress[namespace].current_step = "Generating service docs"
            _enrichment_progress[namespace].progress = 0.8

            service_doc = enricher.generate_service_documentation(namespace, code_units)
            result = qdrant_loader.load_service_documentation(service_doc, namespace)
            total_vectors += result.get("vectors_stored", 0)

        # Phase 3: Glossary
        if request.include_glossary:
            _enrichment_progress[namespace].current_step = "Extracting glossary"
            _enrichment_progress[namespace].progress = 0.9

            terms = enricher.extract_glossary_terms(namespace, code_units)
            if terms:
                result = qdrant_loader.load_glossary_terms(terms, namespace)
                total_vectors += result.get("vectors_stored", 0)

        # Complete
        _enrichment_progress[namespace].status = "completed"
        _enrichment_progress[namespace].progress = 1.0
        _enrichment_progress[namespace].current_step = f"Completed: {total_vectors} vectors stored"

    except Exception as e:
        logger.error(f"Background enrichment failed: {e}", exc_info=True)
        _enrichment_progress[namespace].status = "failed"
        _enrichment_progress[namespace].error = str(e)
        _enrichment_progress[namespace].current_step = "Failed"


# =============================================================================
# New: Single LLM Call Documentation (Recommended)
# =============================================================================

class DocumentNamespaceRequest(BaseModel):
    """Request to generate documentation for a namespace."""

    namespace: str = Field(..., description="Namespace to document")
    chunk_and_embed: bool = Field(
        default=True,
        description="Chunk the documentation and store in Qdrant"
    )


class DocumentNamespaceResponse(BaseModel):
    """Response from documentation generation."""

    success: bool
    namespace: str
    documentation: str = ""
    chunks_stored: int = 0
    stats: Dict[str, int] = {}
    error: Optional[str] = None


@router.post("/document/{namespace}", response_model=DocumentNamespaceResponse)
async def document_namespace(namespace: str, chunk_and_embed: bool = True) -> DocumentNamespaceResponse:
    """
    Generate documentation for a namespace with a SINGLE LLM call.

    This is the recommended approach - much more efficient than per-unit enrichment.

    Flow:
    1. Query Neo4j for service structure (no LLM)
    2. Single LLM call to generate markdown documentation
    3. Optionally chunk and embed into Qdrant

    Args:
        namespace: Service namespace to document
        chunk_and_embed: Whether to store chunks in Qdrant (default: True)
    """
    logger.info(f"Generating documentation for namespace: {namespace}")
    start_time = time.time()

    try:
        documenter = get_service_documenter()
        result = documenter.generate_documentation(namespace)

        if not result["success"]:
            return DocumentNamespaceResponse(
                success=False,
                namespace=namespace,
                error=result.get("error", "Documentation generation failed"),
            )

        documentation = result["documentation"]
        chunks_stored = 0

        # Optionally chunk and embed
        if chunk_and_embed and documentation:
            try:
                chunker = DocumentChunker()
                qdrant_loader = get_qdrant_loader()

                # Chunk the documentation
                chunks = chunker.chunk_text(
                    text=documentation,
                    file_path=f"{namespace}_documentation.md",
                    namespace=namespace,
                )

                if chunks:
                    # Store in Qdrant
                    store_result = qdrant_loader.load_document_chunks(
                        chunks=chunks,
                        namespace=namespace,
                    )
                    chunks_stored = store_result.get("vectors_stored", 0)
                    logger.info(f"Stored {chunks_stored} documentation chunks for {namespace}")

            except Exception as e:
                logger.warning(f"Failed to chunk/embed documentation: {e}")

        processing_time = time.time() - start_time
        logger.info(f"Documentation generated for {namespace} in {processing_time:.2f}s")

        return DocumentNamespaceResponse(
            success=True,
            namespace=namespace,
            documentation=documentation,
            chunks_stored=chunks_stored,
            stats=result.get("stats", {}),
        )

    except Exception as e:
        logger.error(f"Documentation generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documentation generation failed: {str(e)}"
        )
