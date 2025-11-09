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
