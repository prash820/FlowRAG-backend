"""
Demo script showing FlowRAG's unique capability:
Combining semantic search with workflow flow analysis
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from databases.neo4j.client import Neo4jClient
from config import get_settings

settings = get_settings()
openai_client = OpenAI(api_key=settings.openai_api_key)
qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False)
neo4j_client = Neo4jClient()

def query_with_flow_context(query: str):
    """
    Perform semantic search, then enrich results with workflow flow context.
    This demonstrates FlowRAG's key advantage: understanding both WHAT and HOW.
    """
    print(f"\n🔍 Query: '{query}'\n")
    print("=" * 80)

    # Step 1: Semantic search to find relevant steps
    print("\n📊 Step 1: Semantic Search (WHAT is relevant)\n")
    embedding_response = openai_client.embeddings.create(
        model=settings.openai_embedding_model,
        input=query
    )
    query_embedding = embedding_response.data[0].embedding

    results = qdrant_client.search(
        collection_name="flux_documents",
        query_vector=query_embedding,
        limit=3,
        query_filter=Filter(
            must=[FieldCondition(key="namespace", match=MatchValue(value="flux_setup_guide"))]
        )
    )

    print(f"Found {len(results)} relevant steps:\n")
    relevant_step_ids = []
    for i, result in enumerate(results, 1):
        payload = result.payload
        relevant_step_ids.append(payload['step_id'])
        print(f"{i}. {payload['name']} (Score: {result.score:.3f})")
        print(f"   {payload['description'][:80]}...")
        print()

    # Step 2: For each relevant step, get workflow flow context
    print("=" * 80)
    print("\n🔗 Step 2: Workflow Flow Analysis (HOW to execute)\n")

    for step_id in relevant_step_ids[:2]:  # Analyze top 2 results
        # Get step details and dependencies
        flow_query = """
        MATCH (s:Step {namespace: 'flux_setup_guide', id: $step_id})
        OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Step)
        OPTIONAL MATCH (s)-[:PARALLEL_WITH]->(par:Step)
        OPTIONAL MATCH (s)<-[:DEPENDS_ON]-(next:Step)
        OPTIONAL MATCH (p:Phase)-[:CONTAINS]->(s)
        RETURN
            s.name as step,
            s.description as description,
            s.estimated_time as time,
            p.name as phase,
            collect(DISTINCT dep.name) as dependencies,
            collect(DISTINCT par.name) as parallel_steps,
            collect(DISTINCT next.name) as next_steps
        """

        flow_data = neo4j_client.execute_query(flow_query, {"step_id": step_id})[0]

        print(f"📌 {flow_data['step']}")
        print(f"   Phase: {flow_data['phase']}")
        print(f"   Time: {flow_data['time']}")

        if flow_data['dependencies'] and flow_data['dependencies'][0]:
            print(f"   ⚠️  Prerequisites:")
            for dep in flow_data['dependencies']:
                if dep:
                    print(f"      • {dep}")

        if flow_data['parallel_steps'] and flow_data['parallel_steps'][0]:
            print(f"   ⚡ Can run in parallel with:")
            for par in flow_data['parallel_steps']:
                if par:
                    print(f"      • {par}")

        if flow_data['next_steps'] and flow_data['next_steps'][0]:
            print(f"   ➡️  Enables next steps:")
            for next_step in flow_data['next_steps']:
                if next_step:
                    print(f"      • {next_step}")
        print()

    # Step 3: Generate LLM-powered explanation
    print("=" * 80)
    print("\n🤖 Step 3: LLM-Powered Explanation\n")

    # Build context from results
    context_parts = []
    for result in results[:2]:
        payload = result.payload
        context_parts.append(
            f"Step: {payload['name']}\n"
            f"Phase: {payload.get('phase', 'N/A')}\n"
            f"Description: {payload['description']}\n"
            f"Time: {payload.get('estimated_time', 'N/A')}"
        )

    context = "\n\n".join(context_parts)

    llm_response = openai_client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": "You are a technical documentation assistant helping users understand workflow procedures. Be concise and practical."
            },
            {
                "role": "user",
                "content": f"Based on this workflow information:\n\n{context}\n\nQuestion: {query}\n\nProvide a clear, actionable answer."
            }
        ],
        temperature=0.3,
        max_tokens=300
    )

    print(llm_response.choices[0].message.content)
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "What steps can I do in parallel?"
    query_with_flow_context(query)
