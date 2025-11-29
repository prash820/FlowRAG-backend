#!/usr/bin/env python3
"""
Query overall platform flow and architecture.
Analyzes cross-service relationships and data flows.
"""

import sys
import os

# Add flowrag-master to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from databases import get_neo4j_client, get_qdrant_client
from ingestion.embeddings import get_embedding_service
from openai import OpenAI
from config import get_settings


def query_platform_architecture(question: str, platform_name: str = "QBlock"):
    """
    Query the overall platform architecture and flow.

    Args:
        question: User's question about the platform
        platform_name: Name of the platform
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING {platform_name.upper()} PLATFORM ARCHITECTURE")
    print(f"{'='*80}\n")
    print(f"Question: {question}\n")

    neo4j_client = get_neo4j_client()
    qdrant_client = get_qdrant_client()
    embedding_service = get_embedding_service()
    settings = get_settings()

    # Data collection
    context_data = {
        'all_services': [],
        'cross_service_calls': [],
        'service_docs': [],
        'architecture_summary': None
    }

    # ===================================================================
    # STEP 1: Get All Services and Their Documentation
    # ===================================================================
    print("📊 STEP 1: Discovering all services in the platform...")
    print("-" * 80)

    # Get all namespaces (services)
    query = """
    MATCH (n)
    WHERE n.namespace IS NOT NULL
    RETURN DISTINCT n.namespace as namespace, count(n) as node_count
    ORDER BY node_count DESC
    """
    services = neo4j_client.execute_query(query)

    print(f"\n✓ Found {len(services)} services:\n")
    for svc in services:
        print(f"  • {svc['namespace']}: {svc['node_count']} components")
        context_data['all_services'].append({
            'namespace': svc['namespace'],
            'node_count': svc['node_count']
        })

    # Get documentation for each service
    print(f"\n📚 Retrieving service documentation...")
    for svc in services:
        namespace = svc['namespace']

        # Search for documentation in Qdrant
        query_text = f"What does {namespace} service do?"
        query_embedding = embedding_service.generate_embeddings([query_text])[0]

        doc_results = qdrant_client.search(
            query_vector=query_embedding,
            namespace=namespace,
            top_k=1,
            filters={"type": "documentation"}
        )

        if doc_results:
            metadata = doc_results[0]['metadata']
            context_data['service_docs'].append({
                'namespace': namespace,
                'service_name': metadata.get('service_name', namespace),
                'description': metadata.get('description', 'N/A'),
                'responsibilities': metadata.get('responsibilities', [])
            })

    # ===================================================================
    # STEP 2: Analyze Cross-Service Relationships
    # ===================================================================
    print(f"\n🔗 STEP 2: Analyzing cross-service communication...")
    print("-" * 80)

    # Get all cross-service API calls
    query = """
    MATCH (caller)-[r:CALLS_API]->(callee)
    WHERE caller.namespace <> callee.namespace
    RETURN caller.namespace as from_service,
           callee.namespace as to_service,
           caller.name as from_component,
           callee.name as to_component,
           count(r) as call_count
    ORDER BY call_count DESC
    """
    cross_service_calls = neo4j_client.execute_query(query)

    if cross_service_calls:
        print(f"\n✓ Found {len(cross_service_calls)} cross-service API call patterns:\n")
        for call in cross_service_calls:
            print(f"  • {call['from_service']} → {call['to_service']}")
            print(f"    {call['from_component']} calls {call['to_component']} ({call['call_count']} times)")

            context_data['cross_service_calls'].append({
                'from_service': call['from_service'],
                'to_service': call['to_service'],
                'from_component': call['from_component'],
                'to_component': call['to_component'],
                'call_count': call['call_count']
            })
    else:
        print("⚠ No cross-service calls found")

    # ===================================================================
    # STEP 3: Analyze Service Dependencies
    # ===================================================================
    print(f"\n🌐 STEP 3: Building service dependency graph...")
    print("-" * 80)

    # Get service interaction summary
    query = """
    MATCH (n1)-[r:CALLS_API]-(n2)
    WHERE n1.namespace <> n2.namespace
    WITH n1.namespace as service, n2.namespace as connected_service,
         CASE WHEN startNode(r) = n1 THEN 'depends_on' ELSE 'serves' END as relationship_type,
         count(r) as interactions
    RETURN service, connected_service, relationship_type, interactions
    ORDER BY service, interactions DESC
    """
    dependencies = neo4j_client.execute_query(query)

    # Build dependency map
    service_map = {}
    for dep in dependencies:
        svc = dep['service']
        if svc not in service_map:
            service_map[svc] = {'depends_on': [], 'serves': []}

        rel_type = dep['relationship_type']
        service_map[svc][rel_type].append({
            'service': dep['connected_service'],
            'interactions': dep['interactions']
        })

    print("\n📊 Service dependency summary:\n")
    for svc, deps in service_map.items():
        print(f"  {svc}:")
        if deps['serves']:
            print(f"    ↙ Serves: {', '.join([d['service'] for d in deps['serves']])}")
        if deps['depends_on']:
            print(f"    ↗ Depends on: {', '.join([d['service'] for d in deps['depends_on']])}")

    # ===================================================================
    # STEP 4: Identify Service Roles
    # ===================================================================
    print(f"\n🎭 STEP 4: Identifying service roles in architecture...")
    print("-" * 80)

    service_roles = {}
    for svc, deps in service_map.items():
        if deps['serves'] and not deps['depends_on']:
            role = "Leaf Service (provides data/functionality)"
        elif deps['depends_on'] and not deps['serves']:
            role = "Entry Point (initiates requests)"
        elif deps['serves'] and deps['depends_on']:
            role = "Middleware/Orchestrator (both provides and consumes)"
        else:
            role = "Standalone Service"

        service_roles[svc] = role

    print("\n✓ Service roles identified:\n")
    for svc, role in service_roles.items():
        print(f"  • {svc}: {role}")

    # ===================================================================
    # STEP 5: Generate Platform Flow Diagram (Mermaid)
    # ===================================================================
    print(f"\n📈 STEP 5: Generating architecture flow diagram...")
    print("-" * 80)

    mermaid_diagram = "graph TD\n"

    # Add nodes
    for svc in context_data['all_services']:
        namespace = svc['namespace']
        # Sanitize namespace for mermaid
        node_id = namespace.replace('-', '_').replace('.', '_')
        mermaid_diagram += f"    {node_id}[{namespace}]\n"

    # Add edges
    for call in context_data['cross_service_calls']:
        from_id = call['from_service'].replace('-', '_').replace('.', '_')
        to_id = call['to_service'].replace('-', '_').replace('.', '_')
        mermaid_diagram += f"    {from_id} -->|{call['call_count']} calls| {to_id}\n"

    print(f"\n✓ Architecture diagram generated (Mermaid format):\n")
    print("```mermaid")
    print(mermaid_diagram)
    print("```\n")

    # ===================================================================
    # STEP 6: LLM Synthesis
    # ===================================================================
    print(f"\n🤖 STEP 6: Synthesizing comprehensive answer with LLM...")
    print("-" * 80)

    # Build context for LLM
    context_parts = []

    # Add service overview
    services_list = "\n".join([
        f"  - {doc['namespace']}: {doc['description']}"
        for doc in context_data['service_docs']
    ])
    context_parts.append(f"PLATFORM SERVICES ({len(context_data['all_services'])} total):\n{services_list}")

    # Add service responsibilities
    responsibilities_text = ""
    for doc in context_data['service_docs']:
        if doc['responsibilities']:
            resp_list = '\n    '.join([f"• {r}" for r in doc['responsibilities']])
            responsibilities_text += f"\n{doc['namespace']}:\n    {resp_list}\n"

    if responsibilities_text:
        context_parts.append(f"SERVICE RESPONSIBILITIES:\n{responsibilities_text}")

    # Add cross-service calls
    if context_data['cross_service_calls']:
        calls_text = "\n".join([
            f"  - {call['from_service']} → {call['to_service']}: {call['from_component']} calls {call['to_component']}"
            for call in context_data['cross_service_calls']
        ])
        context_parts.append(f"CROSS-SERVICE API CALLS:\n{calls_text}")

    # Add service roles
    roles_text = "\n".join([f"  - {svc}: {role}" for svc, role in service_roles.items()])
    context_parts.append(f"SERVICE ROLES:\n{roles_text}")

    # Add dependency graph
    deps_text = ""
    for svc, deps in service_map.items():
        deps_text += f"\n{svc}:\n"
        if deps['serves']:
            deps_text += f"  Serves: {', '.join([d['service'] for d in deps['serves']])}\n"
        if deps['depends_on']:
            deps_text += f"  Depends on: {', '.join([d['service'] for d in deps['depends_on']])}\n"
    context_parts.append(f"SERVICE DEPENDENCIES:{deps_text}")

    # Add mermaid diagram
    context_parts.append(f"ARCHITECTURE DIAGRAM (Mermaid):\n{mermaid_diagram}")

    context_str = "\n\n" + "="*80 + "\n\n".join(context_parts)

    # Create LLM prompt
    prompt = f"""You are a software architecture expert analyzing a microservices platform. Answer the user's question about the overall platform architecture and flow based on the provided context from graph database analysis and service documentation.

USER QUESTION:
{question}

PLATFORM CONTEXT:
{context_str}

INSTRUCTIONS:
1. Provide a comprehensive answer explaining the overall platform architecture
2. Describe the data/request flow through the system
3. Explain how different services work together
4. Identify key integration points and communication patterns
5. Highlight the role of each service in the overall flow
6. Use the service dependencies to explain the architecture layers
7. Be specific about API calls and service interactions
8. Format your answer in a clear, well-structured way with sections
9. Include insights about the architecture patterns being used

ANSWER:"""

    # Call LLM
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a software architecture expert helping developers understand complex microservice architectures and data flows."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        llm_answer = response.choices[0].message.content

        print(f"\n{'='*80}")
        print("📋 LLM-SYNTHESIZED ANSWER")
        print(f"{'='*80}\n")
        print(llm_answer)
        print(f"\n{'='*80}\n")

        # Also print the mermaid diagram at the end
        print("📊 ARCHITECTURE VISUALIZATION")
        print(f"{'='*80}\n")
        print("Copy this Mermaid diagram to visualize the architecture:")
        print("(Use https://mermaid.live or GitHub markdown)\n")
        print("```mermaid")
        print(mermaid_diagram)
        print("```\n")
        print(f"{'='*80}\n")

    except Exception as e:
        print(f"❌ Error generating LLM synthesis: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: ./query_platform_flow.py \"<your question>\"")
        print("\nExamples:")
        print("  ./query_platform_flow.py \"What is the overall flow for QBlock?\"")
        print("  ./query_platform_flow.py \"How do the services work together?\"")
        print("  ./query_platform_flow.py \"Explain the QBlock architecture\"")
        sys.exit(1)

    question = sys.argv[1]
    query_platform_architecture(question)


if __name__ == "__main__":
    main()
