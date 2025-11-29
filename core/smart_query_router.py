"""
Smart Query Router for Adaptive RAG Strategy.

This implements the intelligent forking logic that determines:
1. Whether to use graph-based retrieval or vector-only
2. How to combine graph flow with vector context
3. When to perform step-specific retrieval
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass

from databases.neo4j import get_neo4j_client
from databases.qdrant import get_qdrant_client

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class QueryType(Enum):
    """Types of user queries."""
    SIMPLE = "simple"  # "What is X?"
    PROCEDURAL = "procedural"  # "How do I do X?"
    SPECIFIC_STEP = "specific_step"  # "What happens in step 5?"
    COMPARISON = "comparison"  # "Difference between X and Y"
    TROUBLESHOOTING = "troubleshooting"  # "Why is X failing?"


@dataclass
class QueryIntent:
    """Analyzed user query intent."""
    query_type: QueryType
    requires_flow: bool
    target_step: Optional[int]
    keywords: List[str]
    confidence: float


class SmartQueryRouter:
    """
    Routes queries to optimal retrieval strategy based on content and intent.

    This implements your vision:
    - Simple docs → Qdrant only
    - Complex docs with steps → Graph flow + Step-specific Qdrant retrieval
    - Code → Graph (AST/dependencies) + Qdrant (implementation details)
    """

    # Keywords indicating procedural queries
    PROCEDURAL_KEYWORDS = [
        'how to', 'how do i', 'steps', 'setup', 'install', 'configure',
        'guide', 'tutorial', 'walkthrough', 'instructions'
    ]

    # Keywords indicating specific step queries
    STEP_KEYWORDS = [
        'step', 'phase', 'stage', 'part', 'section'
    ]

    def __init__(self):
        """Initialize router with database clients."""
        self.neo4j_client = None
        self.qdrant_client = None
        self.openai_client = None

        try:
            from config.settings import get_settings
            settings = get_settings()

            self.neo4j_client = get_neo4j_client()
            self.qdrant_client = get_qdrant_client()

            if OpenAI and settings.openai_api_key:
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize some clients: {e}")

    def analyze_query(self, question: str) -> QueryIntent:
        """
        Analyze user query to determine intent and retrieval strategy.

        Args:
            question: User's natural language question

        Returns:
            QueryIntent with routing decisions
        """
        question_lower = question.lower()

        # Check for specific step references
        target_step = self._extract_step_number(question)

        # Determine query type
        is_procedural = any(
            keyword in question_lower
            for keyword in self.PROCEDURAL_KEYWORDS
        )

        is_step_specific = target_step is not None or any(
            keyword in question_lower
            for keyword in self.STEP_KEYWORDS
        )

        # Decide query type
        if is_step_specific and target_step:
            query_type = QueryType.SPECIFIC_STEP
            requires_flow = True
            confidence = 0.9
        elif is_procedural:
            query_type = QueryType.PROCEDURAL
            requires_flow = True
            confidence = 0.8
        elif 'difference' in question_lower or 'compare' in question_lower:
            query_type = QueryType.COMPARISON
            requires_flow = False
            confidence = 0.7
        elif any(word in question_lower for word in ['error', 'fail', 'issue', 'problem', 'why']):
            query_type = QueryType.TROUBLESHOOTING
            requires_flow = True
            confidence = 0.75
        else:
            query_type = QueryType.SIMPLE
            requires_flow = False
            confidence = 0.6

        # Extract keywords
        keywords = [word for word in question_lower.split() if len(word) > 4]

        return QueryIntent(
            query_type=query_type,
            requires_flow=requires_flow,
            target_step=target_step,
            keywords=keywords[:5],  # Top 5 keywords
            confidence=confidence
        )

    def route_query(
        self,
        question: str,
        namespace: str,
        content_type: str = "complex_document"
    ) -> Dict[str, Any]:
        """
        Main routing logic - implements your vision for adaptive RAG.

        Strategy Selection:
        1. Simple content → Qdrant-only retrieval
        2. Complex content + simple query → Qdrant with light graph context
        3. Complex content + procedural query → Full graph flow + step-specific Qdrant
        4. Code → AST graph + implementation Qdrant

        Args:
            question: User question
            namespace: Document namespace
            content_type: Type of content (simple_document, complex_document, code)

        Returns:
            Query results with answer
        """
        print("\n" + "=" * 80)
        print("🧠 Smart Query Router - Adaptive RAG Strategy")
        print("=" * 80)

        # Analyze query intent
        intent = self.analyze_query(question)
        print(f"\n📋 Query Analysis:")
        print(f"   Type: {intent.query_type.value}")
        print(f"   Requires Flow: {intent.requires_flow}")
        print(f"   Target Step: {intent.target_step or 'N/A'}")
        print(f"   Confidence: {intent.confidence:.2%}")

        # Route based on content type and intent
        if content_type == "simple_document":
            return self._qdrant_only_retrieval(question, namespace)

        elif content_type == "complex_document" or content_type == "workflow_document":
            if intent.query_type == QueryType.SPECIFIC_STEP and intent.target_step:
                # Your vision: Step-specific retrieval
                return self._step_specific_retrieval(
                    question, namespace, intent.target_step
                )
            elif intent.requires_flow:
                # Full graph flow + targeted Qdrant
                return self._graph_guided_retrieval(
                    question, namespace, intent
                )
            else:
                # Light graph context + Qdrant
                return self._hybrid_retrieval(question, namespace)

        elif content_type == "code":
            return self._code_aware_retrieval(question, namespace)

        else:
            # Default: hybrid retrieval
            return self._hybrid_retrieval(question, namespace)

    def _qdrant_only_retrieval(
        self,
        question: str,
        namespace: str
    ) -> Dict[str, Any]:
        """Simple document retrieval - Qdrant only."""
        print("\n🎯 Strategy: Qdrant-Only Retrieval (Simple Content)")

        # Create query embedding
        response = self.openai_client.embeddings.create(
            input=[question],
            model="text-embedding-3-small"
        )
        query_vector = response.data[0].embedding

        # Search Qdrant
        results = self.qdrant_client.search(
            query_vector=query_vector,
            namespace=namespace,
            top_k=10,
        )

        print(f"   ✅ Retrieved {len(results)} relevant documents")

        # Generate answer
        answer = self._generate_answer(
            question=question,
            context_docs=results,
            workflow_steps=[]
        )

        return {
            'strategy': 'qdrant_only',
            'workflow_steps': [],
            'context_docs': results,
            'answer': answer
        }

    def _step_specific_retrieval(
        self,
        question: str,
        namespace: str,
        target_step: int
    ) -> Dict[str, Any]:
        """
        Your Vision Step 8: Step-specific intelligent retrieval.

        1. Get graph flow from Neo4j
        2. Identify the target step in the flow
        3. Retrieve Qdrant context specific to that step
        4. Send both graph flow AND step-specific context to LLM
        """
        print(f"\n🎯 Strategy: Step-Specific Retrieval (Target: Step {target_step})")

        # 1. Get the full workflow graph
        workflow_steps = self._get_workflow_graph(namespace, start=1, limit=50)
        print(f"   📊 Retrieved {len(workflow_steps)} steps from graph")

        # 2. Find the target step and surrounding context
        target_steps = []
        for i, step in enumerate(workflow_steps):
            step_num = step.get('step_number')
            # Get target step plus 1 before and 1 after for context
            if step_num and (target_step - 1) <= step_num <= (target_step + 1):
                target_steps.append(step)

        print(f"   🔍 Focused on {len(target_steps)} steps around Step {target_step}")

        # 3. Get Qdrant context specifically for this step
        # Build a query that includes step-specific keywords
        step_query = f"Step {target_step}: {question}"
        response = self.openai_client.embeddings.create(
            input=[step_query],
            model="text-embedding-3-small"
        )
        query_vector = response.data[0].embedding

        step_context = self.qdrant_client.search(
            query_vector=query_vector,
            namespace=namespace,
            top_k=5,  # Fewer but more relevant
        )

        print(f"   📄 Retrieved {len(step_context)} step-specific documents from Qdrant")

        # 4. Generate answer with BOTH graph flow AND step-specific context
        answer = self._generate_answer(
            question=question,
            context_docs=step_context,
            workflow_steps=target_steps,
            focus=f"step_{target_step}"
        )

        return {
            'strategy': 'step_specific',
            'target_step': target_step,
            'workflow_steps': target_steps,
            'context_docs': step_context,
            'answer': answer
        }

    def _graph_guided_retrieval(
        self,
        question: str,
        namespace: str,
        intent: QueryIntent
    ) -> Dict[str, Any]:
        """Full graph-guided retrieval for procedural queries."""
        print("\n🎯 Strategy: Graph-Guided Retrieval (Complex Flow)")

        # Get workflow graph
        workflow_steps = self._get_workflow_graph(namespace, start=1, limit=30)
        print(f"   📊 Retrieved {len(workflow_steps)} workflow steps")

        # Get broad Qdrant context
        response = self.openai_client.embeddings.create(
            input=[question],
            model="text-embedding-3-small"
        )
        query_vector = response.data[0].embedding

        context_docs = self.qdrant_client.search(
            query_vector=query_vector,
            namespace=namespace,
            top_k=10,
        )

        print(f"   📄 Retrieved {len(context_docs)} context documents")

        # Generate answer with flow understanding
        answer = self._generate_answer(
            question=question,
            context_docs=context_docs,
            workflow_steps=workflow_steps
        )

        return {
            'strategy': 'graph_guided',
            'workflow_steps': workflow_steps,
            'context_docs': context_docs,
            'answer': answer
        }

    def _hybrid_retrieval(
        self,
        question: str,
        namespace: str
    ) -> Dict[str, Any]:
        """Light hybrid retrieval for simple queries on complex content."""
        print("\n🎯 Strategy: Hybrid Retrieval (Light Graph + Vector)")

        # Get limited workflow context
        workflow_steps = self._get_workflow_graph(namespace, start=1, limit=10)

        # Get Qdrant context
        response = self.openai_client.embeddings.create(
            input=[question],
            model="text-embedding-3-small"
        )
        query_vector = response.data[0].embedding

        context_docs = self.qdrant_client.search(
            query_vector=query_vector,
            namespace=namespace,
            top_k=8,
        )

        print(f"   📊 Retrieved {len(workflow_steps)} workflow steps")
        print(f"   📄 Retrieved {len(context_docs)} context documents")

        answer = self._generate_answer(
            question=question,
            context_docs=context_docs,
            workflow_steps=workflow_steps
        )

        return {
            'strategy': 'hybrid',
            'workflow_steps': workflow_steps,
            'context_docs': context_docs,
            'answer': answer
        }

    def _code_aware_retrieval(
        self,
        question: str,
        namespace: str
    ) -> Dict[str, Any]:
        """Code-specific retrieval using AST and dependencies."""
        print("\n🎯 Strategy: Code-Aware Retrieval (AST + Implementation)")

        # For code: graph represents AST, dependencies, call flows
        # TODO: Implement AST-specific queries
        return self._graph_guided_retrieval(question, namespace, None)

    def _get_workflow_graph(
        self,
        namespace: str,
        start: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve workflow steps from Neo4j graph."""
        if not self.neo4j_client:
            return []

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
                    'start_step': start,
                    'max_steps': limit,
                }
            )
            return results
        except Exception as e:
            print(f"   ⚠️  Neo4j query failed: {e}")
            return []

    def _generate_answer(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        workflow_steps: List[Dict[str, Any]],
        focus: str = None
    ) -> str:
        """Generate answer using LLM with graph + vector context."""
        if not self.openai_client:
            return "LLM not available"

        # Build prompt with both graph and vector context
        parts = []

        # Add workflow if available
        if workflow_steps:
            parts.append("# Workflow Steps\n")
            for step in workflow_steps:
                parts.append(f"## Step {step['step_number']}: {step['title']}")
                parts.append(f"{step['content']}\n")

        # Add Qdrant context
        if context_docs:
            parts.append("\n# Additional Context from Documentation\n")
            for i, doc in enumerate(context_docs, 1):
                metadata = doc.get('metadata', {})
                content = metadata.get('content', doc.get('content', ''))
                title = metadata.get('title', '')
                page = metadata.get('page_number', '?')
                parts.append(f"\n## Context {i} (Page {page}): {title}")
                parts.append(f"{content}\n")

        # Add question
        parts.append(f"\n# User Question\n{question}\n")

        if focus and focus.startswith('step_'):
            step_num = focus.split('_')[1]
            parts.append(f"\nThe user is asking specifically about Step {step_num}. Focus your answer on this step while using the workflow context to provide proper context.")
        else:
            parts.append("\nProvide a clear, detailed answer using the workflow steps and documentation context above.")

        prompt = "\n".join(parts)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions using workflow context and documentation. Be precise and cite specific steps when relevant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Failed to generate answer: {e}"

    def _extract_step_number(self, question: str) -> Optional[int]:
        """Extract step number from question."""
        import re
        patterns = [
            r'step (\d+)',
            r'step-(\d+)',
            r'step#(\d+)',
            r'phase (\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, question.lower())
            if match:
                return int(match.group(1))

        return None


# Singleton
_router: Optional[SmartQueryRouter] = None


def get_query_router() -> SmartQueryRouter:
    """Get or create query router instance."""
    global _router
    if _router is None:
        _router = SmartQueryRouter()
    return _router
