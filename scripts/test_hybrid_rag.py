#!/usr/bin/env python3
"""
Hybrid GraphRAG Test - Combining Graph and Vector Search.

This demonstrates the true power of GraphRAG by combining:
1. Graph traversal for structural relationships
2. Vector similarity for semantic understanding
3. Hybrid retrieval strategies
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib

from databases.neo4j.client import Neo4jClient
from ingestion.parsers.python_parser import PythonParser
from ingestion.loaders.neo4j_loader import Neo4jLoader


# Sample codebase: A simple web API with authentication
SAMPLE_CODE = {
    "auth.py": '''"""Authentication module for user management."""

import hashlib
import jwt
from datetime import datetime, timedelta

class AuthenticationService:
    """Handles user authentication and token management."""

    def __init__(self, secret_key, db_connection):
        """Initialize authentication service with secret key."""
        self.secret_key = secret_key
        self.db = db_connection

    def authenticate_user(self, username, password):
        """Authenticate user with username and password.

        Returns JWT token if successful, None otherwise.
        """
        user = self.db.get_user_by_username(username)
        if not user:
            return None

        if self.verify_password(password, user.password_hash):
            token = self.generate_token(user)
            return token

        return None

    def verify_password(self, password, stored_hash):
        """Verify password against stored hash using SHA256."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == stored_hash

    def generate_token(self, user):
        """Generate JWT token for authenticated user."""
        payload = {
            'user_id': user.id,
            'username': user.username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        return token

def hash_password(password):
    """Hash password using SHA256 for storage."""
    return hashlib.sha256(password.encode()).hexdigest()
''',

    "api.py": '''"""API endpoints for user operations."""

from fastapi import FastAPI, HTTPException, Depends
from auth import AuthenticationService
from database import DatabaseConnection

app = FastAPI()

def get_auth_service():
    """Dependency injection for authentication service."""
    db = DatabaseConnection()
    return AuthenticationService(secret_key="my-secret", db_connection=db)

@app.post("/login")
async def login(username: str, password: str, auth: AuthenticationService = Depends(get_auth_service)):
    """Login endpoint that authenticates user and returns JWT token."""
    token = auth.authenticate_user(username, password)
    if not token:
        raise HTTPException(status_code=401, message="Invalid credentials")
    return {"access_token": token, "token_type": "bearer"}

@app.post("/register")
async def register(username: str, password: str):
    """Register new user with hashed password."""
    from auth import hash_password

    password_hash = hash_password(password)
    # Store user in database
    db = DatabaseConnection()
    user = db.create_user(username, password_hash)
    return {"user_id": user.id, "username": user.username}

@app.get("/profile")
async def get_profile(token: str, auth: AuthenticationService = Depends(get_auth_service)):
    """Get user profile using JWT token for authentication."""
    # Verify token and return user profile
    user = auth.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, message="Invalid token")
    return {"user": user}
''',

    "database.py": '''"""Database connection and operations."""

import sqlite3

class DatabaseConnection:
    """SQLite database connection for user management."""

    def __init__(self, db_path="users.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn

    def get_user_by_username(self, username):
        """Retrieve user by username from database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

    def create_user(self, username, password_hash):
        """Create new user in database with hashed password."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        self.conn.commit()
        return self.get_user_by_username(username)
'''
}


def print_section(title, char="="):
    """Print formatted section header."""
    print(f"\n{char*70}")
    print(f"  {title}")
    print(f"{char*70}")


def create_simple_embedding(text):
    """Create a simple deterministic embedding from text.

    In production, use a real embedding model like OpenAI or sentence-transformers.
    For demo purposes, we create a 384-dim vector based on text hash.
    """
    # Use text hash to create deterministic but varied embeddings
    hash_obj = hashlib.sha256(text.encode())
    hash_bytes = hash_obj.digest()

    # Create 384-dim vector (matching our collection size)
    embedding = []
    for i in range(384):
        # Use hash bytes cyclically to generate float values
        byte_val = hash_bytes[i % len(hash_bytes)]
        # Normalize to [-1, 1] range
        embedding.append((byte_val / 255.0) * 2 - 1)

    return embedding


def ingest_codebase(namespace="hybrid_rag_test"):
    """Parse and load all code into Neo4j and Qdrant."""
    print_section("1. Ingesting Codebase")

    parser = PythonParser()
    loader = Neo4jLoader()
    qdrant = QdrantClient(host="localhost", port=6333)
    collection_name = "hybrid_rag_embeddings"

    # Create Qdrant collection
    try:
        qdrant.delete_collection(collection_name)
    except:
        pass

    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
    )

    total_nodes = 0
    total_relationships = 0
    points = []
    point_id = 0

    for filename, code in SAMPLE_CODE.items():
        print(f"\n  Processing {filename}...")

        # Parse code
        parse_result = parser.parse_string(
            code=code,
            namespace=namespace,
            file_path=filename
        )

        # Load to Neo4j
        result = loader.load_parse_result(parse_result)
        total_nodes += result['nodes_created']
        total_relationships += result['relationships_created']

        print(f"    Neo4j: {result['nodes_created']} nodes, {result['relationships_created']} relationships")

        # Create embeddings for Qdrant
        for unit in parse_result.all_units:
            point_id += 1

            # Create embedding from code + docstring
            text_to_embed = f"{unit.name} {unit.docstring or ''} {unit.code[:200]}"
            embedding = create_simple_embedding(text_to_embed)

            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "id": unit.id,
                    "name": unit.name,
                    "type": unit.type.value,
                    "file_path": unit.file_path,
                    "docstring": unit.docstring or "",
                    "code": unit.code[:500],
                    "namespace": namespace
                }
            ))

        print(f"    Qdrant: {len(parse_result.all_units)} embeddings created")

    # Upload to Qdrant
    qdrant.upsert(collection_name=collection_name, points=points)

    print(f"\n  ✓ Total: {total_nodes} nodes, {total_relationships} relationships in Neo4j")
    print(f"  ✓ Total: {len(points)} embeddings in Qdrant")

    return collection_name, namespace


def test_graph_only_retrieval(namespace):
    """Test 1: Pure graph-based retrieval."""
    print_section("2. Graph-Only Retrieval", char="-")

    neo4j = Neo4jClient()

    print("\n  Query: Find all functions that handle password operations")
    print("  Method: Cypher pattern matching on function names\n")

    query = """
    MATCH (f:Function {namespace: $namespace})
    WHERE toLower(f.name) CONTAINS 'password'
       OR toLower(f.docstring) CONTAINS 'password'
    RETURN f.name as name, f.file_path as file, f.docstring as doc
    ORDER BY f.name
    """

    results = neo4j.execute_query(query, {"namespace": namespace})

    print("  📊 Results:")
    for r in results:
        print(f"    • {r['name']}() in {r['file']}")
        print(f"      {r['doc'][:60] if r['doc'] else 'No description'}...")

    return results


def test_vector_only_retrieval(collection_name, namespace):
    """Test 2: Pure vector-based retrieval."""
    print_section("3. Vector-Only Retrieval", char="-")

    qdrant = QdrantClient(host="localhost", port=6333)

    print("\n  Query: Find code related to 'user authentication and security'")
    print("  Method: Semantic similarity search\n")

    # Create query embedding
    query_text = "user authentication and security token validation"
    query_vector = create_simple_embedding(query_text)

    from qdrant_client.models import Filter, FieldCondition, MatchValue

    results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=5,
        query_filter=Filter(
            must=[
                FieldCondition(key="namespace", match=MatchValue(value=namespace))
            ]
        )
    )

    print("  🔍 Results (ranked by semantic similarity):")
    for i, result in enumerate(results, 1):
        payload = result.payload
        print(f"\n    {i}. {payload['name']} ({payload['type']}) - Score: {result.score:.3f}")
        print(f"       File: {payload['file_path']}")
        if payload.get('docstring'):
            print(f"       {payload['docstring'][:60]}...")

    return results


def test_hybrid_retrieval_expansion(collection_name, namespace):
    """Test 3: Hybrid retrieval - Vector search + Graph expansion."""
    print_section("4. Hybrid Retrieval: Vector → Graph Expansion", char="-")

    neo4j = Neo4jClient()
    qdrant = QdrantClient(host="localhost", port=6333)

    print("\n  Query: Find authentication code and explore its dependencies")
    print("  Method: Vector search → Graph traversal to find related code\n")

    # Step 1: Vector search to find relevant starting points
    query_text = "authenticate user with credentials"
    query_vector = create_simple_embedding(query_text)

    vector_results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=3,
        query_filter={
            "must": [
                {"key": "namespace", "match": {"value": namespace}},
                {"key": "type", "match": {"value": "Method"}}
            ]
        }
    ).points

    print("  Step 1: Vector search found these entry points:")
    for r in vector_results:
        print(f"    • {r.payload['name']}() in {r.payload['file_path']}")

    # Step 2: Graph expansion - find what these methods call
    if vector_results:
        top_match = vector_results[0].payload
        print(f"\n  Step 2: Expanding from '{top_match['name']}' via graph relationships...")

        # Find all functions/methods this calls
        query = """
        MATCH (start {namespace: $namespace, name: $name})-[:CALLS]->(called)
        RETURN called.name as name,
               called.type as type,
               called.file_path as file,
               called.docstring as doc
        ORDER BY called.name
        """

        graph_results = neo4j.execute_query(
            query,
            {"namespace": namespace, "name": top_match['name']}
        )

        if graph_results:
            print(f"\n  📊 {top_match['name']}() calls these functions:")
            for r in graph_results:
                print(f"    → {r['name']}() in {r['file']}")
                if r['doc']:
                    print(f"      {r['doc'][:60]}...")
        else:
            print(f"\n  (No function calls found)")

    # Step 3: Find related classes
    print(f"\n  Step 3: Finding related classes via graph structure...")

    query = """
    MATCH (c:Class {namespace: $namespace})-[:CONTAINS]->(m:Method)
    WHERE m.name = $method_name
    RETURN c.name as class_name,
           collect(m.name) as methods,
           c.docstring as doc
    """

    if vector_results:
        class_results = neo4j.execute_query(
            query,
            {"namespace": namespace, "method_name": top_match['name']}
        )

        if class_results:
            for r in class_results:
                print(f"\n  📦 Class: {r['class_name']}")
                print(f"     {r['doc'][:70] if r['doc'] else 'No description'}...")
                print(f"     All methods: {', '.join(r['methods'][:5])}...")


def test_hybrid_retrieval_filtering(collection_name, namespace):
    """Test 4: Hybrid retrieval - Graph filter + Vector search."""
    print_section("5. Hybrid Retrieval: Graph Filter → Vector Ranking", char="-")

    neo4j = Neo4jClient()
    qdrant = QdrantClient(host="localhost", port=6333)

    print("\n  Query: Find database-related code, ranked by relevance")
    print("  Method: Graph structure filter → Vector ranking\n")

    # Step 1: Use graph to find all code in database module
    print("  Step 1: Using graph to find code in database.py...")

    query = """
    MATCH (n {namespace: $namespace, file_path: $file})
    RETURN n.id as id, n.name as name, n.type as type
    ORDER BY n.type, n.name
    """

    graph_results = neo4j.execute_query(
        query,
        {"namespace": namespace, "file": "database.py"}
    )

    print(f"  Found {len(graph_results)} items in database.py:")
    for r in graph_results:
        print(f"    • {r['name']} ({r['type']})")

    # Step 2: Use vector search within those results
    print("\n  Step 2: Ranking by semantic relevance to 'retrieve user data'...")

    query_text = "retrieve user data from database by username"
    query_vector = create_simple_embedding(query_text)

    # Filter Qdrant search to only database.py
    vector_results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=5,
        query_filter={
            "must": [
                {"key": "namespace", "match": {"value": namespace}},
                {"key": "file_path", "match": {"value": "database.py"}}
            ]
        }
    ).points

    print("\n  🔍 Results ranked by semantic similarity:")
    for i, r in enumerate(vector_results, 1):
        print(f"    {i}. {r.payload['name']} - Score: {r.score:.3f}")
        if r.payload.get('docstring'):
            print(f"       {r.payload['docstring'][:60]}...")


def test_full_context_assembly(collection_name, namespace):
    """Test 5: Complete context assembly for a query."""
    print_section("6. Full Context Assembly (Production Workflow)", char="-")

    neo4j = Neo4jClient()
    qdrant = QdrantClient(host="localhost", port=6333)

    user_query = "How does the login system work?"

    print(f"\n  User Query: '{user_query}'")
    print("  \n  Assembling complete context using hybrid retrieval...\n")

    # Step 1: Vector search for relevant code
    print("  Step 1: Semantic search for relevant code...")
    query_vector = create_simple_embedding(user_query)

    vector_results = qdrant.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=3,
        query_filter={
            "must": [{"key": "namespace", "match": {"value": namespace}}]
        }
    ).points

    relevant_names = [r.payload['name'] for r in vector_results]
    print(f"     Found: {', '.join(relevant_names)}")

    # Step 2: Graph expansion for each result
    print("\n  Step 2: Graph expansion to find dependencies...")

    context_items = []

    for result in vector_results:
        name = result.payload['name']

        # Get complete context from graph
        query = """
        MATCH (n {namespace: $namespace, name: $name})
        OPTIONAL MATCH (n)-[:CALLS]->(called)
        OPTIONAL MATCH (caller)-[:CALLS]->(n)
        OPTIONAL MATCH (parent)-[:CONTAINS]->(n)
        RETURN
            n.name as name,
            n.type as type,
            n.code as code,
            n.docstring as doc,
            collect(DISTINCT called.name) as calls,
            collect(DISTINCT caller.name) as called_by,
            parent.name as parent_class
        """

        graph_data = neo4j.execute_query(
            query,
            {"namespace": namespace, "name": name}
        )

        if graph_data:
            item = graph_data[0]
            context_items.append(item)

            print(f"\n     • {item['name']} ({item['type']})")
            if item['parent_class']:
                print(f"       Parent: {item['parent_class']}")
            if item['calls'] and item['calls'][0]:
                print(f"       Calls: {', '.join([c for c in item['calls'] if c])}")
            if item['called_by'] and item['called_by'][0]:
                print(f"       Called by: {', '.join([c for c in item['called_by'] if c])}")

    # Step 3: Assemble final context
    print("\n  Step 3: Assembling final context for LLM...")

    final_context = []
    final_context.append(f"# Question: {user_query}\n")
    final_context.append("# Relevant Code Context:\n")

    for item in context_items:
        final_context.append(f"\n## {item['name']} ({item['type']})")
        if item['doc']:
            final_context.append(f"Description: {item['doc']}")
        if item['parent_class']:
            final_context.append(f"Part of class: {item['parent_class']}")
        final_context.append(f"\n```python\n{item['code'][:300]}...\n```")

        if item['calls'] and item['calls'][0]:
            final_context.append(f"Calls: {', '.join([c for c in item['calls'] if c])}")

    context_text = "\n".join(final_context)

    print(f"\n  ✓ Assembled {len(context_items)} code items with full context")
    print(f"  ✓ Total context size: {len(context_text)} characters")
    print(f"\n  Context preview:")
    print("  " + "-" * 66)
    for line in context_text.split('\n')[:15]:
        print(f"  {line}")
    print("  " + "-" * 66)
    print("  ... (truncated)")


def cleanup(collection_name, namespace):
    """Clean up test data."""
    print_section("7. Cleanup")

    try:
        # Clean Neo4j
        neo4j = Neo4jClient()
        query = f"MATCH (n {{namespace: '{namespace}'}}) DETACH DELETE n"
        neo4j.execute_query(query, {})
        print("  ✓ Cleaned up Neo4j test data")

        # Clean Qdrant
        qdrant = QdrantClient(host="localhost", port=6333)
        qdrant.delete_collection(collection_name)
        print(f"  ✓ Deleted Qdrant collection '{collection_name}'")
    except Exception as e:
        print(f"  ⚠ Cleanup warning: {e}")


def main():
    """Run hybrid GraphRAG demonstration."""
    print("\n" + "="*70)
    print("  Hybrid GraphRAG Test - Graph + Vector Retrieval")
    print("="*70)
    print("\nThis demonstrates combining graph and vector search for rich")
    print("code understanding and retrieval:")
    print("  • Graph: Structural relationships (calls, contains, imports)")
    print("  • Vector: Semantic similarity (meaning, context)")
    print("  • Hybrid: Best of both worlds!")

    # Ingest codebase
    collection_name, namespace = ingest_codebase()

    # Run different retrieval strategies
    test_graph_only_retrieval(namespace)
    test_vector_only_retrieval(collection_name, namespace)
    test_hybrid_retrieval_expansion(collection_name, namespace)
    test_hybrid_retrieval_filtering(collection_name, namespace)
    test_full_context_assembly(collection_name, namespace)

    # Cleanup
    cleanup(collection_name, namespace)

    print("\n" + "="*70)
    print("  ✓ Hybrid GraphRAG Test Complete!")
    print("="*70)
    print("\n💡 Key Insights:")
    print("  • Graph search: Precise structural queries (calls, dependencies)")
    print("  • Vector search: Semantic relevance (finds similar concepts)")
    print("  • Hybrid approach: Combines precision + semantic understanding")
    print("  • Context assembly: Rich, relationship-aware code context for LLMs")
    print("\nThis is the power of GraphRAG - going beyond simple vector search!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
