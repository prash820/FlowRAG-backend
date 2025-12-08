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
    get_data_flow_extractor,
)
from config.feature_flags import get_feature_flags

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

        # Extract data flow relationships for supported languages
        data_flow_relationships = 0
        flags = get_feature_flags()
        if flags.enable_data_flow_relationships and language in ['typescript', 'javascript', 'ts', 'js']:
            try:
                code_content = file_path.read_text(encoding='utf-8')
                data_flow_extractor = get_data_flow_extractor(
                    use_ast=flags.enable_typescript_ast
                )
                flow_result = data_flow_extractor.extract_from_code(
                    code=code_content,
                    file_path=str(file_path),
                    namespace=request.namespace,
                    language=language
                )
                if flow_result.get("data_flows") or flow_result.get("waves"):
                    df_stats = neo4j_loader.load_data_flows(
                        data_flows=flow_result.get("data_flows", []),
                        waves=flow_result.get("waves", []),
                        namespace=request.namespace,
                        source_file=str(file_path)
                    )
                    data_flow_relationships = df_stats.get("data_flows_created", 0) + df_stats.get("waves_created", 0)
            except Exception as e:
                logger.warning(f"Data flow extraction failed: {e}")

        processing_time = time.time() - start_time

        return IngestResponse(
            success=True,
            message=f"Successfully ingested {file_path.name}",
            namespace=request.namespace,
            files_processed=1,
            nodes_created=neo4j_stats.get("nodes_created", 0),
            relationships_created=neo4j_stats.get("relationships_created", 0) + data_flow_relationships,
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

                # Extract data flow relationships for supported languages
                flags = get_feature_flags()
                if flags.enable_data_flow_relationships and language in ['typescript', 'javascript', 'ts', 'js']:
                    try:
                        # Read the file content for data flow analysis
                        code_content = file_path.read_text(encoding='utf-8')

                        # Get the data flow extractor
                        data_flow_extractor = get_data_flow_extractor(
                            use_ast=flags.enable_typescript_ast
                        )

                        # Extract data flows
                        flow_result = data_flow_extractor.extract_from_code(
                            code=code_content,
                            file_path=str(file_path),
                            namespace=request.namespace,
                            language=language
                        )

                        # Load data flows into Neo4j
                        if flow_result.get("data_flows") or flow_result.get("waves"):
                            df_stats = neo4j_loader.load_data_flows(
                                data_flows=flow_result.get("data_flows", []),
                                waves=flow_result.get("waves", []),
                                namespace=request.namespace,
                                source_file=str(file_path)
                            )
                            total_relationships += df_stats.get("data_flows_created", 0)
                            total_relationships += df_stats.get("waves_created", 0)

                            if df_stats.get("data_flows_created", 0) > 0:
                                logger.info(f"Created {df_stats['data_flows_created']} data flow relationships for {file_path.name}")
                    except Exception as e:
                        logger.warning(f"Data flow extraction failed for {file_path.name}: {e}")

            except Exception as e:
                error_msg = f"Error processing {file_path.name}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Semantic enrichment if requested
        if request.semantic_enrichment and total_nodes > 0:
            try:
                logger.info(f"Running semantic enrichment for namespace: {request.namespace}")
                from ingestion.enrichment import get_semantic_enricher
                from databases import get_neo4j_client
                from databases.neo4j import NodeLabel
                from ingestion.parsers.base import CodeUnit

                enricher = get_semantic_enricher()
                neo4j = get_neo4j_client()

                # Get enrichment options
                opts = request.enrichment_options or {}
                max_units = opts.get("max_code_units", 100)
                include_glossary = opts.get("include_glossary", True)
                include_service_doc = opts.get("include_service_doc", True)

                # Fetch code units from Neo4j for enrichment
                query = """
                MATCH (n)
                WHERE n.namespace = $namespace
                  AND (n:Function OR n:Method OR n:Class)
                  AND n.code IS NOT NULL
                RETURN n.id as id, n.name as name, labels(n)[0] as type,
                       n.file_path as file_path, n.language as language,
                       n.code as code, n.signature as signature,
                       n.docstring as docstring, n.line_start as line_start,
                       n.line_end as line_end, n.parameters as parameters,
                       n.decorators as decorators, n.calls as calls,
                       n.imports as imports
                LIMIT $limit
                """
                results = neo4j.execute_query(
                    query, {"namespace": request.namespace, "limit": max_units}
                )

                # Convert to CodeUnit objects
                type_map = {
                    "Function": NodeLabel.FUNCTION,
                    "Method": NodeLabel.METHOD,
                    "Class": NodeLabel.CLASS,
                }
                code_units = []
                for r in results:
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
                        namespace=request.namespace,
                    ))

                if code_units:
                    # Enrich code units with semantic summaries
                    logger.info(f"Enriching {len(code_units)} code units with semantic summaries...")
                    enriched_units = enricher.enrich_batch(
                        code_units,
                        progress_callback=lambda i, t, n: logger.info(f"  Enriched [{i}/{t}] {n}")
                    )

                    # Update Qdrant with enriched embeddings (upsert will update existing)
                    enrich_result = qdrant_loader.load_enriched_code_units(
                        enriched_units, request.namespace
                    )
                    enriched_vectors = enrich_result.get("vectors_stored", 0)
                    logger.info(f"Updated {enriched_vectors} vectors with semantic enrichment")

                    # Generate service documentation
                    if include_service_doc:
                        logger.info("Generating service-level documentation...")
                        service_doc = enricher.generate_service_documentation(
                            request.namespace, code_units
                        )
                        doc_result = qdrant_loader.load_service_documentation(
                            service_doc, request.namespace
                        )
                        total_vectors += doc_result.get("vectors_stored", 0)

                    # Extract glossary terms
                    if include_glossary:
                        logger.info("Extracting glossary terms...")
                        terms = enricher.extract_glossary_terms(
                            request.namespace, code_units
                        )
                        if terms:
                            glossary_result = qdrant_loader.load_glossary_terms(
                                terms, request.namespace
                            )
                            total_vectors += glossary_result.get("vectors_stored", 0)
                            logger.info(f"Extracted {len(terms)} glossary terms")

            except Exception as e:
                logger.warning(f"Semantic enrichment failed: {e}")
                errors.append(f"Semantic enrichment failed: {str(e)}")

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
                    generate_documentation=request.generate_documentation,
                    semantic_enrichment=request.semantic_enrichment,
                    enrichment_options=request.enrichment_options,
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
                from ingestion.loaders import get_neo4j_loader
                detector = get_inter_service_detector()
                neo4j_loader = get_neo4j_loader()

                # Build URL to namespace mapping from the workflow services
                url_to_namespace_map = {}
                for service_def in request.services:
                    # Extract service name from directory path for mapping
                    dir_name = Path(service_def.directory_path).name.lower()
                    url_to_namespace_map[dir_name] = service_def.namespace
                    # Also add common variations
                    url_to_namespace_map[dir_name.replace("-", "")] = service_def.namespace
                    url_to_namespace_map[dir_name.replace("_", "")] = service_def.namespace

                for service_result in service_results:
                    if service_result.success:
                        service_calls = detector.detect_service_calls(service_result.namespace)
                        service_result.service_calls_detected = len(service_calls)
                        total_service_calls += len(service_calls)

                        # Actually persist the detected API calls as CALLS_API relationships
                        if service_calls:
                            try:
                                api_call_stats = neo4j_loader.load_api_calls(
                                    api_calls=service_calls,
                                    source_namespace=service_result.namespace,
                                    url_to_namespace_map=url_to_namespace_map,
                                )
                                total_relationships += api_call_stats.get("api_calls_created", 0)
                                logger.info(
                                    f"Persisted {api_call_stats.get('api_calls_created', 0)} "
                                    f"CALLS_API relationships for {service_result.namespace}"
                                )
                            except Exception as e:
                                logger.warning(f"Failed to persist API calls for {service_result.namespace}: {e}")
                                workflow_errors.append(f"API call persistence failed for {service_result.namespace}: {str(e)}")

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


@router.get("/namespaces")
async def list_namespaces():
    """
    List all namespaces with their statistics.
    """
    try:
        neo4j_loader = get_neo4j_loader()

        result = neo4j_loader.client.execute_query(
            """
            MATCH (n)
            WHERE n.namespace IS NOT NULL
            WITH DISTINCT n.namespace AS namespace
            OPTIONAL MATCH (node {namespace: namespace})
            WITH namespace, count(node) AS total_nodes
            RETURN namespace, total_nodes
            ORDER BY namespace
            """
        )

        namespaces = []
        for record in result:
            namespaces.append({
                "name": record["namespace"],
                "source_type": "code",
                "created_at": "2024-01-01T00:00:00Z",
                "stats": {
                    "total_files": 0,
                    "total_nodes": record["total_nodes"] or 0,
                    "total_relationships": 0,
                }
            })

        return namespaces

    except Exception as e:
        logger.error(f"Failed to list namespaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list namespaces: {str(e)}"
        )


@router.delete("/namespaces/{namespace}")
async def delete_namespace_by_name(namespace: str):
    """
    Delete a namespace by name.

    WARNING: This is irreversible!
    """
    logger.warning(f"Deleting namespace: {namespace}")

    try:
        # Delete from Neo4j
        neo4j_loader = get_neo4j_loader()
        neo4j_stats = neo4j_loader.delete_namespace(namespace)

        # Delete from Qdrant
        qdrant_loader = get_qdrant_loader()
        qdrant_stats = qdrant_loader.delete_namespace(namespace)

        return {
            "success": True,
            "message": f"Successfully deleted namespace: {namespace}",
            "namespace": namespace,
            "nodes_deleted": neo4j_stats.get("nodes_deleted", 0),
            "vectors_deleted": qdrant_stats.get("vectors_deleted", 0),
        }

    except Exception as e:
        logger.error(f"Failed to delete namespace {namespace}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}"
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
