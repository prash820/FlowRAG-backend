#!/usr/bin/env python3
"""
Interactive Query System for FlowRAG

Combines:
1. Qdrant semantic search (documentation + code)
2. Neo4j graph traversal (call relationships)
3. LLM context assembly

Answers complex questions about Sock Shop architecture.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from databases import get_neo4j_client, get_qdrant_client
from ingestion.embeddings import get_embedding_service
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class FlowRAGQuerySystem:
    """Intelligent query system combining all FlowRAG capabilities."""

    def __init__(self):
        """Initialize connections."""
        self.qdrant = get_qdrant_client()
        self.neo4j = get_neo4j_client()
        self.embedding_service = get_embedding_service()

        self.qdrant.connect()
        self.neo4j.connect()

    def query(self, question: str, namespace: str = "sock_shop") -> Dict[str, Any]:
        """
        Answer a complex question using hybrid search.

        Args:
            question: Natural language question
            namespace: Service namespace (default: all services)

        Returns:
            Structured answer with documentation, code, and graph context
        """
        print(f"\n{'='*80}")
        print(f"❓ Question: {question}")
        print(f"{'='*80}\n")

        # Generate query embedding once
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

        # Step 4: Get cross-service flows (if applicable)
        print("🔀 Step 4: Tracing cross-service flows...")
        flow_context = self._trace_service_flows(code_results)

        # Assemble comprehensive answer
        answer = {
            'question': question,
            'documentation': doc_results,
            'code': code_results,
            'call_graph': graph_context,
            'service_flows': flow_context
        }

        self._display_answer(answer)

        return answer

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

        print(f"   Found {len(formatted)} relevant documentation sections\n")
        return formatted

    def _search_code(self, query_embedding: List[float], namespace: str) -> List[Dict[str, Any]]:
        """Search code via Qdrant."""
        # If searching broadly, search each service and combine results
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
            # Sort by score and take top 10
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
                'signature': metadata.get('signature'),
                'code': metadata.get('full_code', ''),
                'service': metadata['namespace'].split(':')[1] if ':' in metadata['namespace'] else 'unknown',
                'score': r['score'],
                'id': metadata.get('original_id')
            })

        # Group by service
        by_service = {}
        for item in formatted:
            service = item['service']
            by_service.setdefault(service, []).append(item)

        print(f"   Found {len(formatted)} relevant code units across {len(by_service)} services\n")
        return formatted

    def _analyze_call_graph(self, code_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze call graph for relevant functions."""
        graph_data = {
            'calls': [],
            'called_by': [],
            'call_chains': []
        }

        for code in code_results[:5]:  # Analyze top 5 functions
            func_id = code.get('id')
            if not func_id:
                continue

            func_name = code['name']

            # What does this function call?
            outgoing_query = """
            MATCH (f {id: $id})-[:CALLS]->(called)
            RETURN called.name as name, called.file_path as file, called.namespace as namespace
            LIMIT 10
            """
            outgoing = self.neo4j.execute_query(outgoing_query, {"id": func_id})

            if outgoing:
                graph_data['calls'].append({
                    'function': func_name,
                    'calls': [{'name': c['name'], 'file': Path(c['file']).name if c['file'] else 'unknown'}
                             for c in outgoing]
                })

            # What calls this function?
            incoming_query = """
            MATCH (caller)-[:CALLS]->(f {id: $id})
            RETURN caller.name as name, caller.file_path as file, caller.namespace as namespace
            LIMIT 10
            """
            incoming = self.neo4j.execute_query(incoming_query, {"id": func_id})

            if incoming:
                graph_data['called_by'].append({
                    'function': func_name,
                    'called_by': [{'name': c['name'], 'file': Path(c['file']).name if c['file'] else 'unknown'}
                                 for c in incoming]
                })

            # Get call chains (2 levels deep)
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
        print(f"   Analyzed {total_relationships} graph relationships\n")

        return graph_data

    def _trace_service_flows(self, code_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Trace cross-service communication flows."""
        flows = []

        # Group by service
        services_involved = set(c['service'] for c in code_results)

        if len(services_involved) > 1:
            # Find cross-service calls
            for code in code_results[:5]:
                func_id = code.get('id')
                if not func_id:
                    continue

                # Find calls to different services
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

        print(f"   Found {len(flows)} cross-service communication flows\n")
        return flows

    def _display_answer(self, answer: Dict[str, Any]):
        """Display comprehensive answer."""
        print(f"\n{'='*80}")
        print("📋 COMPREHENSIVE ANSWER")
        print(f"{'='*80}\n")

        # Documentation context
        if answer['documentation']:
            print("📚 Documentation Context:\n")
            for i, doc in enumerate(answer['documentation'][:3], 1):
                print(f"{i}. {doc['section']} (relevance: {doc['relevance']}, score: {doc['score']:.3f})")
                preview = doc['content'][:300].replace('\n', ' ')
                print(f"   {preview}...\n")

        # Code implementations
        if answer['code']:
            print(f"\n💻 Code Implementations:\n")

            # Group by service
            by_service = {}
            for code in answer['code']:
                service = code['service']
                by_service.setdefault(service, []).append(code)

            for service, codes in sorted(by_service.items()):
                print(f"\n   {service.upper()} Service:")
                for code in codes[:3]:
                    print(f"   • {code['name']} ({code['type']})")
                    print(f"     File: {Path(code['file']).name}:{code['line_start']}")
                    print(f"     Score: {code['score']:.3f}")
                    if code['signature']:
                        sig_preview = code['signature'][:80]
                        print(f"     Signature: {sig_preview}")

        # Call graph relationships
        if answer['call_graph']:
            graph = answer['call_graph']

            if graph['calls']:
                print(f"\n\n📊 Call Graph - What These Functions Call:\n")
                for item in graph['calls'][:3]:
                    print(f"   {item['function']} calls:")
                    for call in item['calls'][:5]:
                        print(f"      → {call['name']} ({call['file']})")

            if graph['called_by']:
                print(f"\n\n📊 Call Graph - What Calls These Functions:\n")
                for item in graph['called_by'][:3]:
                    print(f"   {item['function']} is called by:")
                    for caller in item['called_by'][:5]:
                        print(f"      ← {caller['name']} ({caller['file']})")

            if graph['call_chains']:
                print(f"\n\n📊 Call Chains (execution flows):\n")
                for item in graph['call_chains'][:3]:
                    print(f"   Starting from {item['function']}:")
                    for chain in item['chains'][:3]:
                        print(f"      → {' → '.join(chain)}")

        # Cross-service flows
        if answer['service_flows']:
            print(f"\n\n🔀 Cross-Service Communication:\n")
            for flow in answer['service_flows'][:10]:
                print(f"   {flow['from_service']}.{flow['from_function']}")
                print(f"      → {flow['to_service']}.{flow['to_function']}\n")

        print(f"\n{'='*80}")
        print("✅ Answer complete! Context gathered from:")
        print(f"   • {len(answer['documentation'])} documentation sections")
        print(f"   • {len(answer['code'])} code implementations")
        print(f"   • {len(answer['call_graph'].get('calls', []))} outgoing call relationships")
        print(f"   • {len(answer['call_graph'].get('called_by', []))} incoming call relationships")
        print(f"   • {len(answer['service_flows'])} cross-service flows")
        print(f"{'='*80}\n")


def main():
    """Interactive query interface."""
    print("\n" + "="*80)
    print("FlowRAG Interactive Query System".center(80))
    print("Hybrid Intelligence: Documentation + Code + Graph".center(80))
    print("="*80)

    # Initialize system
    print("\n🔧 Initializing FlowRAG query system...")
    system = FlowRAGQuerySystem()
    print("✅ Ready!\n")

    # Complex example queries
    example_queries = [
        "How does the checkout flow work from cart to payment authorization?",
        "What happens when a user registers and how is their data stored?",
        "Explain the complete order creation process including all service interactions",
        "How does payment authorization work and what functions are involved?",
        "Show me the flow from adding item to cart through to shipping calculation"
    ]

    print("💡 Example complex queries:")
    for i, q in enumerate(example_queries, 1):
        print(f"   {i}. {q}")

    print(f"\n{'='*80}\n")

    # Interactive mode
    while True:
        try:
            print("Enter your question (or 'quit' to exit, 'examples' to see list):")
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

            # Process question
            answer = system.query(question)

            # Ask if user wants more details
            print("\nWould you like to see code details? (y/n): ", end="")
            show_code = input().strip().lower() == 'y'

            if show_code and answer['code']:
                print(f"\n{'='*80}")
                print("📝 CODE DETAILS")
                print(f"{'='*80}\n")

                for i, code in enumerate(answer['code'][:5], 1):
                    print(f"\n{i}. {code['name']} ({code['service']} service)")
                    print(f"   File: {Path(code['file']).name}:{code['line_start']}")
                    if code['code']:
                        print(f"\n   Code:")
                        code_lines = code['code'].split('\n')[:20]
                        for line in code_lines:
                            print(f"   {line}")
                        if len(code['code'].split('\n')) > 20:
                            print(f"   ... (truncated)")
                    print()

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
        system = FlowRAGQuerySystem()
        system.query(question)
    else:
        # Interactive mode
        main()
