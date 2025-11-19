"""
Ingest Sock Shop microservices into FlowRAG
Demonstrates code ingestion for a real microservices architecture
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import get_parser, detect_language, get_neo4j_loader, get_qdrant_loader
from config import get_settings
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sock Shop services directory
SOCK_SHOP_ROOT = Path.home() / "Documents/workspace/sock-shop-services"
NAMESPACE = "sock_shop"

# Service configuration
SERVICES = {
    "front-end": {
        "path": "front-end",
        "language": "javascript",
        "patterns": ["*.js", "*.jsx"],
        "exclude": ["node_modules", "test", "tests", "dist", "build"]
    },
    "payment": {
        "path": "payment",
        "language": "go",
        "patterns": ["*.go"],
        "exclude": ["vendor", "test", "cmd/main.go"]  # Skip main for now
    },
    "user": {
        "path": "user",
        "language": "go",
        "patterns": ["*.go"],
        "exclude": ["vendor", "test"]
    },
    "catalogue": {
        "path": "catalogue",
        "language": "go",
        "patterns": ["*.go"],
        "exclude": ["vendor", "test", "cmd/main.go"]
    },
    "carts": {
        "path": "carts",
        "language": "java",
        "patterns": ["*.java"],
        "exclude": ["test", "tests", "target", "build"]
    },
    "orders": {
        "path": "orders",
        "language": "java",
        "patterns": ["*.java"],
        "exclude": ["test", "tests", "target", "build"]
    },
    "shipping": {
        "path": "shipping",
        "language": "java",
        "patterns": ["*.java"],
        "exclude": ["test", "tests", "target", "build"]
    },
}


def collect_files(service_path: Path, patterns: list, exclude: list) -> list:
    """Collect source files for a service."""
    files = []

    for pattern in patterns:
        for file_path in service_path.rglob(pattern):
            # Check if file should be excluded
            excluded = False
            for exclude_pattern in exclude:
                if exclude_pattern in str(file_path):
                    excluded = True
                    break

            if not excluded and file_path.is_file():
                files.append(file_path)

    return files


def ingest_service(service_name: str, config: dict):
    """Ingest a single microservice."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Ingesting service: {service_name}")
    logger.info(f"{'='*80}")

    service_path = SOCK_SHOP_ROOT / config["path"]

    if not service_path.exists():
        logger.error(f"Service path not found: {service_path}")
        return {"error": f"Path not found: {service_path}"}

    # Collect files
    files = collect_files(service_path, config["patterns"], config["exclude"])
    logger.info(f"Found {len(files)} files to process")

    if not files:
        logger.warning(f"No files found for {service_name}")
        return {"files_processed": 0}

    # Get parser
    parser = get_parser(config["language"])
    if not parser:
        logger.error(f"No parser for language: {config['language']}")
        return {"error": f"No parser for {config['language']}"}

    # Get loaders
    neo4j_loader = get_neo4j_loader()
    qdrant_loader = get_qdrant_loader()

    # Process files
    total_units = 0
    total_nodes = 0
    total_relationships = 0
    total_vectors = 0
    errors = []

    for i, file_path in enumerate(files, 1):
        try:
            logger.info(f"  [{i}/{len(files)}] Processing {file_path.name}...")

            # Parse file
            parse_result = parser.parse_file(
                str(file_path),
                namespace=f"{NAMESPACE}:{service_name}"
            )

            total_units += parse_result.unit_count

            # Load into Neo4j
            neo4j_stats = neo4j_loader.load_parse_result(parse_result)
            total_nodes += neo4j_stats.get("nodes_created", 0)
            total_relationships += neo4j_stats.get("relationships_created", 0)

            # Load into Qdrant
            if parse_result.all_units:
                qdrant_stats = qdrant_loader.load_code_units(
                    parse_result.all_units,
                    namespace=f"{NAMESPACE}:{service_name}"
                )
                total_vectors += qdrant_stats.get("vectors_stored", 0)

        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {str(e)}"
            logger.error(f"    ❌ {error_msg}")
            errors.append(error_msg)

    return {
        "service": service_name,
        "files_processed": len(files),
        "code_units": total_units,
        "nodes_created": total_nodes,
        "relationships_created": total_relationships,
        "vectors_stored": total_vectors,
        "errors": errors
    }


def main():
    """Ingest all Sock Shop services."""
    logger.info("🚀 Starting Sock Shop ingestion into FlowRAG")
    logger.info(f"   Namespace: {NAMESPACE}")
    logger.info(f"   Services: {len(SERVICES)}")

    start_time = time.time()
    results = []

    # Ingest each service
    for service_name, config in SERVICES.items():
        try:
            result = ingest_service(service_name, config)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to ingest {service_name}: {e}")
            results.append({"service": service_name, "error": str(e)})

    # Summary
    elapsed = time.time() - start_time

    logger.info(f"\n{'='*80}")
    logger.info("📊 INGESTION SUMMARY")
    logger.info(f"{'='*80}")

    total_files = 0
    total_units = 0
    total_nodes = 0
    total_relationships = 0
    total_vectors = 0
    total_errors = 0

    for result in results:
        if "error" in result and "files_processed" not in result:
            logger.info(f"\n❌ {result.get('service', 'Unknown')}: {result['error']}")
            continue

        service = result.get("service", "Unknown")
        files = result.get("files_processed", 0)
        units = result.get("code_units", 0)
        nodes = result.get("nodes_created", 0)
        rels = result.get("relationships_created", 0)
        vectors = result.get("vectors_stored", 0)
        errors = len(result.get("errors", []))

        total_files += files
        total_units += units
        total_nodes += nodes
        total_relationships += rels
        total_vectors += vectors
        total_errors += errors

        logger.info(f"\n✅ {service}:")
        logger.info(f"   Files: {files}")
        logger.info(f"   Code Units: {units}")
        logger.info(f"   Neo4j Nodes: {nodes}")
        logger.info(f"   Relationships: {rels}")
        logger.info(f"   Vectors: {vectors}")
        if errors > 0:
            logger.info(f"   ⚠️  Errors: {errors}")

    logger.info(f"\n{'='*80}")
    logger.info("📈 TOTALS:")
    logger.info(f"   Services: {len(results)}")
    logger.info(f"   Files: {total_files}")
    logger.info(f"   Code Units: {total_units}")
    logger.info(f"   Neo4j Nodes: {total_nodes}")
    logger.info(f"   Relationships: {total_relationships}")
    logger.info(f"   Vectors: {total_vectors}")
    logger.info(f"   Time: {elapsed:.2f}s")
    if total_errors > 0:
        logger.info(f"   ⚠️  Errors: {total_errors}")
    logger.info(f"{'='*80}")

    logger.info("\n✨ Ingestion complete!")
    logger.info("\n💡 Query your microservices:")
    logger.info("   cd flowrag-master")
    logger.info("   source venv/bin/activate")
    logger.info("   unset DEBUG")
    logger.info("   python3 query_sock_shop.py")


if __name__ == "__main__":
    main()
