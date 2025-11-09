"""
Context assembly for LLM consumption.

Orchestrator Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from orchestrator.retrieval.hybrid_retriever import RetrievalResult
from orchestrator.router.intent_classifier import QueryIntent

logger = logging.getLogger(__name__)


class ContextItem(BaseModel):
    """Single context item for LLM."""

    content: str = Field(..., description="Main content text")
    source_type: str = Field(..., description="code, document, graph")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation: Optional[str] = Field(None, description="Citation reference")


class AssembledContext(BaseModel):
    """Assembled context for LLM prompt."""

    items: List[ContextItem] = Field(default_factory=list)
    total_items: int = Field(default=0)
    total_tokens: int = Field(default=0, description="Approximate token count")
    context_summary: str = Field(default="", description="Summary of context")


class ContextAssembler:
    """
    Assembles context from hybrid retrieval results.

    Combines vector search and graph traversal results into
    coherent context for LLM consumption.
    """

    def __init__(self, max_tokens: int = 4000):
        """
        Initialize context assembler.

        Args:
            max_tokens: Maximum context tokens for LLM
        """
        self.max_tokens = max_tokens

    def assemble(
        self,
        retrieval_result: RetrievalResult,
        query: str,
        intent: QueryIntent,
    ) -> AssembledContext:
        """
        Assemble context from retrieval results.

        Args:
            retrieval_result: Results from hybrid retrieval
            query: Original user query
            intent: Detected query intent

        Returns:
            Assembled context ready for LLM
        """
        items = []

        # Process vector search results
        vector_items = self._process_vector_results(
            retrieval_result.vector_results,
            intent
        )
        items.extend(vector_items)

        # Process graph traversal results
        graph_items = self._process_graph_results(
            retrieval_result.graph_results,
            intent
        )
        items.extend(graph_items)

        # Deduplicate and rank
        items = self._deduplicate(items)
        items = self._rank_and_filter(items, query)

        # Trim to token budget
        items, total_tokens = self._trim_to_budget(items)

        # Generate summary
        summary = self._generate_summary(items, intent)

        return AssembledContext(
            items=items,
            total_items=len(items),
            total_tokens=total_tokens,
            context_summary=summary,
        )

    def _process_vector_results(
        self,
        vector_results: List[Dict[str, Any]],
        intent: QueryIntent,
    ) -> List[ContextItem]:
        """Process vector search results into context items."""
        items = []

        for idx, result in enumerate(vector_results):
            metadata = result.get("metadata", {})
            result_type = metadata.get("type", "unknown")

            if result_type == "code":
                item = self._format_code_result(result, idx)
            elif result_type == "document":
                item = self._format_document_result(result, idx)
            else:
                continue

            items.append(item)

        return items

    def _format_code_result(
        self,
        result: Dict[str, Any],
        idx: int
    ) -> ContextItem:
        """Format code unit as context item."""
        metadata = result.get("metadata", {})

        # Build content with structure
        content_parts = []

        # Header
        code_type = metadata.get("code_unit_type", "code")
        name = metadata.get("name", "unknown")
        file_path = metadata.get("file_path", "")
        line_start = metadata.get("line_start", 0)

        content_parts.append(f"# {code_type.upper()}: {name}")
        content_parts.append(f"Location: {file_path}:{line_start}")
        content_parts.append("")

        # Signature
        signature = metadata.get("signature")
        if signature:
            content_parts.append("```python")
            content_parts.append(signature)
            content_parts.append("```")
            content_parts.append("")

        # Docstring
        docstring = metadata.get("docstring")
        if docstring:
            content_parts.append("**Documentation:**")
            content_parts.append(docstring)
            content_parts.append("")

        # Code
        code = metadata.get("full_code", metadata.get("code"))
        if code:
            content_parts.append("**Implementation:**")
            content_parts.append("```python")
            content_parts.append(code)
            content_parts.append("```")

        # Calls/Imports context
        calls = metadata.get("calls", [])
        if calls:
            content_parts.append("")
            content_parts.append(f"**Calls:** {', '.join(calls)}")

        imports = metadata.get("imports", [])
        if imports:
            content_parts.append(f"**Imports:** {', '.join(imports)}")

        content = "\n".join(content_parts)

        # Citation
        citation = f"[{idx + 1}] {file_path}:{line_start}"

        return ContextItem(
            content=content,
            source_type="code",
            metadata=metadata,
            relevance_score=result.get("score", 0.0),
            citation=citation,
        )

    def _format_document_result(
        self,
        result: Dict[str, Any],
        idx: int
    ) -> ContextItem:
        """Format document chunk as context item."""
        metadata = result.get("metadata", {})

        content_parts = []

        # Header
        file_path = metadata.get("file_path", "")
        chunk_index = metadata.get("chunk_index", 0)
        section_title = metadata.get("section_title")

        if section_title:
            content_parts.append(f"# {section_title}")
        else:
            content_parts.append(f"# Document Chunk {chunk_index + 1}")

        content_parts.append(f"Source: {file_path}")
        content_parts.append("")

        # Content
        chunk_content = metadata.get("content", "")
        content_parts.append(chunk_content)

        content = "\n".join(content_parts)

        # Citation
        citation = f"[{idx + 1}] {file_path} (chunk {chunk_index})"

        return ContextItem(
            content=content,
            source_type="document",
            metadata=metadata,
            relevance_score=result.get("score", 0.0),
            citation=citation,
        )

    def _process_graph_results(
        self,
        graph_results: List[Dict[str, Any]],
        intent: QueryIntent,
    ) -> List[ContextItem]:
        """Process graph traversal results into context items."""
        items = []

        # Different formatting based on intent
        if intent == QueryIntent.FIND_FLOW:
            items = self._format_flow_results(graph_results)
        elif intent == QueryIntent.PARALLEL_STEPS:
            items = self._format_parallel_steps(graph_results)
        elif intent == QueryIntent.TRACE_CALLS:
            items = self._format_call_chain(graph_results)
        elif intent == QueryIntent.FIND_DEPENDENCIES:
            items = self._format_dependencies(graph_results)
        else:
            # Generic graph result formatting
            items = self._format_generic_graph(graph_results)

        return items

    def _format_flow_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Format execution flow results."""
        items = []

        for idx, flow in enumerate(results):
            content_parts = []

            content_parts.append("# Execution Flow")
            content_parts.append("")

            flow_data = flow.get("flow", {})
            description = flow_data.get("description", "")
            if description:
                content_parts.append(f"**Description:** {description}")
                content_parts.append("")

            # Flow metadata
            flow_type = flow_data.get("flow_type", "")
            if flow_type:
                content_parts.append(f"**Type:** {flow_type}")

            content = "\n".join(content_parts)

            items.append(ContextItem(
                content=content,
                source_type="graph",
                metadata=flow_data,
                relevance_score=0.8,  # Graph results highly relevant
                citation=f"[G{idx + 1}] Execution Flow",
            ))

        return items

    def _format_parallel_steps(
        self,
        results: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Format parallel step results."""
        if not results:
            return []

        content_parts = []
        content_parts.append("# Parallel Execution Opportunities")
        content_parts.append("")

        for result in results:
            step = result.get("step", 0)
            description = result.get("description", "")
            parallel_with = result.get("parallel_with", [])

            content_parts.append(f"**Step {step}:** {description}")
            if parallel_with:
                parallel_str = ", ".join(f"Step {s}" for s in parallel_with)
                content_parts.append(f"  - Can run in parallel with: {parallel_str}")
            content_parts.append("")

        content = "\n".join(content_parts)

        return [ContextItem(
            content=content,
            source_type="graph",
            metadata={"type": "parallel_analysis"},
            relevance_score=0.9,
            citation="[G1] Parallel Step Analysis",
        )]

    def _format_call_chain(
        self,
        results: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Format call chain results."""
        if not results:
            return []

        content_parts = []
        content_parts.append("# Call Chain Analysis")
        content_parts.append("")

        for idx, chain in enumerate(results):
            content_parts.append(f"**Chain {idx + 1}:**")

            # Format as chain: A -> B -> C
            nodes = chain.get("nodes", [])
            if nodes:
                chain_str = " -> ".join(n.get("name", "?") for n in nodes)
                content_parts.append(f"  {chain_str}")

            content_parts.append("")

        content = "\n".join(content_parts)

        return [ContextItem(
            content=content,
            source_type="graph",
            metadata={"type": "call_chain"},
            relevance_score=0.9,
            citation="[G1] Call Chain",
        )]

    def _format_dependencies(
        self,
        results: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Format dependency results."""
        if not results:
            return []

        content_parts = []
        content_parts.append("# Dependency Analysis")
        content_parts.append("")

        for result in results:
            name = result.get("name", "unknown")
            deps = result.get("dependencies", [])

            content_parts.append(f"**{name}**")
            if deps:
                content_parts.append("  Depends on:")
                for dep in deps:
                    content_parts.append(f"  - {dep}")
            else:
                content_parts.append("  No dependencies")
            content_parts.append("")

        content = "\n".join(content_parts)

        return [ContextItem(
            content=content,
            source_type="graph",
            metadata={"type": "dependencies"},
            relevance_score=0.85,
            citation="[G1] Dependency Graph",
        )]

    def _format_generic_graph(
        self,
        results: List[Dict[str, Any]]
    ) -> List[ContextItem]:
        """Format generic graph results."""
        items = []

        for idx, result in enumerate(results):
            content = f"# Graph Result {idx + 1}\n\n"
            content += str(result)

            items.append(ContextItem(
                content=content,
                source_type="graph",
                metadata=result,
                relevance_score=0.7,
                citation=f"[G{idx + 1}] Graph Result",
            ))

        return items

    def _deduplicate(self, items: List[ContextItem]) -> List[ContextItem]:
        """Remove duplicate context items."""
        seen = set()
        unique_items = []

        for item in items:
            # Create hash from content preview
            content_hash = hash(item.content[:200])

            if content_hash not in seen:
                seen.add(content_hash)
                unique_items.append(item)

        return unique_items

    def _rank_and_filter(
        self,
        items: List[ContextItem],
        query: str
    ) -> List[ContextItem]:
        """Rank items by relevance and filter low scores."""
        # Sort by relevance score (descending)
        items.sort(key=lambda x: x.relevance_score, reverse=True)

        # Filter out very low scores
        items = [item for item in items if item.relevance_score > 0.3]

        return items

    def _trim_to_budget(
        self,
        items: List[ContextItem]
    ) -> tuple[List[ContextItem], int]:
        """Trim items to fit token budget."""
        selected = []
        total_tokens = 0

        for item in items:
            # Rough token estimation (1 token ≈ 4 chars)
            item_tokens = len(item.content) // 4

            if total_tokens + item_tokens <= self.max_tokens:
                selected.append(item)
                total_tokens += item_tokens
            else:
                # Budget exhausted
                break

        return selected, total_tokens

    def _generate_summary(
        self,
        items: List[ContextItem],
        intent: QueryIntent
    ) -> str:
        """Generate summary of assembled context."""
        if not items:
            return "No relevant context found."

        code_count = sum(1 for item in items if item.source_type == "code")
        doc_count = sum(1 for item in items if item.source_type == "document")
        graph_count = sum(1 for item in items if item.source_type == "graph")

        parts = []
        if code_count:
            parts.append(f"{code_count} code units")
        if doc_count:
            parts.append(f"{doc_count} document chunks")
        if graph_count:
            parts.append(f"{graph_count} graph analyses")

        summary = f"Retrieved {', '.join(parts)} for {intent.value} query."

        return summary


def get_context_assembler(max_tokens: int = 4000) -> ContextAssembler:
    """Get context assembler instance."""
    return ContextAssembler(max_tokens=max_tokens)
