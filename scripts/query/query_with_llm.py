#!/usr/bin/env python3
"""
FlowRAG Query System with LLM Integration

Combines:
1. Qdrant semantic search (documentation + code)
2. Neo4j graph traversal (call relationships)
3. LLM context assembly and answer generation

Answers complex questions using hybrid intelligence + LLM.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases import get_neo4j_client, get_qdrant_client
from ingestion.embeddings import get_embedding_service
import logging
from typing import Dict, List, Any
import os

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not available - answers will show context only")


class FlowRAGLLMQuerySystem:
    """Intelligent query system with LLM integration."""

    def __init__(self, use_llm: bool = True):
        """Initialize connections."""
        self.qdrant = get_qdrant_client()
        self.neo4j = get_neo4j_client()
        self.embedding_service = get_embedding_service()

        self.qdrant.connect()
        self.neo4j.connect()

        # Initialize LLM if available
        self.use_llm = use_llm and OPENAI_AVAILABLE
        if self.use_llm:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.llm_client = OpenAI(api_key=api_key)
                print("✅ LLM integration enabled (OpenAI)")
            else:
                self.use_llm = False
                print("⚠️  OPENAI_API_KEY not set - showing context only")
        else:
            print("ℹ️  LLM integration disabled - showing context only")

    def query(self, question: str, namespace: str = "sock_shop") -> Dict[str, Any]:
        """
        Answer a complex question using hybrid search + LLM.

        Args:
            question: Natural language question
            namespace: Service namespace (default: all services)

        Returns:
            Structured answer with context and LLM response
        """
        print(f"\n{'='*80}")
        print(f"❓ Question: {question}")
        print(f"{'='*80}\n")

        # Generate query embedding once
        print("🔍 Generating query embedding...")
        query_embedding = self.embedding_service.generate_embedding(question)

        # Step 1: Search documentation
        print("📚 Step 1: Searching documentation...")
        doc_results = self._search_documentation(query_embedding)

        # Step 2: Search code
        print("💻 Step 2: Searching code implementations...")
        code_results = self._search_code(query_embedding, namespace)

        # Step 3: Build call graph context
        print("📊 Step 3: Analyzing call graph relationships...")
        graph_context = self._analyze_call_graph(code_results)

        # Step 4: Get cross-service flows
        print("🔀 Step 4: Tracing cross-service flows...")
        flow_context = self._trace_service_flows(code_results)

        # Assemble comprehensive context
        context = {
            'question': question,
            'documentation': doc_results,
            'code': code_results,
            'call_graph': graph_context,
            'service_flows': flow_context
        }

        # Step 5: Generate LLM answer
        if self.use_llm:
            print("🤖 Step 5: Generating LLM answer from context...\n")
            llm_answer = self._generate_llm_answer(context)
            context['llm_answer'] = llm_answer
        else:
            context['llm_answer'] = None

        # Display results
        self._display_answer(context)

        return context

    def _search_documentation(self, query_embedding: List[float]) -> List[Dict[str, Any]]:
        """Search documentation via Qdrant."""
        results = self.qdrant.search(
            query_vector=query_embedding,
            namespace="sock_shop:documentation",
            top_k=3
        )

        formatted = []
        for r in results:
            metadata = r['metadata']
            formatted.append({
                'section': metadata['section_title'],
                'content': metadata['content'],
                'score': r['score'],
                'relevance': 'high' if r['score'] > 0.5 else 'medium'
            })

        print(f"   Found {len(formatted)} relevant documentation sections")
        return formatted

    def _search_code(self, query_embedding: List[float], namespace: str) -> List[Dict[str, Any]]:
        """Search code via Qdrant."""
        if namespace == "sock_shop":
            all_results = []
            services = ["front-end", "payment", "user", "catalogue", "carts", "orders", "shipping"]
            for service in services:
                try:
                    service_results = self.qdrant.search(
                        query_vector=query_embedding,
                        namespace=f"sock_shop:{service}",
                        top_k=5
                    )
                    all_results.extend(service_results)
                except:
                    continue
            results = sorted(all_results, key=lambda x: x.get('score', 0), reverse=True)[:10]
        else:
            results = self.qdrant.search(
                query_vector=query_embedding,
                namespace=namespace,
                top_k=10
            )

        formatted = []
        for r in results:
            metadata = r['metadata']
            formatted.append({
                'name': metadata['name'],
                'type': metadata.get('code_unit_type', 'unknown'),
                'file': metadata['file_path'],
                'line_start': metadata.get('line_start'),
                'signature': metadata.get('signature', ''),
                'code': metadata.get('full_code', ''),
                'service': metadata['namespace'].split(':')[1] if ':' in metadata['namespace'] else 'unknown',
                'score': r['score'],
                'id': metadata.get('original_id')
            })

        by_service = {}
        for item in formatted:
            by_service.setdefault(item['service'], []).append(item)

        print(f"   Found {len(formatted)} code units across {len(by_service)} services")
        return formatted

    def _analyze_call_graph(self, code_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze call graph for relevant functions."""
        graph_data = {
            'calls': [],
            'called_by': [],
            'call_chains': []
        }

        for code in code_results[:5]:
            func_id = code.get('id')
            if not func_id:
                continue

            func_name = code['name']

            # Outgoing calls
            outgoing_query = """
            MATCH (f {id: $id})-[:CALLS]->(called)
            RETURN called.name as name, called.file_path as file
            LIMIT 10
            """
            outgoing = self.neo4j.execute_query(outgoing_query, {"id": func_id})

            if outgoing:
                graph_data['calls'].append({
                    'function': func_name,
                    'calls': [c['name'] for c in outgoing]
                })

            # Incoming calls
            incoming_query = """
            MATCH (caller)-[:CALLS]->(f {id: $id})
            RETURN caller.name as name
            LIMIT 10
            """
            incoming = self.neo4j.execute_query(incoming_query, {"id": func_id})

            if incoming:
                graph_data['called_by'].append({
                    'function': func_name,
                    'called_by': [c['name'] for c in incoming]
                })

            # Call chains
            chain_query = """
            MATCH path = (f {id: $id})-[:CALLS*1..2]->(downstream)
            RETURN [node in nodes(path) | node.name] as chain
            LIMIT 5
            """
            chains = self.neo4j.execute_query(chain_query, {"id": func_id})

            if chains:
                graph_data['call_chains'].append({
                    'function': func_name,
                    'chains': [c['chain'] for c in chains]
                })

        total_relationships = (len(graph_data['calls']) +
                              len(graph_data['called_by']) +
                              len(graph_data['call_chains']))
        print(f"   Analyzed {total_relationships} graph relationships")

        return graph_data

    def _trace_service_flows(self, code_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trace cross-service communication flows."""
        flows = []
        services_involved = set(c['service'] for c in code_results)

        if len(services_involved) > 1:
            for code in code_results[:5]:
                func_id = code.get('id')
                if not func_id:
                    continue

                cross_service_query = """
                MATCH (source {id: $id})-[:CALLS]->(target)
                WHERE source.namespace <> target.namespace
                RETURN source.name as source_func,
                       source.namespace as source_service,
                       target.name as target_func,
                       target.namespace as target_service
                LIMIT 10
                """

                cross_calls = self.neo4j.execute_query(cross_service_query, {"id": func_id})

                if cross_calls:
                    for call in cross_calls:
                        flows.append({
                            'from_service': call['source_service'].split(':')[1],
                            'from_function': call['source_func'],
                            'to_service': call['target_service'].split(':')[1],
                            'to_function': call['target_func']
                        })

        print(f"   Found {len(flows)} cross-service flows\n")
        return flows

    def _generate_llm_answer(self, context: Dict[str, Any]) -> str:
        """Generate comprehensive answer using LLM with all gathered context."""

        # Build context string for LLM
        context_parts = []

        # Add documentation context
        if context['documentation']:
            context_parts.append("=== DOCUMENTATION CONTEXT ===\n")
            for i, doc in enumerate(context['documentation'], 1):
                context_parts.append(f"{i}. {doc['section']} (relevance: {doc['relevance']})")
                context_parts.append(f"{doc['content'][:1000]}\n")

        # Add code context
        if context['code']:
            context_parts.append("\n=== CODE IMPLEMENTATIONS ===\n")
            by_service = {}
            for code in context['code']:
                by_service.setdefault(code['service'], []).append(code)

            for service, codes in sorted(by_service.items()):
                context_parts.append(f"\n{service.upper()} Service:")
                for code in codes[:3]:
                    context_parts.append(f"\n{code['name']} ({code['type']})")
                    context_parts.append(f"File: {Path(code['file']).name}:{code['line_start']}")
                    if code['signature']:
                        context_parts.append(f"Signature: {code['signature']}")
                    if code['code']:
                        context_parts.append(f"Code:\n{code['code'][:500]}\n")

        # Add call graph context
        graph = context['call_graph']
        if graph['calls'] or graph['called_by'] or graph['call_chains']:
            context_parts.append("\n=== CALL GRAPH RELATIONSHIPS ===\n")

            if graph['calls']:
                context_parts.append("\nFunction Calls:")
                for item in graph['calls'][:3]:
                    calls_str = ", ".join(item['calls'][:5])
                    context_parts.append(f"• {item['function']} calls: {calls_str}")

            if graph['called_by']:
                context_parts.append("\nCalled By:")
                for item in graph['called_by'][:3]:
                    callers_str = ", ".join(item['called_by'][:5])
                    context_parts.append(f"• {item['function']} is called by: {callers_str}")

            if graph['call_chains']:
                context_parts.append("\nExecution Chains:")
                for item in graph['call_chains'][:3]:
                    for chain in item['chains'][:2]:
                        chain_str = " → ".join(chain)
                        context_parts.append(f"• {chain_str}")

        # Add service flow context
        if context['service_flows']:
            context_parts.append("\n=== CROSS-SERVICE COMMUNICATION ===\n")
            for flow in context['service_flows'][:5]:
                context_parts.append(
                    f"• {flow['from_service']}.{flow['from_function']} "
                    f"→ {flow['to_service']}.{flow['to_function']}"
                )

        full_context = "\n".join(context_parts)

        # Create LLM prompt
        prompt = f"""You are a software architecture expert analyzing the Sock Shop microservices application.

Based on the following context gathered from documentation, code implementations, and call graph analysis, provide a comprehensive answer to the user's question.

QUESTION: {context['question']}

CONTEXT:
{full_context}

Please provide a detailed, well-structured answer that:
1. Directly answers the question
2. References specific services, functions, and code locations from the context
3. Explains the flow and relationships between components
4. Includes relevant technical details from the code
5. Is easy to understand for developers

ANSWER:"""

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a software architecture expert specializing in microservices analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )

            answer = response.choices[0].message.content
            return answer

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error generating LLM answer: {e}"

    def _display_answer(self, context: Dict[str, Any]):
        """Display comprehensive answer with LLM response."""
        print(f"\n{'='*80}")
        print("📋 COMPREHENSIVE ANSWER")
        print(f"{'='*80}\n")

        # Show LLM answer if available
        if context.get('llm_answer'):
            print("🤖 LLM GENERATED ANSWER:\n")
            print(context['llm_answer'])
            print(f"\n{'='*80}\n")

        # Show context summary
        print("📚 Context Used:")
        print(f"   • {len(context['documentation'])} documentation sections")
        print(f"   • {len(context['code'])} code implementations")

        if context['code']:
            by_service = {}
            for code in context['code']:
                by_service.setdefault(code['service'], []).append(code)
            print(f"   • Services: {', '.join(sorted(by_service.keys()))}")

        if context['call_graph']:
            graph = context['call_graph']
            print(f"   • {len(graph.get('calls', []))} outgoing call relationships")
            print(f"   • {len(graph.get('called_by', []))} incoming call relationships")
            print(f"   • {len(graph.get('call_chains', []))} execution chains")

        if context['service_flows']:
            print(f"   • {len(context['service_flows'])} cross-service flows")

        # Show top documentation sections
        if context['documentation']:
            print(f"\n📖 Key Documentation Sections:")
            for i, doc in enumerate(context['documentation'][:3], 1):
                print(f"   {i}. {doc['section']} (score: {doc['score']:.3f})")

        # Show top code implementations
        if context['code']:
            print(f"\n💻 Key Code Implementations:")
            for i, code in enumerate(context['code'][:5], 1):
                print(f"   {i}. {code['service']}.{code['name']} ({code['type']}) - score: {code['score']:.3f}")

        # Show call graph highlights
        if context['call_graph']['call_chains']:
            print(f"\n📊 Key Execution Chains:")
            for item in context['call_graph']['call_chains'][:2]:
                for chain in item['chains'][:2]:
                    print(f"   • {' → '.join(chain)}")

        print(f"\n{'='*80}\n")


def main():
    """Interactive query interface with LLM."""
    print("\n" + "="*80)
    print("FlowRAG Query System with LLM Integration".center(80))
    print("Hybrid Intelligence + AI Answer Generation".center(80))
    print("="*80)

    # Initialize system
    print("\n🔧 Initializing FlowRAG with LLM...")
    system = FlowRAGLLMQuerySystem(use_llm=True)
    print("✅ Ready!\n")

    # Complex example queries
    example_queries = [
        "How does the checkout flow work from cart to payment authorization?",
        "What happens when a user registers? Explain the complete authentication flow.",
        "Explain the payment authorization process and which functions are involved.",
        "How do services communicate during order creation?",
        "What is the database architecture and why were those databases chosen?"
    ]

    print("💡 Example queries:")
    for i, q in enumerate(example_queries, 1):
        print(f"   {i}. {q}")

    print(f"\n{'='*80}\n")

    # Interactive mode
    while True:
        try:
            print("Enter your question (or 'quit' to exit, 'examples' for list):")
            question = input("❓ > ").strip()

            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!\n")
                break

            if question.lower() in ['examples', 'ex', 'help']:
                print("\n💡 Example queries:")
                for i, q in enumerate(example_queries, 1):
                    print(f"   {i}. {q}")
                print()
                continue

            if not question:
                continue

            # Process question with LLM
            answer = system.query(question)

            print("\n" + "-"*80 + "\n")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    # If arguments provided, run single query
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        system = FlowRAGLLMQuerySystem(use_llm=True)
        system.query(question)
    else:
        # Interactive mode
        main()
