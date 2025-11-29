"""
Ingestion API endpoints.

API Layer is responsible for this module.
"""

from fastapi import APIRouter, HTTPException, status
from pathlib import Path
import logging
import time
from typing import List

from api.schemas import (
    IngestFileRequest,
    IngestDirectoryRequest,
    IngestResponse,
    DeleteNamespaceRequest,
    DeleteNamespaceResponse,
    IngestWorkflowRequest,
    IngestWorkflowResponse,
    WorkflowIngestResult,
)
from ingestion import (
    get_parser,
    detect_language,
    DocumentChunker,
    get_neo4j_loader,
    get_qdrant_loader,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/file", response_model=IngestResponse)
async def ingest_file(request: IngestFileRequest) -> IngestResponse:
    """
    Ingest a single file.

    Parses code or documents and stores in Neo4j + Qdrant.
    """
    logger.info(f"Ingesting file: {request.file_path} into namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Validate file exists
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {request.file_path}"
            )

        if not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a file: {request.file_path}"
            )

        # Detect language if not provided
        language = request.language
        if not language:
            language = detect_language(str(file_path))
            if not language:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not detect language for file: {request.file_path}"
                )

        # Get parser
        parser = get_parser(language)
        if not parser:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No parser available for language: {language}"
            )

        # Parse file
        logger.debug(f"Parsing {file_path} as {language}")
        parse_result = parser.parse_file(str(file_path), request.namespace)

        # Load into Neo4j
        neo4j_loader = get_neo4j_loader()
        neo4j_stats = neo4j_loader.load_parse_result(parse_result)

        # Load into Qdrant
        qdrant_loader = get_qdrant_loader()
        qdrant_stats = qdrant_loader.load_code_units(
            parse_result.all_units,
            request.namespace
        )

        processing_time = time.time() - start_time

        return IngestResponse(
            success=True,
            message=f"Successfully ingested {file_path.name}",
            namespace=request.namespace,
            files_processed=1,
            nodes_created=neo4j_stats.get("nodes_created", 0),
            relationships_created=neo4j_stats.get("relationships_created", 0),
            vectors_stored=qdrant_stats.get("vectors_stored", 0),
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest file {request.file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/directory", response_model=IngestResponse)
async def ingest_directory(request: IngestDirectoryRequest) -> IngestResponse:
    """
    Ingest all files in a directory.

    Recursively processes files and stores in Neo4j + Qdrant.
    """
    logger.info(f"Ingesting directory: {request.directory_path} into namespace: {request.namespace}")
    start_time = time.time()

    try:
        # Validate directory exists
        dir_path = Path(request.directory_path)
        if not dir_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {request.directory_path}"
            )

        if not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {request.directory_path}"
            )

        # Collect files
        files_to_process: List[Path] = []

        if request.recursive:
            pattern = "**/*"
        else:
            pattern = "*"

        for file_path in dir_path.glob(pattern):
            if not file_path.is_file():
                continue

            # Check exclusions
            if request.exclude_patterns:
                excluded = False
                for exclude_pattern in request.exclude_patterns:
                    if exclude_pattern in str(file_path):
                        excluded = True
                        break
                if excluded:
                    continue

            # Check inclusions
            if request.file_patterns:
                included = False
                for file_pattern in request.file_patterns:
                    if file_path.match(file_pattern):
                        included = True
                        break
                if not included:
                    continue

            files_to_process.append(file_path)

        if not files_to_process:
            return IngestResponse(
                success=True,
                message="No files found to process",
                namespace=request.namespace,
                files_processed=0,
                processing_time=time.time() - start_time,
            )

        # Process files
        total_nodes = 0
        total_relationships = 0
        total_vectors = 0
        errors = []

        neo4j_loader = get_neo4j_loader()
        qdrant_loader = get_qdrant_loader()

        for file_path in files_to_process:
            try:
                # Detect language
                language = detect_language(str(file_path))
                if not language:
                    logger.debug(f"Skipping {file_path} - could not detect language")
                    continue

                # Get parser
                parser = get_parser(language)
                if not parser:
                    logger.debug(f"Skipping {file_path} - no parser for {language}")
                    continue

                # Parse
                parse_result = parser.parse_file(str(file_path), request.namespace)

                # Load into Neo4j
                neo4j_stats = neo4j_loader.load_parse_result(parse_result)
                total_nodes += neo4j_stats.get("nodes_created", 0)
                total_relationships += neo4j_stats.get("relationships_created", 0)

                # Load into Qdrant
                qdrant_stats = qdrant_loader.load_code_units(
                    parse_result.all_units,
                    request.namespace
                )
                total_vectors += qdrant_stats.get("vectors_stored", 0)

                logger.debug(f"Processed {file_path.name}")

            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Generate documentation if requested
        if request.generate_documentation and total_nodes > 0:
            try:
                logger.info(f"Generating documentation for namespace: {request.namespace}")
                from orchestrator.documentation import get_documentation_generator

                doc_generator = get_documentation_generator()

                # Generate comprehensive documentation
                doc_result = await doc_generator.generate(
                    namespace=request.namespace,
                    include_diagrams=True,
                    include_api_docs=True,
                    include_data_models=True,
                    include_architecture=True,
                    max_depth=3
                )

                # Store documentation metadata in Neo4j namespace node
                if doc_result.get("success"):
                    try:
                        documentation_metadata = {
                            "service_name": doc_result.get("service_name", ""),
                            "description": doc_result.get("description", ""),
                            "architecture_summary": doc_result.get("architecture_summary", ""),
                            "responsibilities": doc_result.get("responsibilities", []),
                            "total_components": doc_result.get("total_components", 0),
                            "has_documentation": True,
                        }

                        # Store in Neo4j as namespace metadata
                        neo4j_loader.client.execute_query(
                            """
                            MERGE (ns:Namespace {name: $namespace})
                            SET ns += $metadata
                            SET ns.documentation_generated_at = datetime()
                            """,
                            {
                                "namespace": request.namespace,
                                "metadata": documentation_metadata
                            }
                        )

                        logger.info(f"Documentation metadata stored in Neo4j for namespace: {request.namespace}")

                        # Chunk and store the generated documentation as vectors
                        markdown_doc = doc_result.get("markdown_documentation", "")
                        if markdown_doc:
                            try:
                                logger.info(f"Chunking and storing documentation as vectors...")

                                # Chunk the markdown documentation
                                from ingestion import DocumentChunker
                                chunker = DocumentChunker()

                                doc_chunks = chunker.chunk_text(
                                    text=markdown_doc,
                                    file_path=f"{request.namespace}_documentation.md",
                                    namespace=request.namespace
                                )

                                # Store document chunks in Qdrant
                                if doc_chunks:
                                    chunk_result = qdrant_loader.load_document_chunks(
                                        chunks=doc_chunks,
                                        namespace=request.namespace
                                    )

                                    doc_vectors_stored = chunk_result.get("vectors_stored", 0)
                                    logger.info(f"Stored {doc_vectors_stored} documentation chunk vectors in Qdrant")
                                    total_vectors += doc_vectors_stored
                                else:
                                    logger.warning("No documentation chunks generated")

                            except Exception as e:
                                logger.warning(f"Failed to chunk/store documentation: {e}")
                                errors.append(f"Documentation chunking failed: {str(e)}")

                        # Also enrich with high-level summary vector
                        try:
                            enrich_result = qdrant_loader.enrich_with_documentation(
                                namespace=request.namespace,
                                documentation_metadata=documentation_metadata
                            )

                            if enrich_result.get("enriched"):
                                logger.info(f"Qdrant vectors enriched with documentation summary for namespace: {request.namespace}")
                                total_vectors += 1  # Count the summary vector
                            else:
                                logger.warning(f"Qdrant enrichment failed: {enrich_result.get('error', 'Unknown error')}")
                                errors.append(f"Qdrant enrichment failed: {enrich_result.get('error', 'Unknown error')}")

                        except Exception as e:
                            logger.warning(f"Failed to enrich Qdrant with documentation: {e}")
                            errors.append(f"Qdrant enrichment failed: {str(e)}")

                    except Exception as e:
                        logger.warning(f"Failed to store documentation metadata: {e}")
                        errors.append(f"Documentation metadata storage failed: {str(e)}")

            except Exception as e:
                logger.warning(f"Documentation generation failed: {e}")
                errors.append(f"Documentation generation failed: {str(e)}")

        processing_time = time.time() - start_time

        return IngestResponse(
            success=True,
            message=f"Processed {len(files_to_process)} files from {dir_path.name}",
            namespace=request.namespace,
            files_processed=len(files_to_process),
            nodes_created=total_nodes,
            relationships_created=total_relationships,
            vectors_stored=total_vectors,
            processing_time=processing_time,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest directory {request.directory_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/workflow", response_model=IngestWorkflowResponse)
async def ingest_workflow(request: IngestWorkflowRequest) -> IngestWorkflowResponse:
    """
    Ingest multiple services as a coordinated workflow.

    This endpoint orchestrates the ingestion of multiple services, generates
    documentation for each, and detects inter-service calls for comprehensive
    workflow documentation.
    """
    logger.info(f"Ingesting workflow: {request.workflow_name} with {len(request.services)} services")
    start_time = time.time()

    service_results = []
    total_files = 0
    total_nodes = 0
    total_relationships = 0
    total_vectors = 0
    total_service_calls = 0
    workflow_errors = []

    try:
        # Ingest each service
        for service_def in request.services:
            logger.info(f"Ingesting service: {service_def.namespace}")

            try:
                # Create directory request
                dir_request = IngestDirectoryRequest(
                    directory_path=service_def.directory_path,
                    namespace=service_def.namespace,
                    recursive=request.recursive,
                    file_patterns=service_def.file_patterns,
                    exclude_patterns=service_def.exclude_patterns,
                    overwrite=request.overwrite,
                    generate_documentation=request.generate_documentation
                )

                # Ingest directory
                result = await ingest_directory(dir_request)

                # Create service result
                service_result = WorkflowIngestResult(
                    namespace=service_def.namespace,
                    success=result.success,
                    files_processed=result.files_processed,
                    nodes_created=result.nodes_created,
                    relationships_created=result.relationships_created,
                    vectors_stored=result.vectors_stored,
                    service_calls_detected=0,  # Will be updated below
                    documentation_generated=request.generate_documentation,
                    errors=result.errors
                )

                service_results.append(service_result)

                # Update totals
                total_files += result.files_processed
                total_nodes += result.nodes_created
                total_relationships += result.relationships_created
                total_vectors += result.vectors_stored

            except Exception as e:
                error_msg = f"Failed to ingest service {service_def.namespace}: {str(e)}"
                logger.error(error_msg)
                workflow_errors.append(error_msg)

                service_results.append(WorkflowIngestResult(
                    namespace=service_def.namespace,
                    success=False,
                    files_processed=0,
                    nodes_created=0,
                    relationships_created=0,
                    vectors_stored=0,
                    errors=[error_msg]
                ))

        # Detect inter-service calls if requested
        if request.detect_inter_service_calls:
            try:
                from orchestrator.documentation import get_inter_service_detector
                detector = get_inter_service_detector()

                for service_result in service_results:
                    if service_result.success:
                        service_calls = detector.detect_service_calls(service_result.namespace)
                        service_result.service_calls_detected = len(service_calls)
                        total_service_calls += len(service_calls)

            except Exception as e:
                logger.warning(f"Failed to detect inter-service calls: {e}")
                workflow_errors.append(f"Inter-service call detection failed: {str(e)}")

        # Create workflow metadata node in Neo4j
        try:
            neo4j_loader = get_neo4j_loader()
            workflow_metadata = {
                "workflow_name": request.workflow_name,
                "services": [s.namespace for s in request.services],
                "total_services": len(request.services),
                "has_documentation": request.generate_documentation,
                "has_inter_service_detection": request.detect_inter_service_calls,
            }

            neo4j_loader.client.execute_query(
                """
                MERGE (wf:Workflow {name: $workflow_name})
                SET wf += $metadata
                SET wf.created_at = datetime()

                WITH wf
                UNWIND $namespaces AS namespace
                MATCH (ns:Namespace {name: namespace})
                MERGE (wf)-[:CONTAINS_SERVICE]->(ns)
                """,
                {
                    "workflow_name": request.workflow_name,
                    "metadata": workflow_metadata,
                    "namespaces": [s.namespace for s in request.services]
                }
            )

            logger.info(f"Created workflow metadata node for: {request.workflow_name}")
        except Exception as e:
            logger.warning(f"Failed to create workflow metadata: {e}")
            workflow_errors.append(f"Workflow metadata creation failed: {str(e)}")

        processing_time = time.time() - start_time

        return IngestWorkflowResponse(
            success=len([r for r in service_results if r.success]) > 0,
            message=f"Workflow '{request.workflow_name}' processed {len(service_results)} services",
            workflow_name=request.workflow_name,
            services_processed=len(service_results),
            total_files_processed=total_files,
            total_nodes_created=total_nodes,
            total_relationships_created=total_relationships,
            total_vectors_stored=total_vectors,
            total_service_calls_detected=total_service_calls,
            processing_time=processing_time,
            service_results=service_results,
            errors=workflow_errors
        )

    except Exception as e:
        logger.error(f"Workflow ingestion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow ingestion failed: {str(e)}"
        )


@router.delete("/namespace", response_model=DeleteNamespaceResponse)
async def delete_namespace(request: DeleteNamespaceRequest) -> DeleteNamespaceResponse:
    """
    Delete all data for a namespace.

    WARNING: This is irreversible!
    """
    logger.warning(f"Deleting namespace: {request.namespace}")

    try:
        # Delete from Neo4j
        neo4j_loader = get_neo4j_loader()
        neo4j_stats = neo4j_loader.delete_namespace(request.namespace)

        # Delete from Qdrant
        qdrant_loader = get_qdrant_loader()
        qdrant_stats = qdrant_loader.delete_namespace(request.namespace)

        return DeleteNamespaceResponse(
            success=True,
            message=f"Successfully deleted namespace: {request.namespace}",
            namespace=request.namespace,
            nodes_deleted=neo4j_stats.get("nodes_deleted", 0),
            vectors_deleted=qdrant_stats.get("vectors_deleted", 0),
        )

    except Exception as e:
        logger.error(f"Failed to delete namespace {request.namespace}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
        )
