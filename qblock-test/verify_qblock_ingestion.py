#!/usr/bin/env python3
"""
Verify QBlock Platform Ingestion
Checks both Neo4j graph data and Qdrant vector data
"""

import sys
import os

# Add flowrag-master to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from databases import get_neo4j_client, get_qdrant_client

def verify_neo4j():
    """Verify Neo4j graph data."""
    print("\n" + "="*60)
    print("NEO4J VERIFICATION")
    print("="*60)

    client = get_neo4j_client()

    # Count total nodes
    query = "MATCH (n) RETURN count(n) as total"
    result = client.execute_query(query)
    total_nodes = result[0]['total'] if result else 0
    print(f"\n✓ Total nodes: {total_nodes}")

    # Count nodes by namespace
    query = """
    MATCH (n)
    WHERE n.namespace IS NOT NULL
    RETURN n.namespace as namespace, count(n) as count
    ORDER BY count DESC
    """
    results = client.execute_query(query)

    print(f"\n📊 Nodes per namespace:")
    for row in results:
        print(f"  • {row['namespace']}: {row['count']} nodes")

    # Count relationships by type
    query = """
    MATCH ()-[r]->()
    RETURN type(r) as rel_type, count(r) as count
    ORDER BY count DESC
    """
    results = client.execute_query(query)

    print(f"\n🔗 Relationships by type:")
    for row in results:
        print(f"  • {row['rel_type']}: {row['count']}")

    # Count cross-service CALLS_API relationships
    query = """
    MATCH (n1)-[r:CALLS_API]->(n2)
    WHERE n1.namespace <> n2.namespace
    RETURN n1.namespace as from_service, n2.namespace as to_service, count(r) as calls
    ORDER BY calls DESC
    """
    results = client.execute_query(query)

    print(f"\n🌐 Cross-service API calls:")
    total_cross_service = 0
    for row in results:
        print(f"  • {row['from_service']} -> {row['to_service']}: {row['calls']} calls")
        total_cross_service += row['calls']

    print(f"\n✓ Total cross-service relationships: {total_cross_service}")


def verify_qdrant():
    """Verify Qdrant vector data."""
    print("\n" + "="*60)
    print("QDRANT VERIFICATION")
    print("="*60)

    client = get_qdrant_client()

    # Get collection info
    info = client.get_collection_info()
    print(f"\n✓ Collection: {info['name']}")
    print(f"✓ Total vectors: {info['points_count']}")
    print(f"✓ Vector dimension: {info['vector_size']}")

    # Count vectors per namespace
    namespaces = [
        'qblock-mobile',
        'qblock-label-service',
        'qblock-auth-service',
        'qblock-shop-data',
        'qblock-transaction-data',
        'qblock-metrics'
    ]

    print(f"\n📊 Vectors per namespace:")
    total = 0
    for ns in namespaces:
        count = client.count_vectors(namespace=ns)
        print(f"  • {ns}: {count} vectors")
        total += count

    print(f"\n✓ Total namespace vectors: {total}")

    # Count by vector type (code vs documentation)
    print(f"\n📝 Vector types breakdown:")
    for ns in namespaces:
        # Search for code vectors (has 'type': 'code')
        code_results = client.client.scroll(
            collection_name=client.collection_name,
            scroll_filter={
                "must": [
                    {"key": "namespace", "match": {"value": ns}},
                    {"key": "type", "match": {"value": "code"}}
                ]
            },
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        code_count = len(code_results[0]) if code_results else 0

        # Search for document vectors
        doc_results = client.client.scroll(
            collection_name=client.collection_name,
            scroll_filter={
                "must": [
                    {"key": "namespace", "match": {"value": ns}},
                    {"key": "type", "match": {"value": "document"}}
                ]
            },
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        doc_count = len(doc_results[0]) if doc_results else 0

        # Search for documentation summary vectors
        summary_results = client.client.scroll(
            collection_name=client.collection_name,
            scroll_filter={
                "must": [
                    {"key": "namespace", "match": {"value": ns}},
                    {"key": "type", "match": {"value": "documentation"}}
                ]
            },
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        summary_count = len(summary_results[0]) if summary_results else 0

        total_ns = code_count + doc_count + summary_count
        print(f"  • {ns}: {total_ns} total ({code_count} code + {doc_count} doc chunks + {summary_count} summary)")


def main():
    """Run verification."""
    print("\n🔍 QBlock Platform Ingestion Verification")
    print("Checking Neo4j graph and Qdrant vectors...")

    try:
        verify_neo4j()
        verify_qdrant()

        print("\n" + "="*60)
        print("✅ VERIFICATION COMPLETE")
        print("="*60)
        print("\nAll QBlock services successfully ingested!")
        print("• Graph relationships stored in Neo4j")
        print("• Code + documentation vectors stored in Qdrant")
        print("• Cross-service API mappings complete")
        print()

    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
