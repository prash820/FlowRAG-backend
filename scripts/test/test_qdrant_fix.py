#!/usr/bin/env python3
"""
Test Qdrant fix with a single file ingestion
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ingestion import get_parser, get_neo4j_loader, get_qdrant_loader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test with a single small file
TEST_FILE = Path.home() / "Documents/workspace/sock-shop-services/payment/service.go"
NAMESPACE = "sock_shop:payment"

logger.info(f"Testing Qdrant fix with file: {TEST_FILE}")

# Get parser
parser = get_parser("go")

# Parse file
logger.info("Parsing file...")
parse_result = parser.parse_file(str(TEST_FILE), namespace=NAMESPACE)
logger.info(f"Extracted {parse_result.unit_count} code units")

# Load into Neo4j
logger.info("Loading to Neo4j...")
neo4j_loader = get_neo4j_loader()
neo4j_stats = neo4j_loader.load_parse_result(parse_result)
logger.info(f"Neo4j: {neo4j_stats.get('nodes_created', 0)} nodes created")

# Load into Qdrant
logger.info("Loading to Qdrant...")
qdrant_loader = get_qdrant_loader()
qdrant_stats = qdrant_loader.load_code_units(
    parse_result.all_units,
    namespace=NAMESPACE
)
logger.info(f"Qdrant: {qdrant_stats.get('upserted_count', 0)} vectors stored")

logger.info("✅ Test complete! Qdrant is now working.")
