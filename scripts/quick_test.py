#!/usr/bin/env python3
"""
Quick test without dependencies - just verify services are accessible.
"""

import http.client
import json


def test_neo4j():
    """Test Neo4j HTTP endpoint."""
    try:
        conn = http.client.HTTPConnection("localhost", 7474)
        conn.request("GET", "/")
        response = conn.getresponse()
        if response.status == 200:
            print("✓ Neo4j: HTTP endpoint accessible (port 7474)")
            return True
        else:
            print(f"✗ Neo4j: Unexpected status {response.status}")
            return False
    except Exception as e:
        print(f"✗ Neo4j: Connection failed - {e}")
        return False


def test_qdrant():
    """Test Qdrant health endpoint."""
    try:
        conn = http.client.HTTPConnection("localhost", 6333)
        conn.request("GET", "/healthz")
        response = conn.getresponse()
        if response.status == 200:
            print("✓ Qdrant: Health check passed (port 6333)")
            return True
        else:
            print(f"✗ Qdrant: Health check returned {response.status}")
            return False
    except Exception as e:
        print(f"✗ Qdrant: Connection failed - {e}")
        return False


def test_redis():
    """Test Redis port."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()
        if result == 0:
            print("✓ Redis: Port 6379 is accessible")
            return True
        else:
            print("✗ Redis: Port 6379 not accessible")
            return False
    except Exception as e:
        print(f"✗ Redis: Connection test failed - {e}")
        return False


def main():
    print("=" * 60)
    print("FlowRAG Quick Service Check")
    print("=" * 60)
    print()

    results = []
    results.append(test_neo4j())
    results.append(test_qdrant())
    results.append(test_redis())

    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} services accessible")
    print("=" * 60)

    if passed == total:
        print()
        print("✓ All services are running!")
        print()
        print("Next steps:")
        print("1. Install Poetry: pip install poetry")
        print("2. Install dependencies: poetry install")
        print("3. Run tests: poetry run pytest tests/integration/")
        return 0
    else:
        print()
        print("✗ Some services are not accessible")
        print("Check: docker compose ps")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
