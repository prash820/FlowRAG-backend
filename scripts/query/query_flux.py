"""
Demo script to query the ingested Flux Light Node workflow
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config import get_settings

settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key)
qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)

def semantic_search(query: str, limit: int = 5):
    """Perform semantic search on Flux workflow."""
    print(f"\n🔍 Searching: '{query}'\n")

    # Create query embedding
    embedding_response = openai_client.embeddings.create(
        model=settings.openai_embedding_model,
        input=query
    )
    query_embedding = embedding_response.data[0].embedding

    # Search Qdrant with namespace filter (using legacy search method for Qdrant 1.7.4)
    results = qdrant_client.search(
        collection_name="flux_documents",
        query_vector=query_embedding,
        limit=limit,
        query_filter=Filter(
            must=[FieldCondition(key="namespace", match=MatchValue(value="flux_setup_guide"))]
        )
    )

    print(f"📊 Found {len(results)} relevant steps:\n")

    for i, result in enumerate(results, 1):
        payload = result.payload
        print(f"{i}. {payload['name']} (Score: {result.score:.3f})")
        print(f"   Phase: {payload.get('phase', 'N/A')}")
        print(f"   Description: {payload['description'][:100]}...")
        print(f"   Estimated Time: {payload.get('estimated_time', 'N/A')}")
        if payload.get('dependencies'):
            print(f"   Dependencies: {', '.join(payload['dependencies'])}")
        print()

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "How do I set up a Flux light node?"
    semantic_search(query)
