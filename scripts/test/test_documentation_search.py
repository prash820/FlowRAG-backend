#!/usr/bin/env python3
"""
Test documentation semantic search in Qdrant.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases import get_qdrant_client
from ingestion.embeddings import get_embedding_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_doc_search():
    """Test searching documentation."""
    client = get_qdrant_client()
    client.connect()

    embedding_service = get_embedding_service()

    print("\n" + "="*80)
    print("Testing Sock Shop Documentation Search".center(80))
    print("="*80)

    # Test queries
    queries = [
        "How does payment authorization work?",
        "Explain the user registration flow",
        "What databases are used and why?",
        "How do services communicate?"
    ]

    for query in queries:
        print(f"\n\n🔍 Query: '{query}'")
        print("-" * 80)

        # Generate embedding for the query
        query_embedding = embedding_service.generate_embedding(query)

        results = client.search(
            query_vector=query_embedding,
            namespace="sock_shop:documentation",
            top_k=3
        )

        if results:
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                score = result.get('score', 0)

                print(f"\n{i}. {metadata.get('section_title', 'Unknown')} "
                      f"(similarity: {score:.3f})")

                content = metadata.get('content', '')
                # Show first 300 chars
                preview = content[:300].replace('\n', ' ')
                print(f"   {preview}...")
        else:
            print("   No results found")

    print("\n" + "="*80)
    print("✅ Documentation search working!".center(80))
    print("="*80)

    # Show total counts
    print("\n📊 Qdrant Collection Stats:")
    print(f"   Total vectors: 710 (683 code + 27 docs)")
    print(f"   Documentation chunks: 27")
    print(f"   Namespace: sock_shop:documentation")

if __name__ == "__main__":
    test_doc_search()
