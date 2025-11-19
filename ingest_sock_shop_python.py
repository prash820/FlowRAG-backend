"""
Ingest Sock Shop Python files (test utilities) into FlowRAG
Focuses on Python files since JavaScript/Go parsers have issues
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import get_parser, get_neo4j_loader, get_qdrant_loader
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SOCK_SHOP_ROOT = Path.home() / "Documents/workspace/sock-shop-services"
NAMESPACE = "sock_shop"


def main():
    """Ingest all Python files from Sock Shop."""
    logger.info("🚀 Ingesting Sock Shop Python files into FlowRAG")

    # Find all Python files
    python_files = list(SOCK_SHOP_ROOT.rglob("*.py"))
    logger.info(f"Found {len(python_files)} Python files")

    # Get parser and loaders
    parser = get_parser("python")
    neo4j_loader = get_neo4j_loader()
    qdrant_loader = get_qdrant_loader()

    # Process files
    total_units = 0
    total_nodes = 0
    total_relationships = 0
    total_vectors = 0
    start_time = time.time()

    for i, file_path in enumerate(python_files, 1):
        try:
            logger.info(f"  [{i}/{len(python_files)}] {file_path.relative_to(SOCK_SHOP_ROOT)}")

            # Parse
            result = parser.parse_file(str(file_path), namespace=NAMESPACE)

            if result.unit_count > 0:
                total_units += result.unit_count
                logger.info(f"      → {result.unit_count} units ({len(result.classes)} classes, {len(result.functions)} functions, {len(result.methods)} methods)")

                # Load into Neo4j
                neo4j_stats = neo4j_loader.load_parse_result(result)
                total_nodes += neo4j_stats.get("nodes_created", 0)
                total_relationships += neo4j_stats.get("relationships_created", 0)

                # Load into Qdrant
                qdrant_stats = qdrant_loader.load_code_units(result.all_units, namespace=NAMESPACE)
                total_vectors += qdrant_stats.get("vectors_stored", 0)
            else:
                logger.info(f"      → 0 units (empty or __init__.py)")

        except Exception as e:
            logger.error(f"      ❌ Error: {e}")

    elapsed = time.time() - start_time

    logger.info(f"\n{'='*80}")
    logger.info("📊 INGESTION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Files Processed: {len(python_files)}")
    logger.info(f"Code Units: {total_units}")
    logger.info(f"Neo4j Nodes: {total_nodes}")
    logger.info(f"Relationships: {total_relationships}")
    logger.info(f"Vectors: {total_vectors}")
    logger.info(f"Time: {elapsed:.2f}s")
    logger.info(f"{'='*80}\n")

    logger.info("✨ Ingestion complete! Try querying:")
    logger.info(f"   python3 query_sock_shop.py")


if __name__ == "__main__":
    main()
