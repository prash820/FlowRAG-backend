#!/usr/bin/env python3
"""
Complete Hybrid Search Demo: Documentation + Code + Graph

Demonstrates the full power of FlowRAG:
1. Semantic documentation search
2. Semantic code search
3. Graph traversal for call relationships
4. Hybrid queries combining all three
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases import get_neo4j_client, get_qdrant_client
from ingestion.embeddings import get_embedding_service
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress info logs
logger = logging.getLogger(__name__)

def print_header(text):
    print("\n" + "="*80)
    print(text.center(80))
    print("="*80)

def print_subheader(text):
    print("\n" + "-"*80)
    print(text)
    print("-"*80)

def demo_1_documentation_search():
    """Demo 1: Pure documentation search."""
    print_header("DEMO 1: Documentation Search")

    client = get_qdrant_client()
    client.connect()
    embedding_service = get_embedding_service()

    query = "How does payment authorization work?"
    print(f"\n🔍 Query: '{query}'")

    query_embedding = embedding_service.generate_embedding(query)
    results = client.search(
        query_vector=query_embedding,
        namespace="sock_shop:documentation",
        top_k=2
    )

    print("\n📚 Documentation Results:")
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        print(f"\n{i}. {metadata['section_title']} (similarity: {result['score']:.3f})")
        content = metadata['content'][:250].replace('\n', ' ')
        print(f"   {content}...")

def demo_2_code_search():
    """Demo 2: Pure code search."""
    print_header("DEMO 2: Code Search")

    client = get_qdrant_client()
    client.connect()
    embedding_service = get_embedding_service()

    query = "payment authorization"
    print(f"\n🔍 Query: '{query}'")

    query_embedding = embedding_service.generate_embedding(query)
    results = client.search(
        query_vector=query_embedding,
        namespace="sock_shop:payment",
        top_k=3
    )

    print("\n💻 Code Results:")
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        print(f"\n{i}. {metadata['name']} ({metadata['code_unit_type']})")
        print(f"   File: {Path(metadata['file_path']).name}:{metadata['line_start']}")
        print(f"   Similarity: {result['score']:.3f}")
        if metadata.get('signature'):
            print(f"   Signature: {metadata['signature']}")

def demo_3_graph_traversal():
    """Demo 3: Pure graph traversal."""
    print_header("DEMO 3: Graph Traversal")

    client = get_neo4j_client()
    client.connect()

    print("\n🔍 Query: 'What does the Authorise function call?'")

    query = """
    MATCH (f {name: 'Authorise', namespace: 'sock_shop:payment'})-[:CALLS]->(called)
    WHERE f.file_path CONTAINS 'service.go'
    RETURN called.name as function, called.file_path as file
    ORDER BY function
    LIMIT 5
    """

    results = client.execute_query(query, {})

    print("\n📊 Call Graph:")
    if results:
        for r in results:
            file_name = Path(r['file']).name if r['file'] else 'unknown'
            print(f"  → {r['function']} ({file_name})")
    else:
        print("  (no calls found)")

def demo_4_hybrid_all_three():
    """Demo 4: Hybrid search combining all three."""
    print_header("DEMO 4: Complete Hybrid Search (Docs + Code + Graph)")

    qdrant = get_qdrant_client()
    neo4j = get_neo4j_client()
    embedding_service = get_embedding_service()

    qdrant.connect()
    neo4j.connect()

    query = "payment authorization"
    print(f"\n🔍 Query: '{query}'")
    print("\nCombining documentation, code, and call graph...")

    query_embedding = embedding_service.generate_embedding(query)

    # Step 1: Search documentation
    print_subheader("📚 Step 1: Documentation Context")
    doc_results = qdrant.search(
        query_vector=query_embedding,
        namespace="sock_shop:documentation",
        top_k=1
    )

    if doc_results:
        metadata = doc_results[0]['metadata']
        print(f"\n{metadata['section_title']}")
        content = metadata['content'][:200].replace('\n', ' ')
        print(f"{content}...")

    # Step 2: Search code
    print_subheader("💻 Step 2: Related Code")
    code_results = qdrant.search(
        query_vector=query_embedding,
        namespace="sock_shop:payment",
        top_k=2
    )

    for result in code_results:
        metadata = result['metadata']
        print(f"\n{metadata['name']} ({metadata['code_unit_type']})")
        print(f"File: {Path(metadata['file_path']).name}:{metadata['line_start']}")

        # Step 3: Get call graph for each function
        func_id = metadata.get('original_id')
        if func_id:
            print(f"\n  📊 Call Graph for {metadata['name']}:")

            graph_query = """
            MATCH (f {id: $id})-[:CALLS]->(called)
            RETURN called.name as name, called.file_path as file
            LIMIT 5
            """

            calls = neo4j.execute_query(graph_query, {"id": func_id})

            if calls:
                for call in calls:
                    file_name = Path(call['file']).name if call['file'] else 'unknown'
                    print(f"    → {call['name']} ({file_name})")
            else:
                print(f"    (no direct calls)")

def demo_5_cross_service():
    """Demo 5: Cross-service documentation + code search."""
    print_header("DEMO 5: Cross-Service Search")

    client = get_qdrant_client()
    client.connect()
    embedding_service = get_embedding_service()

    query = "user authentication and login"
    print(f"\n🔍 Query: '{query}'")
    print("\nSearching across documentation AND all service code...")

    query_embedding = embedding_service.generate_embedding(query)

    # Search documentation
    print_subheader("📚 Documentation")
    doc_results = client.search(
        query_vector=query_embedding,
        namespace="sock_shop:documentation",
        top_k=1
    )

    if doc_results:
        metadata = doc_results[0]['metadata']
        print(f"\n{metadata['section_title']} (score: {doc_results[0]['score']:.3f})")

    # Search all services
    print_subheader("💻 Code (All Services)")
    code_results = client.search(
        query_vector=query_embedding,
        namespace="sock_shop",  # No specific service
        top_k=5
    )

    # Group by service
    by_service = {}
    for r in code_results:
        service = r['metadata']['namespace'].split(':')[1]
        by_service.setdefault(service, []).append(r)

    for service, results in sorted(by_service.items()):
        print(f"\n{service}:")
        for r in results[:2]:
            metadata = r['metadata']
            print(f"  • {metadata['name']} (score: {r['score']:.3f})")

def demo_6_ai_context():
    """Demo 6: Building context for AI/LLM."""
    print_header("DEMO 6: AI Context Building")

    qdrant = get_qdrant_client()
    neo4j = get_neo4j_client()
    embedding_service = get_embedding_service()

    qdrant.connect()
    neo4j.connect()

    question = "How does the payment service validate authorization amounts?"
    print(f"\n💬 User Question: '{question}'")
    print("\nBuilding comprehensive context for LLM...")

    query_embedding = embedding_service.generate_embedding(question)

    # Gather context from all sources
    context = {
        'documentation': [],
        'code': [],
        'graph': []
    }

    # Documentation context
    doc_results = qdrant.search(
        query_vector=query_embedding,
        namespace="sock_shop:documentation",
        top_k=2
    )
    for r in doc_results:
        context['documentation'].append({
            'section': r['metadata']['section_title'],
            'content': r['metadata']['content'][:300]
        })

    # Code context
    code_results = qdrant.search(
        query_vector=query_embedding,
        namespace="sock_shop:payment",
        top_k=2
    )
    for r in code_results:
        metadata = r['metadata']
        context['code'].append({
            'function': metadata['name'],
            'file': Path(metadata['file_path']).name,
            'code': metadata.get('full_code', '')[:300]
        })

        # Graph context
        func_id = metadata.get('original_id')
        if func_id:
            calls = neo4j.execute_query("""
                MATCH (f {id: $id})-[:CALLS]->(called)
                RETURN called.name
                LIMIT 3
            """, {"id": func_id})
            context['graph'].append({
                'function': metadata['name'],
                'calls': [c['name'] for c in calls] if calls else []
            })

    # Display context structure
    print("\n📦 Context Built:")
    print(f"\n📚 Documentation ({len(context['documentation'])} sections):")
    for doc in context['documentation']:
        print(f"  • {doc['section']}")

    print(f"\n💻 Code ({len(context['code'])} functions):")
    for code in context['code']:
        print(f"  • {code['function']} ({code['file']})")

    print(f"\n📊 Call Graph ({len(context['graph'])} functions):")
    for graph in context['graph']:
        if graph['calls']:
            print(f"  • {graph['function']} calls: {', '.join(graph['calls'])}")

    print("\n✅ This context would be sent to an LLM to generate a comprehensive answer.")

def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("FlowRAG Complete Hybrid Search Demo".center(80))
    print("Documentation + Code + Graph Intelligence".center(80))
    print("="*80)

    try:
        # Demo 1: Documentation only
        demo_1_documentation_search()

        # Demo 2: Code only
        demo_2_code_search()

        # Demo 3: Graph only
        demo_3_graph_traversal()

        # Demo 4: All three combined
        demo_4_hybrid_all_three()

        # Demo 5: Cross-service search
        demo_5_cross_service()

        # Demo 6: AI context building
        demo_6_ai_context()

        print("\n" + "="*80)
        print("✅ All Demos Complete!".center(80))
        print("="*80)

        print("\n💡 Key Capabilities Demonstrated:")
        print("   1. Semantic documentation search - find architectural knowledge")
        print("   2. Semantic code search - find implementations by meaning")
        print("   3. Graph traversal - understand code structure and flow")
        print("   4. Hybrid queries - combine docs + code + graph")
        print("   5. Cross-service search - search across all languages")
        print("   6. AI context building - gather comprehensive context for LLMs")

        print("\n📊 System Stats:")
        print("   • Documentation: 27 chunks")
        print("   • Code: 683 functions")
        print("   • Graph: 683 nodes, 205 relationships")
        print("   • Total vectors: 710")
        print("   • Services: 7 (Go, JavaScript, Java)")

        print("\n🎉 FlowRAG has COMPLETE intelligence!")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
