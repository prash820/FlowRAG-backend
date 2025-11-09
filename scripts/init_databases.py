#!/usr/bin/env python3
"""
Database initialization script.

Initializes Neo4j schema and Qdrant collections.
Run this before first use of the application.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from databases import get_neo4j_client, get_qdrant_client
from config import get_settings


def initialize_neo4j() -> None:
    """Initialize Neo4j schema (indexes and constraints)."""
    print("Initializing Neo4j...")

    try:
        client = get_neo4j_client()
        client.initialize_schema()
        stats = client.get_stats()
        print(f"✓ Neo4j initialized")
        print(f"  Nodes: {stats['nodes']}")
        print(f"  Relationships: {stats['relationships']}")
    except Exception as e:
        print(f"✗ Neo4j initialization failed: {e}")
        raise


def initialize_qdrant() -> None:
    """Initialize Qdrant collection."""
    print("\nInitializing Qdrant...")

    try:
        client = get_qdrant_client()
        settings = get_settings()

        client.create_collection(
            collection_name=settings.qdrant_collection,
            vector_size=settings.qdrant_vector_size,
        )

        info = client.get_collection_info()
        print(f"✓ Qdrant initialized")
        print(f"  Collection: {info['name']}")
        print(f"  Vector size: {info['vector_size']}")
        print(f"  Points count: {info['points_count']}")
    except Exception as e:
        print(f"✗ Qdrant initialization failed: {e}")
        raise


def main() -> None:
    """Run database initialization."""
    print("=" * 60)
    print("FlowRAG Database Initialization")
    print("=" * 60)
    print()

    try:
        initialize_neo4j()
        initialize_qdrant()

        print()
        print("=" * 60)
        print("✓ All databases initialized successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Index your first repository:")
        print("     POST /api/v1/ingest")
        print("  2. Query your code:")
        print("     POST /api/v1/query")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("✗ Initialization failed!")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nPlease check:")
        print("  - Neo4j is running (port 7687)")
        print("  - Qdrant is running (port 6333)")
        print("  - .env file has correct credentials")
        sys.exit(1)


if __name__ == "__main__":
    main()
