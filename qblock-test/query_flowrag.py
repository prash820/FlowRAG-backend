#!/usr/bin/env python3
"""
FlowRAG Query Interface
Combines Neo4j graph queries with Qdrant vector search for hybrid RAG
"""

import sys
import os

# Add flowrag-master to path (parent directory)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from databases import get_neo4j_client, get_qdrant_client
from ingestion.embeddings import get_embedding_service
from openai import OpenAI
from config import get_settings


def synthesize_with_llm(question: str, context_data: dict) -> str:
    """
    Use LLM to synthesize graph and vector data into a natural answer.

    Args:
        question: The original user question
        context_data: Dictionary containing graph and vector search results

    Returns:
        LLM-generated answer
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    # Build context from collected data
    context_parts = []

    # Add documentation
    if context_data.get('documentation'):
        doc = context_data['documentation']
        context_parts.append(f"SERVICE DOCUMENTATION:\n{doc}")

    # Add documentation chunks
    if context_data.get('doc_chunks'):
        chunks_text = "\n\n".join([
            f"Section: {chunk.get('section', 'General')}\n{chunk.get('content', '')}"
            for chunk in context_data['doc_chunks']
        ])
        context_parts.append(f"RELEVANT DOCUMENTATION SECTIONS:\n{chunks_text}")

    # Add graph relationships
    if context_data.get('incoming_calls'):
        incoming = "\n".join([
            f"  - {call['caller_service']} → {call['callee_service']}: {call['caller_name']} calls {call['callee_name']}"
            for call in context_data['incoming_calls']
        ])
        context_parts.append(f"INCOMING API CALLS (who depends on this service):\n{incoming}")

    if context_data.get('outgoing_calls'):
        outgoing = "\n".join([
            f"  - {call['caller_service']} → {call['callee_service']}: {call['caller_name']} calls {call['callee_name']}"
            for call in context_data['outgoing_calls']
        ])
        context_parts.append(f"OUTGOING API CALLS (what this service depends on):\n{outgoing}")

    # Add key components
    if context_data.get('components'):
        components = "\n".join([
            f"  - [{comp['type']}] {comp['name']}"
            for comp in context_data['components'][:10]
        ])
        context_parts.append(f"KEY COMPONENTS:\n{components}")

    # Add relevant code
    if context_data.get('code_units'):
        code = "\n".join([
            f"  - {unit.get('unit_type', 'Unknown')}: {unit.get('name', 'Unknown')} (score: {unit.get('score', 0):.3f})\n    File: {unit.get('file_path', 'N/A')}"
            for unit in context_data['code_units'][:5]
        ])
        context_parts.append(f"RELEVANT CODE IMPLEMENTATIONS:\n{code}")

    context_str = "\n\n" + "="*80 + "\n\n".join(context_parts)

    # Create prompt for LLM
    prompt = f"""You are a software architecture expert analyzing a microservices platform. Answer the user's question based on the provided context from both graph database (showing relationships and structure) and vector database (showing semantic similarity and documentation).

USER QUESTION:
{question}

CONTEXT FROM HYBRID GRAPH + VECTOR RAG:
{context_str}

INSTRUCTIONS:
1. Provide a clear, comprehensive answer to the question
2. Explain the service's purpose and role in the overall architecture
3. Describe key responsibilities and integration points
4. Mention specific components and their functions where relevant
5. Use the graph data to explain how this service fits in the microservice flow
6. Use the documentation to explain what the service does
7. Be specific and technical, but clear
8. Format your answer in a well-structured way

ANSWER:"""

    # Call LLM
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a software architecture expert helping developers understand complex microservice architectures."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )

    return response.choices[0].message.content


def query_service_purpose(service_name: str, namespace: str, question: str = ""):
    """
    Query the purpose and role of a service in the microservice architecture.

    Args:
        service_name: Name of the service (e.g., "ShopKeyProvider")
        namespace: Namespace of the service (e.g., "qblock-auth-service")
    """
    print(f"\n{'='*80}")
    print(f"QUERYING: {service_name} ({namespace})")
    print(f"{'='*80}\n")

    neo4j_client = get_neo4j_client()
    qdrant_client = get_qdrant_client()
    embedding_service = get_embedding_service()

    # Data collection for LLM synthesis
    context_data = {
        'documentation': None,
        'doc_chunks': [],
        'incoming_calls': [],
        'outgoing_calls': [],
        'components': [],
        'code_units': [],
        'interactions': []
    }

    # ===================================================================
    # PART 1: Vector Search - Get documentation and semantic context
    # ===================================================================
    print("📚 STEP 1: Retrieving documentation from vector database...")
    print("-" * 80)

    # Query for documentation summary
    query_text = f"What is the purpose and responsibility of {service_name}?"
    query_embedding = embedding_service.generate_embeddings([query_text])[0]

    # Search in the specific namespace
    doc_results = qdrant_client.search(
        query_vector=query_embedding,
        namespace=namespace,
        top_k=10,
        filters={"type": "documentation"}
    )

    if doc_results:
        print(f"\n✓ Found service documentation:\n")
        for result in doc_results:
            metadata = result['metadata']
            print(f"Service: {metadata.get('service_name', 'N/A')}")
            print(f"Description: {metadata.get('description', 'N/A')}")
            print(f"Architecture: {metadata.get('architecture_summary', 'N/A')}")

            responsibilities = metadata.get('responsibilities', [])
            if responsibilities:
                print(f"\nResponsibilities:")
                for resp in responsibilities:
                    print(f"  • {resp}")
            print()

            # Store for LLM
            context_data['documentation'] = f"""Service: {metadata.get('service_name', '')}
Description: {metadata.get('description', '')}
Architecture: {metadata.get('architecture_summary', '')}
Responsibilities: {', '.join(responsibilities)}"""
            break
    else:
        print("⚠ No documentation summary found\n")

    # Search for relevant documentation chunks
    doc_chunk_results = qdrant_client.search(
        query_vector=query_embedding,
        namespace=namespace,
        top_k=5,
        filters={"type": "document"}
    )

    if doc_chunk_results:
        print(f"\n📄 Relevant documentation sections:\n")
        for i, result in enumerate(doc_chunk_results, 1):
            metadata = result['metadata']
            content = metadata.get('content', '')[:300]  # First 300 chars
            section = metadata.get('section_title', 'General')
            print(f"{i}. {section} (score: {result['score']:.3f})")
            print(f"   {content}...\n")

            # Store for LLM
            context_data['doc_chunks'].append({
                'section': section,
                'content': metadata.get('content', ''),
                'score': result['score']
            })

    # ===================================================================
    # PART 2: Graph Analysis - Understand service relationships
    # ===================================================================
    print("\n🔗 STEP 2: Analyzing service relationships in graph database...")
    print("-" * 80)

    # Get incoming API calls (who calls this service?)
    query = """
    MATCH (caller)-[r:CALLS_API]->(callee)
    WHERE callee.namespace = $namespace
    RETURN caller.namespace as caller_service,
           caller.name as caller_name,
           callee.name as callee_name,
           count(r) as call_count
    ORDER BY call_count DESC
    """
    incoming_calls = neo4j_client.execute_query(query, {"namespace": namespace})

    if incoming_calls:
        print(f"\n📥 Incoming API calls (who depends on {service_name}?):\n")
        for call in incoming_calls:
            print(f"  • {call['caller_service']} → {namespace}")
            print(f"    {call['caller_name']} calls {call['callee_name']} ({call['call_count']} times)")
            # Store for LLM
            context_data['incoming_calls'].append({
                'caller_service': call['caller_service'],
                'callee_service': namespace,
                'caller_name': call['caller_name'],
                'callee_name': call['callee_name'],
                'call_count': call['call_count']
            })
    else:
        print(f"\n⚠ No incoming API calls found")

    # Get outgoing API calls (what does this service call?)
    query = """
    MATCH (caller)-[r:CALLS_API]->(callee)
    WHERE caller.namespace = $namespace
    RETURN callee.namespace as callee_service,
           caller.name as caller_name,
           callee.name as callee_name,
           count(r) as call_count
    ORDER BY call_count DESC
    """
    outgoing_calls = neo4j_client.execute_query(query, {"namespace": namespace})

    if outgoing_calls:
        print(f"\n📤 Outgoing API calls (what does {service_name} depend on?):\n")
        for call in outgoing_calls:
            print(f"  • {namespace} → {call['callee_service']}")
            print(f"    {call['caller_name']} calls {call['callee_name']} ({call['call_count']} times)")
            # Store for LLM
            context_data['outgoing_calls'].append({
                'caller_service': namespace,
                'callee_service': call['callee_service'],
                'caller_name': call['caller_name'],
                'callee_name': call['callee_name'],
                'call_count': call['call_count']
            })
    else:
        print(f"\n⚠ No outgoing API calls found")

    # Get key components (classes/functions) in this service
    query = """
    MATCH (n)
    WHERE n.namespace = $namespace
    RETURN n.name as name,
           labels(n)[0] as type,
           n.description as description
    ORDER BY
        CASE
            WHEN labels(n)[0] = 'Class' THEN 1
            WHEN labels(n)[0] = 'Function' THEN 2
            ELSE 3
        END,
        n.name
    LIMIT 10
    """
    components = neo4j_client.execute_query(query, {"namespace": namespace})

    if components:
        print(f"\n🏗️  Key components in {service_name}:\n")
        for comp in components:
            comp_type = comp['type']
            comp_name = comp['name']
            comp_desc = comp['description'] or 'No description'
            print(f"  • [{comp_type}] {comp_name}")
            if comp_desc != 'No description':
                print(f"    {comp_desc[:100]}...")
            # Store for LLM
            context_data['components'].append({
                'type': comp_type,
                'name': comp_name,
                'description': comp_desc
            })

    # ===================================================================
    # PART 3: Semantic Code Search - Find relevant implementations
    # ===================================================================
    print(f"\n💻 STEP 3: Finding relevant code implementations...")
    print("-" * 80)

    # Search for authentication/authorization related code
    auth_query = f"authentication authorization JWT token validation in {service_name}"
    auth_embedding = embedding_service.generate_embeddings([auth_query])[0]

    code_results = qdrant_client.search(
        query_vector=auth_embedding,
        namespace=namespace,
        top_k=5,
        filters={"type": "code"}
    )

    if code_results:
        print(f"\n🔍 Relevant code units:\n")
        for i, result in enumerate(code_results, 1):
            metadata = result['metadata']
            print(f"{i}. {metadata.get('unit_type', 'Unknown')} - {metadata.get('name', 'Unknown')}")
            print(f"   File: {metadata.get('file_path', 'N/A')}")
            print(f"   Score: {result['score']:.3f}")

            desc = metadata.get('description', '')
            if desc:
                print(f"   Description: {desc[:150]}...")
            print()

            # Store for LLM
            context_data['code_units'].append({
                'unit_type': metadata.get('unit_type', 'Unknown'),
                'name': metadata.get('name', 'Unknown'),
                'file_path': metadata.get('file_path', 'N/A'),
                'score': result['score'],
                'description': desc
            })

    # ===================================================================
    # PART 4: Cross-Service Flow Analysis
    # ===================================================================
    print(f"\n🌐 STEP 4: Understanding {service_name} in overall architecture...")
    print("-" * 80)

    # Get all services that interact with this service
    query = """
    MATCH (n1)-[r:CALLS_API]-(n2)
    WHERE n1.namespace = $namespace OR n2.namespace = $namespace
    WITH
        CASE WHEN n1.namespace = $namespace THEN n2.namespace ELSE n1.namespace END as other_service,
        CASE WHEN n1.namespace = $namespace THEN 'outgoing' ELSE 'incoming' END as direction,
        count(r) as interactions
    RETURN other_service, direction, interactions
    ORDER BY interactions DESC
    """
    interactions = neo4j_client.execute_query(query, {"namespace": namespace})

    if interactions:
        print(f"\n🔄 Service interaction summary:\n")
        incoming = [i for i in interactions if i['direction'] == 'incoming']
        outgoing = [i for i in interactions if i['direction'] == 'outgoing']

        if incoming:
            print("  Serves requests from:")
            for i in incoming:
                print(f"    ↘ {i['other_service']} ({i['interactions']} interactions)")

        if outgoing:
            print("\n  Makes requests to:")
            for o in outgoing:
                print(f"    ↗ {o['other_service']} ({o['interactions']} interactions)")

    # ===================================================================
    # PART 5: LLM-Powered Synthesis
    # ===================================================================
    print(f"\n{'='*80}")
    print("🤖 STEP 5: Synthesizing answer with LLM...")
    print(f"{'='*80}\n")

    # Generate comprehensive answer using LLM
    try:
        llm_answer = synthesize_with_llm(question, context_data)

        print(f"\n{'='*80}")
        print("📋 LLM-SYNTHESIZED ANSWER")
        print(f"{'='*80}\n")
        print(llm_answer)
        print(f"\n{'='*80}\n")

    except Exception as e:
        print(f"❌ Error generating LLM synthesis: {e}")
        print("\nFalling back to basic summary...\n")

        print(f"Based on hybrid graph + vector analysis:\n")

        if doc_results:
            doc_meta = doc_results[0]['metadata']
            print(f"🎯 Purpose: {doc_meta.get('description', 'N/A')}\n")

        print(f"🔗 Integration Points:")
        if incoming_calls:
            print(f"  • Serves {len(incoming_calls)} different service(s)")
        if outgoing_calls:
            print(f"  • Depends on {len(outgoing_calls)} different service(s)")

        print(f"\n📦 Components: {len(components)} key classes/functions identified")

        print(f"\n🎭 Role: ", end="")
        if incoming_calls and not outgoing_calls:
            print("Provider service (provides capabilities to others)")
        elif outgoing_calls and not incoming_calls:
            print("Consumer service (consumes from others)")
        elif incoming_calls and outgoing_calls:
            print("Orchestrator service (both provides and consumes)")
        else:
            print("Standalone service")

        print(f"\n{'='*80}\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: ./query_flowrag.py \"<your question>\"")
        print("\nExamples:")
        print("  ./query_flowrag.py \"what is the purpose of ShopKeyProvider?\"")
        print("  ./query_flowrag.py \"how does authentication work?\"")
        sys.exit(1)

    question = sys.argv[1].lower()

    # Parse the question to determine which service
    service_mappings = {
        "shopkeyprovider": ("ShopKeyProvider", "qblock-auth-service"),
        "shop key provider": ("ShopKeyProvider", "qblock-auth-service"),
        "auth": ("ShopKeyProvider", "qblock-auth-service"),
        "authentication": ("ShopKeyProvider", "qblock-auth-service"),
        "labelcreationorchestrator": ("LabelCreationOrchestrator", "qblock-label-service"),
        "label": ("LabelCreationOrchestrator", "qblock-label-service"),
        "shopdataprovider": ("ShopDataProvider", "qblock-shop-data"),
        "shop data": ("ShopDataProvider", "qblock-shop-data"),
        "transactiondataprovider": ("TransactionDataProvider", "qblock-transaction-data"),
        "transaction": ("TransactionDataProvider", "qblock-transaction-data"),
        "ordermanagementsystem": ("OrderManagementSystem", "qblock-mobile"),
        "mobile": ("OrderManagementSystem", "qblock-mobile"),
        "flutter": ("OrderManagementSystem", "qblock-mobile"),
        "metrics": ("MetricsJs", "qblock-metrics"),
    }

    # Find matching service
    service_name = None
    namespace = None

    for keyword, (name, ns) in service_mappings.items():
        if keyword in question:
            service_name = name
            namespace = ns
            break

    if not service_name:
        print("❌ Could not identify service from question.")
        print("Please mention one of: ShopKeyProvider, LabelCreationOrchestrator,")
        print("ShopDataProvider, TransactionDataProvider, OrderManagementSystem, MetricsJs")
        sys.exit(1)

    # Run the query
    query_service_purpose(service_name, namespace, question)


if __name__ == "__main__":
    main()
