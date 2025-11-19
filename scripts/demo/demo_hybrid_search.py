#!/usr/bin/env python3
"""
Demo: Hybrid Search (Graph + Vector)

Shows how to combine:
- Semantic search via Qdrant (find by meaning)
- Graph traversal via Neo4j (find by structure)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases import get_neo4j_client, get_qdrant_client
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_header(text):
    print("\n" + "=" * 80)
    print(text.center(80))
    print("=" * 80)

def demo_semantic_search():
    """Demo 1: Pure semantic search using Qdrant."""
    print_header("DEMO 1: Semantic Code Search (Qdrant)")

    client = get_qdrant_client()
    client.connect()

    # Search by meaning, not exact keywords
    query = "payment authorization and validation"
    logger.info(f"Searching for: '{query}'")

    results = client.search(
        query=query,
        namespace="sock_shop:payment",
        limit=5
    )

    print(f"\n📍 Found {len(results)} semantically similar functions:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result.payload['name']} ({result.payload['code_unit_type']})")
        print(f"   File: {result.payload['file_path']}:{result.payload['line_start']}")
        print(f"   Similarity: {result.score:.3f}")
        if result.payload.get('signature'):
            print(f"   Signature: {result.payload['signature']}")
        print()

    client.close()

def demo_graph_search():
    """Demo 2: Graph traversal using Neo4j."""
    print_header("DEMO 2: Call Graph Traversal (Neo4j)")

    client = get_neo4j_client()
    client.connect()

    # Find what Authorise function calls
    query = """
    MATCH (f {name: 'Authorise', namespace: 'sock_shop:payment'})-[:CALLS*1..2]->(called)
    WHERE f.file_path CONTAINS 'service.go'
    RETURN DISTINCT called.name as function, called.file_path as file
    ORDER BY function
    LIMIT 10
    """

    results = client.execute_query(query, {})

    print(f"\n📊 Authorise function call graph:\n")

    if results:
        for r in results:
            file_name = Path(r['file']).name if r['file'] else 'unknown'
            print(f"  → {r['function']} ({file_name})")
    else:
        print("  No calls found")

    client.close()

def demo_hybrid_search():
    """Demo 3: Combine semantic search + graph traversal."""
    print_header("DEMO 3: Hybrid Search (Qdrant + Neo4j)")

    qdrant = get_qdrant_client()
    neo4j = get_neo4j_client()

    qdrant.connect()
    neo4j.connect()

    # Step 1: Find functions semantically
    print("\n🔍 Step 1: Semantic search for 'error handling'")
    vector_results = qdrant.search(
        query="error handling and response encoding",
        namespace="sock_shop:payment",
        limit=3
    )

    for result in vector_results:
        func_name = result.payload['name']
        func_id = result.payload['original_id']

        print(f"\n📌 {func_name} (similarity: {result.score:.3f})")
        print(f"   File: {result.payload['file_path']}:{result.payload['line_start']}")

        # Step 2: Get call graph from Neo4j
        print(f"\n   📊 What {func_name} calls (from graph):")

        graph_query = """
        MATCH (f {id: $id})-[:CALLS]->(called)
        RETURN called.name as name, called.file_path as file
        LIMIT 5
        """

        calls = neo4j.execute_query(graph_query, {"id": func_id})

        if calls:
            for call in calls:
                file_name = Path(call['file']).name if call['file'] else 'unknown'
                print(f"      → {call['name']} ({file_name})")
        else:
            print(f"      (no direct calls found)")

    qdrant.close()
    neo4j.close()

def demo_cross_service_search():
    """Demo 4: Search across all services."""
    print_header("DEMO 4: Cross-Service Semantic Search")

    client = get_qdrant_client()
    client.connect()

    # Search across ALL services
    query = "database connection and initialization"
    logger.info(f"Searching across all services for: '{query}'")

    results = client.search(
        query=query,
        namespace="sock_shop",  # No specific service
        limit=10
    )

    # Group by service
    by_service = {}
    for r in results:
        service = r.payload['namespace'].split(':')[1]
        by_service.setdefault(service, []).append({
            'name': r.payload['name'],
            'score': r.score,
            'file': r.payload['file_path']
        })

    print(f"\n📍 Found {len(results)} functions across {len(by_service)} services:\n")

    for service, functions in sorted(by_service.items()):
        print(f"  {service}:")
        for func in functions[:3]:  # Top 3 per service
            file_name = Path(func['file']).name if func['file'] else 'unknown'
            print(f"    • {func['name']} ({file_name}) - {func['score']:.3f}")
        print()

    client.close()

def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("FlowRAG Hybrid Search Demo".center(80))
    print("Combining Graph Intelligence + Semantic Understanding".center(80))
    print("=" * 80)

    try:
        # Demo 1: Semantic search only
        demo_semantic_search()

        # Demo 2: Graph traversal only
        demo_graph_search()

        # Demo 3: Hybrid (both combined)
        demo_hybrid_search()

        # Demo 4: Cross-service search
        demo_cross_service_search()

        print("\n" + "=" * 80)
        print("✅ Demo Complete!".center(80))
        print("=" * 80)
        print("\n💡 Key Capabilities Demonstrated:")
        print("   1. Semantic search - find code by meaning, not keywords")
        print("   2. Graph traversal - understand code structure and flow")
        print("   3. Hybrid queries - combine both for powerful insights")
        print("   4. Cross-service - search across all languages and services")
        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise

if __name__ == "__main__":
    main()
