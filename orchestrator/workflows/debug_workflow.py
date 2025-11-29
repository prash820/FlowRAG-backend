"""
Debug Workflow - Multi-stage issue hunting.

Implements a 4-stage approach for debugging queries:
1. Locate: Broad semantic search to find issue area
2. Narrow: Graph traversal to follow call chains
3. Diagnose: Pattern matching for likely causes
4. Synthesize: LLM analysis with recommendations
"""

import logging
from typing import Dict, Any, List, Optional
import time

from orchestrator.workflows.router import WorkflowRequest, WorkflowResult, WorkflowStage, WorkflowType
from orchestrator import get_orchestrator, OrchestrationRequest
from databases.neo4j.client import get_neo4j_client
from databases.qdrant.client import get_qdrant_client
from agents.llm import get_response_generator, ResponseRequest

logger = logging.getLogger(__name__)


class DebugWorkflow:
    """
    Multi-stage workflow for debugging and issue hunting.

    Stages:
    1. LOCATE: Broad semantic search to identify relevant code areas
    2. NARROW: Graph traversal to trace call chains and dependencies
    3. DIAGNOSE: Pattern matching and similar issue detection
    4. SYNTHESIZE: LLM-powered analysis and recommendations
    """

    def __init__(self):
        """Initialize debug workflow with required clients."""
        self.neo4j_client = get_neo4j_client()
        self.qdrant_client = get_qdrant_client()
        self.orchestrator = get_orchestrator()
        self.response_generator = get_response_generator()

    async def execute(self, request: WorkflowRequest) -> WorkflowResult:
        """
        Execute debug workflow.

        Args:
            request: Workflow request

        Returns:
            WorkflowResult with debug-specific fields populated
        """
        logger.info(f"Starting DEBUG workflow for: {request.query[:50]}...")

        result = WorkflowResult(
            success=False,
            workflow_type=WorkflowType.DEBUG,
            query=request.query,
            namespace=request.namespace,
        )

        try:
            # Stage 1: Locate
            stage1_results = self._stage_locate(request)
            result.stages.append(WorkflowStage(
                stage="locate",
                status="completed",
                results_count=len(stage1_results),
                details={"message": "Broad semantic search completed"}
            ))

            if not stage1_results:
                result.error = "No relevant code areas found"
                return result

            # Stage 2: Narrow
            stage2_results = self._stage_narrow(request, stage1_results)
            result.stages.append(WorkflowStage(
                stage="narrow",
                status="completed",
                results_count=len(stage2_results),
                details={"message": "Call chain tracing completed"}
            ))

            # Stage 3: Diagnose
            diagnose_results = self._stage_diagnose(request, stage1_results, stage2_results)
            result.stages.append(WorkflowStage(
                stage="diagnose",
                status="completed",
                results_count=len(diagnose_results.get('likely_causes', [])),
                details={"message": "Pattern matching completed"}
            ))

            result.likely_causes = diagnose_results.get('likely_causes', [])
            result.similar_fixes = diagnose_results.get('similar_fixes', [])

            # Stage 4: Synthesize
            synthesis = await self._stage_synthesize(request, stage1_results, stage2_results, diagnose_results)
            result.stages.append(WorkflowStage(
                stage="synthesize",
                status="completed",
                results_count=1,
                details={"message": "LLM synthesis completed"}
            ))

            result.answer = synthesis.get('answer', '')
            result.recommendations = synthesis.get('recommendations', [])
            result.context_items = synthesis.get('context_items', [])

            result.success = True
            logger.info("DEBUG workflow completed successfully")

        except Exception as e:
            logger.error(f"DEBUG workflow failed: {e}", exc_info=True)
            result.error = str(e)
            # Mark last stage as failed
            if result.stages:
                result.stages[-1].status = "failed"

        return result

    def _stage_locate(self, request: WorkflowRequest) -> List[Dict[str, Any]]:
        """
        Stage 1: Locate - Broad semantic search.

        Uses semantic search to find relevant code areas related to the issue.
        Focuses on error messages, function names, and related concepts.

        Args:
            request: Workflow request

        Returns:
            List of relevant code chunks from semantic search
        """
        logger.info("Stage 1: LOCATE - Running semantic search")

        # Enhance query with debug-specific terms if error context provided
        enhanced_query = request.query
        if request.error_context:
            error_msg = request.error_context.get('error_message', '')
            stack_trace = request.error_context.get('stack_trace', '')

            if error_msg:
                enhanced_query += f" error: {error_msg}"
            if stack_trace:
                # Extract function names from stack trace
                lines = stack_trace.split('\n')[:5]  # First 5 lines
                enhanced_query += f" stack trace: {' '.join(lines)}"

        # Use orchestrator for semantic search
        orch_request = OrchestrationRequest(
            query=enhanced_query,
            namespace=request.namespace,
            max_results=request.max_results * 2,  # Get more candidates
            max_context_tokens=request.max_context_tokens,
            include_flow_analysis=False,
        )

        orch_result = self.orchestrator.orchestrate(orch_request)

        # Convert to list of dicts
        results = []
        if orch_result.context:
            for item in orch_result.context.items:
                results.append({
                    'content': item.content,
                    'source_type': item.source_type,
                    'relevance_score': item.relevance_score,
                    'citation': item.citation,
                    'metadata': item.metadata,
                })

        logger.info(f"Stage 1 complete: Found {len(results)} relevant code chunks")
        return results

    def _stage_narrow(
        self,
        request: WorkflowRequest,
        locate_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Narrow - Graph traversal to trace call chains.

        Uses Neo4j graph traversal to follow CALLS and IMPORTS relationships
        from the code areas found in Stage 1.

        Args:
            request: Workflow request
            locate_results: Results from Stage 1

        Returns:
            List of related nodes from graph traversal
        """
        logger.info("Stage 2: NARROW - Tracing call chains")

        # Extract node IDs from locate results
        node_ids = []
        for item in locate_results[:5]:  # Top 5 results
            metadata = item.get('metadata', {})
            if 'node_id' in metadata:
                node_ids.append(metadata['node_id'])

        if not node_ids:
            logger.warning("No node IDs found in locate results")
            return []

        # Use CodeTracer to follow call chains
        from orchestrator.trace import get_code_tracer
        tracer = get_code_tracer()

        all_nodes = []
        all_relationships = []

        for node_id in node_ids:
            try:
                nodes, relationships = tracer.trace_from_node(
                    node_id=node_id,
                    namespace=request.namespace,
                    max_depth=3,  # Limited depth for performance
                    include_code=request.include_code
                )
                all_nodes.extend(nodes)
                all_relationships.extend(relationships)
            except Exception as e:
                logger.warning(f"Failed to trace from node {node_id}: {e}")
                continue

        # Deduplicate nodes by ID
        seen = set()
        unique_nodes = []
        for node in all_nodes:
            if node['id'] not in seen:
                seen.add(node['id'])
                unique_nodes.append(node)

        logger.info(f"Stage 2 complete: Found {len(unique_nodes)} related nodes via graph traversal")
        return unique_nodes

    def _stage_diagnose(
        self,
        request: WorkflowRequest,
        locate_results: List[Dict[str, Any]],
        narrow_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Stage 3: Diagnose - Pattern matching for likely causes.

        Analyzes code patterns, common anti-patterns, and similar issues
        to identify likely causes.

        Args:
            request: Workflow request
            locate_results: Results from Stage 1
            narrow_results: Results from Stage 2

        Returns:
            Dictionary with likely_causes and similar_fixes
        """
        logger.info("Stage 3: DIAGNOSE - Pattern matching")

        likely_causes = []
        similar_fixes = []

        # Pattern 1: Look for common error patterns in code
        error_patterns = self._detect_error_patterns(locate_results, narrow_results)
        likely_causes.extend(error_patterns)

        # Pattern 2: Find similar issues based on error context
        if request.error_context:
            similar = self._find_similar_issues(request)
            similar_fixes.extend(similar)

        # Pattern 3: Analyze call chain complexity
        complexity_issues = self._analyze_complexity(narrow_results)
        likely_causes.extend(complexity_issues)

        logger.info(f"Stage 3 complete: Found {len(likely_causes)} likely causes, {len(similar_fixes)} similar fixes")

        return {
            'likely_causes': likely_causes,
            'similar_fixes': similar_fixes,
        }

    async def _stage_synthesize(
        self,
        request: WorkflowRequest,
        locate_results: List[Dict[str, Any]],
        narrow_results: List[Dict[str, Any]],
        diagnose_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stage 4: Synthesize - LLM-powered analysis and recommendations.

        Uses LLM to analyze all gathered information and generate
        actionable recommendations.

        Args:
            request: Workflow request
            locate_results: Results from Stage 1
            narrow_results: Results from Stage 2
            diagnose_results: Results from Stage 3

        Returns:
            Dictionary with answer, recommendations, and context_items
        """
        logger.info("Stage 4: SYNTHESIZE - LLM analysis")

        # Build comprehensive context for LLM
        context_parts = []

        # Add locate results (semantic matches)
        context_parts.append("## Relevant Code Areas (Semantic Search):\n")
        for i, item in enumerate(locate_results[:5], 1):
            context_parts.append(f"\n### Match {i} (Score: {item.get('relevance_score', 0):.2f})")
            context_parts.append(f"Source: {item.get('citation', 'Unknown')}")
            context_parts.append(f"```\n{item.get('content', '')}\n```\n")

        # Add narrow results (call chain)
        if narrow_results:
            context_parts.append("\n## Call Chain Analysis:\n")
            for i, node in enumerate(narrow_results[:10], 1):
                context_parts.append(f"\n### Node {i}: {node.get('name', 'Unknown')}")
                context_parts.append(f"File: {node.get('file_path', 'Unknown')}")
                context_parts.append(f"Type: {node.get('type', 'Unknown')}")
                if request.include_code and node.get('code'):
                    context_parts.append(f"```\n{node['code']}\n```")

        # Add likely causes
        if diagnose_results.get('likely_causes'):
            context_parts.append("\n## Likely Causes Detected:\n")
            for i, cause in enumerate(diagnose_results['likely_causes'], 1):
                context_parts.append(f"{i}. {cause.get('description', 'Unknown cause')}")
                if cause.get('location'):
                    context_parts.append(f"   Location: {cause['location']}")

        # Add similar fixes
        if diagnose_results.get('similar_fixes'):
            context_parts.append("\n## Similar Issues and Fixes:\n")
            for i, fix in enumerate(diagnose_results['similar_fixes'], 1):
                context_parts.append(f"{i}. {fix.get('description', 'Unknown fix')}")

        # Add error context if provided
        if request.error_context:
            context_parts.append("\n## Error Context:\n")
            if request.error_context.get('error_message'):
                context_parts.append(f"Error Message: {request.error_context['error_message']}")
            if request.error_context.get('stack_trace'):
                context_parts.append(f"Stack Trace:\n```\n{request.error_context['stack_trace']}\n```")

        full_context = "\n".join(context_parts)

        # Build enhanced prompt for debugging
        debug_prompt = f"""You are analyzing a debugging query. The user is investigating an issue in their codebase.

**User Query:** {request.query}

**Analysis Results:**
{full_context}

**Your Task:**
1. Analyze the code areas, call chains, and detected patterns
2. Identify the most likely root cause of the issue
3. Provide specific, actionable recommendations to fix it
4. Reference specific files and line numbers when possible
5. Suggest testing strategies to verify the fix

Provide a clear, structured response with:
- Root Cause Analysis
- Recommended Fix (with code examples if applicable)
- Testing Strategy
- Prevention Tips
"""

        # Generate response using LLM
        import asyncio

        # Create mock orchestration result for response generator
        from orchestrator.controller import OrchestrationResult
        from orchestrator.context.context_assembler import AssembledContext, ContextItem
        from orchestrator.router.intent_classifier import QueryIntent

        context_items = []
        for item in locate_results[:10]:
            context_items.append(ContextItem(
                content=item.get('content', ''),
                source_type=item.get('source_type', 'unknown'),
                relevance_score=item.get('relevance_score', 0.0),
                citation=item.get('citation', ''),
                metadata=item.get('metadata', {}),
            ))

        mock_orch_result = OrchestrationResult(
            query=debug_prompt,
            namespace=request.namespace,
            intent=QueryIntent.FIND_USAGE,
            intent_confidence=0.95,
            context=AssembledContext(items=context_items, total_items=len(context_items)),
            total_chunks_retrieved=len(context_items),
            retrieval_time=0.0,
        )

        response_request = ResponseRequest(
            orchestration_result=mock_orch_result,
            stream=False,
        )

        # Generate response - use existing event loop if available
        try:
            loop = asyncio.get_running_loop()
            # Already in async context - create task and wait
            generated_response = await self.response_generator.generate_async(response_request)
        except RuntimeError:
            # No running loop - create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                generated_response = loop.run_until_complete(
                    self.response_generator.generate_async(response_request)
                )
            finally:
                loop.close()

        # Parse recommendations from response
        recommendations = self._parse_recommendations(generated_response.content)

        # Build context items for result
        result_context_items = []
        for item in locate_results[:10]:
            result_context_items.append({
                'content': item.get('content', ''),
                'source_type': item.get('source_type', 'unknown'),
                'relevance_score': item.get('relevance_score', 0.0),
                'citation': item.get('citation', ''),
                'metadata': item.get('metadata', {}),
            })

        logger.info("Stage 4 complete: LLM synthesis finished")

        return {
            'answer': generated_response.content,
            'recommendations': recommendations,
            'context_items': result_context_items,
        }

    def _detect_error_patterns(
        self,
        locate_results: List[Dict[str, Any]],
        narrow_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect common error patterns in code."""
        patterns = []

        # Combine all code snippets
        all_code = []
        for item in locate_results:
            all_code.append(item.get('content', ''))
        for node in narrow_results:
            if node.get('code'):
                all_code.append(node['code'])

        # Pattern: Unchecked null/undefined
        for i, code in enumerate(all_code):
            if any(keyword in code.lower() for keyword in ['null', 'undefined', 'none']):
                if not any(check in code.lower() for check in ['if', 'try', 'catch', '?.']):
                    patterns.append({
                        'type': 'potential_null_reference',
                        'description': 'Potential null/undefined reference without null check',
                        'location': f'Code chunk {i+1}',
                        'severity': 'medium'
                    })

        # Pattern: Unhandled promises/async
        for i, code in enumerate(all_code):
            if 'async' in code.lower() or 'promise' in code.lower():
                if '.catch' not in code.lower() and 'try' not in code.lower():
                    patterns.append({
                        'type': 'unhandled_async',
                        'description': 'Async operation without error handling',
                        'location': f'Code chunk {i+1}',
                        'severity': 'high'
                    })

        return patterns

    def _find_similar_issues(self, request: WorkflowRequest) -> List[Dict[str, Any]]:
        """Find similar issues based on error context."""
        similar = []

        # This is a placeholder - in production, you'd search historical issues
        # or use semantic search on error messages

        if request.error_context:
            error_msg = request.error_context.get('error_message', '').lower()

            # Common patterns
            if 'cannot read property' in error_msg or 'undefined' in error_msg:
                similar.append({
                    'type': 'null_reference',
                    'description': 'Accessing property of null/undefined object',
                    'fix': 'Add null checks or use optional chaining (?.)',
                    'frequency': 'common'
                })

            if 'is not a function' in error_msg:
                similar.append({
                    'type': 'type_error',
                    'description': 'Attempting to call non-function as function',
                    'fix': 'Verify variable type before calling as function',
                    'frequency': 'common'
                })

        return similar

    def _analyze_complexity(self, narrow_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze call chain complexity for potential issues."""
        issues = []

        # Analyze call chain depth
        if narrow_results:
            max_depth = max([node.get('depth', 0) for node in narrow_results])
            if max_depth > 5:
                issues.append({
                    'type': 'deep_call_chain',
                    'description': f'Deep call chain detected (depth: {max_depth})',
                    'location': 'Call chain analysis',
                    'severity': 'low',
                    'recommendation': 'Consider simplifying call hierarchy'
                })

        # Analyze circular dependencies (simplified)
        node_ids = [node.get('id') for node in narrow_results]
        if len(node_ids) != len(set(node_ids)):
            issues.append({
                'type': 'potential_circular_dependency',
                'description': 'Potential circular dependency detected',
                'location': 'Call chain analysis',
                'severity': 'medium',
                'recommendation': 'Review dependency structure'
            })

        return issues

    def _parse_recommendations(self, llm_response: str) -> List[Dict[str, Any]]:
        """Parse structured recommendations from LLM response."""
        recommendations = []

        # Simple parsing - look for numbered lists or bullet points
        lines = llm_response.split('\n')
        current_rec = None

        for line in lines:
            line = line.strip()

            # Check for recommendation indicators
            if any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*']):
                if current_rec:
                    recommendations.append(current_rec)

                # Extract recommendation text
                for prefix in ['1.', '2.', '3.', '4.', '5.', '-', '*', '•']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break

                current_rec = {
                    'description': line,
                    'type': 'general',
                    'priority': 'medium'
                }
            elif current_rec and line:
                # Continuation of current recommendation
                current_rec['description'] += ' ' + line

        # Add last recommendation
        if current_rec:
            recommendations.append(current_rec)

        # If no structured recommendations found, create one general recommendation
        if not recommendations:
            recommendations.append({
                'description': 'Review the analysis above for detailed guidance',
                'type': 'general',
                'priority': 'medium'
            })

        return recommendations[:10]  # Limit to 10 recommendations
