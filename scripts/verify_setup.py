#!/usr/bin/env python3
"""
Quick verification script to test FlowRAG setup.
Tests database connectivity without requiring full dependency install.
"""

import sys


def test_neo4j():
    """Test Neo4j connection."""
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "your-password-here")
        )

        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            value = result.single()["test"]
            assert value == 1

        driver.close()
        print("✓ Neo4j: Connected successfully")
        return True
    except Exception as e:
        print(f"✗ Neo4j: Failed - {e}")
        return False


def test_redis():
    """Test Redis connection."""
    try:
        import redis

        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis: Connected successfully")
        return True
    except Exception as e:
        print(f"✗ Redis: Failed - {e}")
        return False


def test_qdrant():
    """Test Qdrant connection."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        print(f"✓ Qdrant: Connected successfully ({len(collections.collections)} collections)")
        return True
    except Exception as e:
        print(f"✗ Qdrant: Failed - {e}")
        return False


def main():
    """Run all connectivity tests."""
    print("=" * 60)
    print("FlowRAG Setup Verification")
    print("=" * 60)

    results = []

    print("\nTesting database connections...")
    results.append(("Neo4j", test_neo4j()))
    results.append(("Redis", test_redis()))
    results.append(("Qdrant", test_qdrant()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All services are ready!")
        print("\nNext steps:")
        print("1. Install dependencies: poetry install")
        print("2. Run integration tests: poetry run pytest tests/integration/")
        print("3. Start API server: poetry run python -m api.main")
        return 0
    else:
        print("\n✗ Some services failed. Check docker compose logs.")
        print("Run: docker compose logs <service-name>")
        return 1


if __name__ == "__main__":
    sys.exit(main())
