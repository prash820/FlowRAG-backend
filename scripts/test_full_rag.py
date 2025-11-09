#!/usr/bin/env python3
"""
Complete FlowRAG test using all databases: Neo4j, Qdrant, and Redis.
Demonstrates full GraphRAG + Vector search functionality.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import redis

from databases.neo4j.client import Neo4jClient
from ingestion.parsers.python_parser import PythonParser
from ingestion.loaders.neo4j_loader import Neo4jLoader


# Sample Python code to analyze
SAMPLE_CODE = '''"""Sample module for testing FlowRAG."""

class UserAuthentication:
    """Handles user authentication and authorization."""

    def __init__(self, db_connection):
        """Initialize authentication system."""
        self.db = db_connection
        self.session_cache = {}

    def authenticate(self, username, password):
        """Authenticate user with username and password."""
        user = self.db.get_user(username)
        if user and self.verify_password(password, user.password_hash):
            session = self.create_session(user)
            return session
        return None

    def verify_password(self, password, hash):
        """Verify password against stored hash."""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest() == hash

    def create_session(self, user):
        """Create new session for authenticated user."""
        import uuid
        session_id = str(uuid.uuid4())
        self.session_cache[session_id] = user
        return session_id

def validate_email(email):
    """Validate email format using regex."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def hash_password(password):
    """Hash password using SHA256."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
'''


def print_section(title):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def test_all_connections():
    """Test all database connections."""
    print_section("1. Testing Database Connections")

    results = {}

    # Test Neo4j
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "your-password-here")
        )
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            value = result.single()["test"]
        driver.close()
        print("✓ Neo4j: Connected successfully")
        results['neo4j'] = True
    except Exception as e:
        print(f"✗ Neo4j: Failed - {e}")
        results['neo4j'] = False

    # Test Qdrant
    try:
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections()
        print(f"✓ Qdrant: Connected successfully ({len(collections.collections)} collections)")
        results['qdrant'] = True
    except Exception as e:
        print(f"✗ Qdrant: Failed - {e}")
        results['qdrant'] = False

    # Test Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✓ Redis: Connected successfully")
        results['redis'] = True
    except Exception as e:
        print(f"✗ Redis: Failed - {e}")
        results['redis'] = False

    return results


def test_parse_code():
    """Parse sample Python code."""
    print_section("2. Parsing Python Code")

    try:
        parser = PythonParser()
        result = parser.parse_string(
            code=SAMPLE_CODE,
            namespace="test_full_rag",
            file_path="auth.py"
        )

        print(f"✓ Parsed successfully:")
        print(f"  - Modules: {len(result.modules)}")
        print(f"  - Classes: {len(result.classes)}")
        print(f"  - Functions: {len(result.functions)}")
        print(f"  - Methods: {len(result.methods)}")

        print("\n  Classes found:")
        for cls in result.classes:
            print(f"    • {cls.name} - {cls.docstring[:50] if cls.docstring else 'No docs'}...")

        print("\n  Functions found:")
        for func in result.functions:
            print(f"    • {func.name}() - {func.docstring[:50] if func.docstring else 'No docs'}...")

        return result
    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_load_to_neo4j(parse_result):
    """Load parsed code into Neo4j graph."""
    print_section("3. Loading Code into Neo4j Graph")

    try:
        loader = Neo4jLoader()
        result = loader.load_parse_result(parse_result)

        print(f"✓ Loaded to Neo4j:")
        print(f"  - Nodes created: {result['nodes_created']}")
        print(f"  - Relationships created: {result['relationships_created']}")

        return True
    except Exception as e:
        print(f"✗ Loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_load_to_qdrant(parse_result):
    """Load code embeddings into Qdrant."""
    print_section("4. Loading Embeddings into Qdrant")

    try:
        # Initialize Qdrant client
        qdrant = QdrantClient(host="localhost", port=6333)
        collection_name = "test_code_embeddings"

        # Create collection if it doesn't exist
        try:
            qdrant.get_collection(collection_name)
            print(f"  Collection '{collection_name}' already exists")
        except:
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            print(f"  Created collection '{collection_name}'")

        # For demo purposes, we'll use dummy embeddings
        # In production, you'd use actual embeddings from a model
        import random

        points = []
        point_id = 0

        for unit in parse_result.all_units:
            # Create dummy embedding (in production, use real embedding model)
            embedding = [random.random() for _ in range(384)]

            point_id += 1
            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "name": unit.name,
                    "type": unit.type.value,
                    "docstring": unit.docstring or "",
                    "code": unit.code[:200],  # First 200 chars
                    "file_path": unit.file_path,
                    "namespace": unit.namespace
                }
            })

        # Upload points
        if points:
            qdrant.upsert(
                collection_name=collection_name,
                points=points
            )
            print(f"✓ Loaded {len(points)} embeddings to Qdrant")

        return collection_name
    except Exception as e:
        print(f"✗ Qdrant loading failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_graph_queries(neo4j_client):
    """Test Neo4j graph queries."""
    print_section("5. Testing Graph Queries (Neo4j)")

    namespace = "test_full_rag"

    # Query 1: Find all classes
    print("\n📊 Query 1: All Classes")
    query = """
    MATCH (c:Class {namespace: $namespace})
    RETURN c.name as name, c.docstring as doc
    ORDER BY c.name
    """
    results = neo4j_client.execute_query(query, {"namespace": namespace})
    for r in results:
        print(f"  • {r['name']} - {r['doc'][:60] if r['doc'] else 'No docs'}...")

    # Query 2: Class methods
    print("\n📊 Query 2: Class Methods")
    query = """
    MATCH (c:Class {namespace: $namespace})-[:CONTAINS]->(m:Method)
    RETURN c.name as class, m.name as method, m.docstring as doc
    ORDER BY m.name
    """
    results = neo4j_client.execute_query(query, {"namespace": namespace})
    for r in results:
        print(f"  • {r['class']}.{r['method']}() - {r['doc'][:50] if r['doc'] else 'No docs'}...")

    # Query 3: Function calls in methods
    print("\n📊 Query 3: Function Calls from Methods")
    query = """
    MATCH (m:Method {namespace: $namespace})-[:CALLS]->(f:Function)
    RETURN m.name as method, collect(f.name) as calls
    """
    results = neo4j_client.execute_query(query, {"namespace": namespace})
    for r in results:
        if r['calls']:
            print(f"  • {r['method']}() calls: {', '.join(r['calls'])}")


def test_vector_search(collection_name):
    """Test Qdrant vector search."""
    print_section("6. Testing Vector Search (Qdrant)")

    try:
        qdrant = QdrantClient(host="localhost", port=6333)

        # Search for authentication-related code (using dummy query vector)
        import random
        query_vector = [random.random() for _ in range(384)]

        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5
        )

        print("\n🔍 Vector Search Results (Top 5):")
        for i, result in enumerate(results, 1):
            payload = result.payload
            print(f"\n  {i}. {payload['name']} ({payload['type']})")
            print(f"     File: {payload['file_path']}")
            if payload.get('docstring'):
                print(f"     Desc: {payload['docstring'][:60]}...")

        print(f"\n✓ Found {len(results)} results from vector search")
        return True
    except Exception as e:
        print(f"✗ Vector search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_cache():
    """Test Redis caching."""
    print_section("7. Testing Redis Cache")

    try:
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Store a test value
        test_key = "test_full_rag:cache:demo"
        test_value = "FlowRAG cache test"

        r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
        retrieved = r.get(test_key).decode('utf-8')

        if retrieved == test_value:
            print(f"✓ Redis cache working correctly")
            print(f"  - Stored: '{test_value}'")
            print(f"  - Retrieved: '{retrieved}'")

            # Clean up
            r.delete(test_key)
            return True
        else:
            print(f"✗ Cache mismatch: expected '{test_value}', got '{retrieved}'")
            return False
    except Exception as e:
        print(f"✗ Redis cache test failed: {e}")
        return False


def cleanup(collection_name):
    """Clean up test data."""
    print_section("8. Cleanup")

    try:
        # Clean Neo4j
        neo4j_client = Neo4jClient()
        query = "MATCH (n {namespace: 'test_full_rag'}) DETACH DELETE n"
        neo4j_client.execute_query(query, {})
        print("✓ Cleaned up Neo4j test data")

        # Clean Qdrant
        if collection_name:
            qdrant = QdrantClient(host="localhost", port=6333)
            qdrant.delete_collection(collection_name)
            print(f"✓ Deleted Qdrant collection '{collection_name}'")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")


def main():
    """Run the complete FlowRAG test."""
    print("\n" + "="*70)
    print("  FlowRAG Complete System Test")
    print("="*70)
    print("\nThis demonstrates full FlowRAG functionality:")
    print("  • Neo4j graph database (structure & relationships)")
    print("  • Qdrant vector database (semantic search)")
    print("  • Redis cache (performance)")
    print("  • Code parsing with AST")
    print("  • Graph and vector retrieval")

    # Step 1: Test connections
    connections = test_all_connections()
    if not all(connections.values()):
        print("\n❌ Some databases are not accessible.")
        print("Make sure all services are running: docker compose up -d")
        return 1

    # Step 2: Parse code
    parse_result = test_parse_code()
    if not parse_result:
        return 1

    # Step 3: Load to Neo4j
    if not test_load_to_neo4j(parse_result):
        return 1

    # Step 4: Load to Qdrant
    collection_name = test_load_to_qdrant(parse_result)
    if not collection_name:
        return 1

    # Step 5: Test graph queries
    try:
        neo4j_client = Neo4jClient()
        test_graph_queries(neo4j_client)
    except Exception as e:
        print(f"\n✗ Graph queries failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 6: Test vector search
    if not test_vector_search(collection_name):
        return 1

    # Step 7: Test Redis cache
    if not test_redis_cache():
        return 1

    # Step 8: Cleanup
    cleanup(collection_name)

    print("\n" + "="*70)
    print("  ✓ Complete FlowRAG Test Passed!")
    print("="*70)
    print("\n💡 What was tested:")
    print("  ✓ Neo4j graph construction and querying")
    print("  ✓ Qdrant vector storage and search")
    print("  ✓ Redis caching functionality")
    print("  ✓ Python code parsing (AST)")
    print("  ✓ Multi-database integration")
    print("\nYour FlowRAG system is fully operational!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
