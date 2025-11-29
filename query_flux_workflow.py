#!/usr/bin/env python3
"""
Query Flux documentation workflow using Graph + Vector + LLM.

This demonstrates the complete RAG pipeline:
1. Query Neo4j graph for workflow structure
2. Retrieve relevant content from Qdrant
3. Send to LLM for intelligent summarization
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

# Add flowrag to path
sys.path.insert(0, str(Path(__file__).parent / 'flowrag-master'))

from databases.neo4j import get_neo4j_client
from databases.qdrant import get_qdrant_client
from config.settings import get_settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class FluxWorkflowQuery:
    """Query system for Flux documentation using Graph + Vector + LLM."""

    def __init__(self):
        """Initialize query system."""
        self.neo4j_client = None
        self.qdrant_client = None
        self.openai_client = None

        # Initialize clients
        self._init_clients()

    def _init_clients(self):
        """Initialize database and LLM clients."""
        print("🔌 Connecting to databases...")

        # Load settings (auto-loads from .env file)
        settings = get_settings()

        # Neo4j
        try:
            self.neo4j_client = get_neo4j_client()
            print("   ✅ Neo4j connected")
        except Exception as e:
            print(f"   ⚠️  Neo4j connection failed: {e}")

        # Qdrant
        try:
            self.qdrant_client = get_qdrant_client()
            print("   ✅ Qdrant connected")
        except Exception as e:
            print(f"   ⚠️  Qdrant connection failed: {e}")

        # OpenAI (using settings from .env file)
        try:
            if OpenAI and settings.openai_api_key:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                print("   ✅ OpenAI connected")
            else:
                print("   ⚠️  OpenAI not available (check OPENAI_API_KEY in .env)")
        except Exception as e:
            print(f"   ⚠️  OpenAI initialization failed: {e}")

    def get_workflow_from_graph(
        self,
        namespace: str = "flux_guide",
        start_step: int = 1,
        max_steps: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get workflow steps from Neo4j graph.

        Args:
            namespace: Document namespace
            start_step: Starting step number
            max_steps: Maximum steps to retrieve

        Returns:
            List of step dictionaries
        """
        print(f"\n📊 Querying Neo4j graph...")
        print(f"   Namespace: {namespace}")
        print(f"   Steps: {start_step} to {start_step + max_steps - 1}")

        if not self.neo4j_client:
            print("   ❌ Neo4j not connected")
            return []

        # Query for workflow steps
        query = """
        MATCH path = (start:Document {namespace: $namespace, step_number: $start_step})-[:NEXT_STEP*0..]->(step)
        WHERE start.is_procedure = true AND step.is_procedure = true
        WITH step
        ORDER BY step.step_number
        LIMIT $max_steps
        RETURN
            step.id as id,
            step.step_number as step_number,
            step.title as title,
            step.content as content,
            step.page_number as page_number
        """

        try:
            results = self.neo4j_client.execute_query(
                query,
                parameters={
                    'namespace': namespace,
                    'start_step': start_step,
                    'max_steps': max_steps,
                }
            )

            print(f"   ✅ Retrieved {len(results)} steps from graph")
            return results

        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            return []

    def search_qdrant(
        self,
        query_text: str,
        collection_name: str = "flux_documentation",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search Qdrant vector store for relevant content.

        Args:
            query_text: Search query
            collection_name: Qdrant collection name
            limit: Number of results

        Returns:
            List of relevant documents
        """
        print(f"\n🔍 Searching Qdrant vector store...")
        print(f"   Query: {query_text[:60]}...")
        print(f"   Collection: {collection_name}")

        if not self.qdrant_client:
            print("   ⚠️  Qdrant not connected - skipping search")
            return []

        if not self.openai_client:
            print("   ⚠️  OpenAI not available - cannot create query embedding")
            return []

        try:
            # Create embedding for query
            response = self.openai_client.embeddings.create(
                input=[query_text],
                model="text-embedding-3-small"
            )
            query_vector = response.data[0].embedding

            # Search with embedding vector
            results = self.qdrant_client.search(
                query_vector=query_vector,
                namespace="flux_guide",
                top_k=limit,
                collection_name=collection_name,
            )

            print(f"   ✅ Found {len(results)} relevant documents")
            return results

        except Exception as e:
            print(f"   ⚠️  Qdrant search failed: {e}")
            return []

    def summarize_with_llm(
        self,
        workflow_steps: List[Dict[str, Any]],
        context_docs: List[Dict[str, Any]] = None,
        question: str = None,
    ) -> str:
        """
        Summarize workflow using LLM.

        Args:
            workflow_steps: Steps from Neo4j
            context_docs: Additional context from Qdrant
            question: Optional user question

        Returns:
            LLM-generated summary
        """
        print(f"\n🤖 Generating summary with LLM...")

        if not self.openai_client:
            print("   ⚠️  OpenAI not available")
            return self._fallback_summary(workflow_steps)

        # Build prompt
        prompt = self._build_prompt(workflow_steps, context_docs, question)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that explains technical workflows clearly and concisely."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            summary = response.choices[0].message.content
            print(f"   ✅ Summary generated ({len(summary)} chars)")
            return summary

        except Exception as e:
            print(f"   ❌ LLM failed: {e}")
            return self._fallback_summary(workflow_steps)

    def _build_prompt(
        self,
        workflow_steps: List[Dict[str, Any]],
        context_docs: List[Dict[str, Any]],
        question: str,
    ) -> str:
        """Build prompt for LLM."""
        parts = []

        # Add workflow steps
        parts.append("# Workflow Steps\n")
        for step in workflow_steps:
            parts.append(f"## Step {step['step_number']}: {step['title']}")
            parts.append(f"{step['content']}\n")

        # Add context if available
        if context_docs:
            parts.append("\n# Additional Context from Documentation\n")
            for i, doc in enumerate(context_docs, 1):
                metadata = doc.get('metadata', {})
                content = metadata.get('content', doc.get('content', doc.get('text', '')))
                title = metadata.get('title', '')
                page = metadata.get('page_number', '?')

                parts.append(f"\n## Context {i} (Page {page}): {title}")
                parts.append(f"{content}\n")

        # Add question
        if question:
            parts.append(f"\n# User Question\n{question}\n")
            # Check if user wants all steps enumerated
            if any(keyword in question.lower() for keyword in ['list all', 'all steps', 'list down all', 'enumerate all']):
                parts.append(f"\nPlease list out ALL {len(workflow_steps)} workflow steps individually, maintaining their original step numbers and details. Do not summarize or group them.")
            else:
                parts.append("\nPlease provide a clear, concise answer to the user's question based on the workflow steps above.")
        else:
            parts.append("\nPlease summarize this workflow in a clear, step-by-step format. Highlight key actions and any important prerequisites.")

        return "\n".join(parts)

    def _fallback_summary(self, workflow_steps: List[Dict[str, Any]]) -> str:
        """Generate simple summary without LLM."""
        lines = ["# Workflow Summary\n"]

        for step in workflow_steps:
            lines.append(f"**Step {step['step_number']}:** {step['title']}")
            content = step['content'][:150]
            lines.append(f"   {content}...\n")

        return "\n".join(lines)

    def _generate_from_qdrant_only(self, context_docs: List[Dict[str, Any]], question: str) -> str:
        """Generate answer using only Qdrant context when Neo4j is unavailable."""
        print(f"\n🤖 Generating answer from Qdrant context only...")

        if not self.openai_client:
            # Fallback without LLM
            lines = ["# Answer from Documentation\n"]
            for i, doc in enumerate(context_docs, 1):
                metadata = doc.get('metadata', {})
                content = metadata.get('content', doc.get('content', doc.get('text', '')))
                lines.append(f"\n## Context {i}")
                lines.append(content[:300] + "..." if len(content) > 300 else content)
            return "\n".join(lines)

        # Build prompt from Qdrant context
        parts = []
        parts.append("# Relevant Documentation\n")
        for i, doc in enumerate(context_docs, 1):
            metadata = doc.get('metadata', {})
            content = metadata.get('content', doc.get('content', doc.get('text', '')))
            page = metadata.get('page_number', 'unknown')
            title = metadata.get('title', '')
            parts.append(f"\n## Document {i} (Page {page}): {title}")
            parts.append(content)

        parts.append(f"\n# User Question\n{question}\n")
        parts.append("\nPlease provide a clear, detailed answer based on the documentation above.")

        prompt = "\n".join(parts)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided documentation. Be clear, concise, and accurate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            summary = response.choices[0].message.content
            print(f"   ✅ Answer generated from {len(context_docs)} Qdrant documents")
            return summary

        except Exception as e:
            print(f"   ❌ LLM failed: {e}")
            # Simple fallback
            lines = ["# Answer from Documentation\n"]
            for i, doc in enumerate(context_docs, 1):
                content = doc.get('content', doc.get('text', ''))
                lines.append(f"\n## Context {i}")
                lines.append(content[:300] + "..." if len(content) > 300 else content)
            return "\n".join(lines)

    def query(
        self,
        question: str = None,
        start_step: int = 1,
        max_steps: int = 10,
        use_qdrant: bool = True,
    ) -> Dict[str, Any]:
        """
        Main query method - orchestrates Graph + Vector + LLM.

        Args:
            question: Optional user question
            start_step: Starting step number
            max_steps: Maximum steps to retrieve
            use_qdrant: Whether to use Qdrant for additional context

        Returns:
            Dictionary with results
        """
        print("=" * 80)
        print("🔍 Flux Workflow Query - Graph + Vector + LLM")
        print("=" * 80)

        if question:
            print(f"\n❓ Question: {question}")

        # 1. Get workflow from graph
        workflow_steps = self.get_workflow_from_graph(
            start_step=start_step,
            max_steps=max_steps,
        )

        # 2. Search Qdrant for context (required if Neo4j failed, optional otherwise)
        context_docs = []
        if use_qdrant and question and (not workflow_steps or use_qdrant):
            context_docs = self.search_qdrant(
                query_text=question,
                limit=10 if not workflow_steps else 10,  # Increased from 3 to 10 for better context
            )

        # If no workflow steps from Neo4j, try to use Qdrant results only
        if not workflow_steps:
            if context_docs:
                print("\n⚠️  No workflow steps from Neo4j, using Qdrant results only")
                # Generate answer from Qdrant context only
                summary = self._generate_from_qdrant_only(context_docs, question)
                return {
                    'workflow_steps': [],
                    'context_docs': context_docs,
                    'summary': summary,
                }
            else:
                print("\n❌ No data available from either Neo4j or Qdrant")
                return {'error': 'No workflow steps found and no Qdrant results available'}

        # 3. Generate summary with LLM
        summary = self.summarize_with_llm(
            workflow_steps=workflow_steps,
            context_docs=context_docs,
            question=question,
        )

        # Return results
        return {
            'workflow_steps': workflow_steps,
            'context_docs': context_docs,
            'summary': summary,
        }


def demo_queries():
    """Run demo queries."""
    print("=" * 80)
    print("FlowRAG - Complete RAG Pipeline Demo")
    print("Graph (Neo4j) + Vector (Qdrant) + LLM (OpenAI)")
    print("=" * 80)

    # Initialize query system
    query_system = FluxWorkflowQuery()

    # Demo 1: Get workflow summary
    print("\n" + "=" * 80)
    print("Demo 1: Summarize first 5 steps of Flux setup")
    print("=" * 80)

    result1 = query_system.query(
        start_step=1,
        max_steps=5,
        use_qdrant=False,
    )

    print("\n📝 Summary:")
    print("-" * 80)
    print(result1['summary'])

    # Demo 2: Answer specific question
    print("\n" + "=" * 80)
    print("Demo 2: Answer specific question about setup")
    print("=" * 80)

    result2 = query_system.query(
        question="What are the prerequisites before setting up a Flux node?",
        start_step=1,
        max_steps=10,
        use_qdrant=True,
    )

    print("\n📝 Answer:")
    print("-" * 80)
    print(result2['summary'])

    # Demo 3: Get specific workflow section
    print("\n" + "=" * 80)
    print("Demo 3: Configuration steps (steps 5-10)")
    print("=" * 80)

    result3 = query_system.query(
        start_step=5,
        max_steps=5,
        use_qdrant=False,
    )

    print("\n📝 Summary:")
    print("-" * 80)
    print(result3['summary'])

    # Show statistics
    print("\n" + "=" * 80)
    print("📊 Query Statistics")
    print("=" * 80)

    total_steps = len(result1['workflow_steps']) + len(result2['workflow_steps']) + len(result3['workflow_steps'])
    print(f"\nTotal steps retrieved: {total_steps}")
    print(f"Qdrant searches: {1 if result2['context_docs'] else 0}")
    print(f"LLM summaries generated: 3")


def interactive_query():
    """Interactive query mode."""
    print("=" * 80)
    print("🤖 Interactive FlowRAG Query")
    print("=" * 80)
    print("\nAsk questions about the Flux setup workflow!")
    print("Type 'quit' to exit\n")

    query_system = FluxWorkflowQuery()

    while True:
        question = input("❓ Your question: ").strip()

        if question.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break

        if not question:
            continue

        # Query
        result = query_system.query(
            question=question,
            start_step=1,
            max_steps=15,
            use_qdrant=True,
        )

        # Show answer
        print("\n" + "=" * 80)
        print("📝 Answer:")
        print("=" * 80)
        print(result['summary'])
        print("\n" + "=" * 80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Query Flux documentation using Graph + Vector + LLM"
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo queries'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive query mode'
    )
    parser.add_argument(
        '--question',
        type=str,
        help='Single question to answer'
    )
    parser.add_argument(
        '--steps',
        type=int,
        default=10,
        help='Number of steps to retrieve (default: 10)'
    )

    args = parser.parse_args()

    if args.interactive:
        interactive_query()
    elif args.demo:
        demo_queries()
    elif args.question:
        query_system = FluxWorkflowQuery()
        result = query_system.query(
            question=args.question,
            max_steps=args.steps,
            use_qdrant=True,
        )
        print("\n" + "=" * 80)
        print("📝 Answer:")
        print("=" * 80)
        if 'summary' in result:
            print(result['summary'])
        elif 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("❌ Unknown error occurred")
    else:
        # Default: run demo
        demo_queries()


if __name__ == "__main__":
    main()
