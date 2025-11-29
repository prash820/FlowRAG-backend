"""
Optimization Workflow - Performance analysis and bottleneck detection.

Analyzes code flow for optimization opportunities:
1. Map Flow: Build execution flow graph
2. Detect Bottlenecks: Identify performance bottlenecks
3. Find Parallelization: Discover parallel execution opportunities
4. Generate Plan: Create optimization recommendations
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import time

from orchestrator.workflows.router import WorkflowRequest, WorkflowResult, WorkflowStage, WorkflowType
from orchestrator import get_orchestrator, OrchestrationRequest
from databases.neo4j.client import get_neo4j_client
from orchestrator.trace import get_code_tracer
from agents.llm import get_response_generator, ResponseRequest

logger = logging.getLogger(__name__)


class OptimizationWorkflow:
    """
    Workflow for performance optimization analysis.

    Stages:
    1. MAP_FLOW: Build execution flow graph from target function
    2. DETECT_BOTTLENECKS: Identify performance bottlenecks
    3. FIND_PARALLELIZATION: Discover parallel execution opportunities
    4. GENERATE_PLAN: LLM-powered optimization plan
    """

    def __init__(self):
        """Initialize optimization workflow with required clients."""
        self.neo4j_client = get_neo4j_client()
        self.tracer = get_code_tracer()
        self.orchestrator = get_orchestrator()
        self.response_generator = get_response_generator()

    async def execute(self, request: WorkflowRequest) -> WorkflowResult:
        """
        Execute optimization workflow.

        Args:
            request: Workflow request

        Returns:
            WorkflowResult with optimization-specific fields populated
        """
        logger.info(f"Starting OPTIMIZATION workflow for: {request.query[:50]}...")

        result = WorkflowResult(
            success=False,
            workflow_type=WorkflowType.OPTIMIZE,
            query=request.query,
            namespace=request.namespace,
        )

        try:
            # Stage 1: Map Flow
            flow_map = self._stage_map_flow(request)
            result.stages.append(WorkflowStage(
                stage="map_flow",
                status="completed",
                results_count=flow_map.get('total_nodes', 0),
                details={"message": "Execution flow mapped"}
            ))

            if not flow_map.get('success'):
                result.error = flow_map.get('message', 'Failed to map flow')
                return result

            result.flow_map = flow_map

            # Stage 2: Detect Bottlenecks
            bottlenecks = self._stage_detect_bottlenecks(request, flow_map)
            result.stages.append(WorkflowStage(
                stage="detect_bottlenecks",
                status="completed",
                results_count=len(bottlenecks),
                details={"message": f"Found {len(bottlenecks)} potential bottlenecks"}
            ))

            result.bottlenecks = bottlenecks

            # Stage 3: Find Parallelization
            parallel_opportunities = self._stage_find_parallelization(request, flow_map)
            result.stages.append(WorkflowStage(
                stage="find_parallelization",
                status="completed",
                results_count=len(parallel_opportunities),
                details={"message": f"Found {len(parallel_opportunities)} parallelization opportunities"}
            ))

            result.parallel_opportunities = parallel_opportunities

            # Stage 4: Generate Plan
            plan = await self._stage_generate_plan(request, flow_map, bottlenecks, parallel_opportunities)
            result.stages.append(WorkflowStage(
                stage="generate_plan",
                status="completed",
                results_count=1,
                details={"message": "Optimization plan generated"}
            ))

            result.answer = plan.get('answer', '')
            result.context_items = plan.get('context_items', [])

            result.success = True
            logger.info("OPTIMIZATION workflow completed successfully")

        except Exception as e:
            logger.error(f"OPTIMIZATION workflow failed: {e}", exc_info=True)
            result.error = str(e)
            if result.stages:
                result.stages[-1].status = "failed"

        return result

    def _stage_map_flow(self, request: WorkflowRequest) -> Dict[str, Any]:
        """
        Stage 1: Map Flow - Build execution flow graph.

        Uses graph traversal to build complete execution flow starting
        from target function or entry point.

        Args:
            request: Workflow request

        Returns:
            Dictionary containing flow map with nodes and relationships
        """
        logger.info("Stage 1: MAP_FLOW - Building execution flow graph")

        # Determine starting point
        if request.target_function:
            # Search for specific function
            entry_point = request.target_function
        else:
            # Extract function name from query
            entry_point = self._extract_function_from_query(request.query)

        # Trace linear flow from entry point
        flow_result = self.tracer.trace_linear_flow(
            namespace=request.namespace,
            entry_point=entry_point,
            max_depth=request.analysis_depth,
            include_code=request.include_code
        )

        logger.info(f"Stage 1 complete: Mapped {flow_result.get('total_nodes', 0)} nodes")
        return flow_result

    def _stage_detect_bottlenecks(
        self,
        request: WorkflowRequest,
        flow_map: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Stage 2: Detect Bottlenecks - Identify performance bottlenecks.

        Analyzes execution flow for common bottleneck patterns:
        - Synchronous operations that could be async
        - Nested loops
        - Repeated database queries
        - Large data processing without streaming

        Args:
            request: Workflow request
            flow_map: Flow map from Stage 1

        Returns:
            List of detected bottlenecks
        """
        logger.info("Stage 2: DETECT_BOTTLENECKS - Analyzing performance bottlenecks")

        bottlenecks = []
        nodes = flow_map.get('nodes', [])

        # Bottleneck 1: Nested loops
        for node in nodes:
            code = node.get('code', '')
            if not code:
                continue

            # Count loop nesting
            loop_depth = self._detect_loop_nesting(code)
            if loop_depth >= 2:
                bottlenecks.append({
                    'type': 'nested_loops',
                    'severity': 'high' if loop_depth >= 3 else 'medium',
                    'description': f'Nested loops detected (depth: {loop_depth})',
                    'location': {
                        'file': node.get('file_path', 'Unknown'),
                        'function': node.get('name', 'Unknown'),
                        'line': node.get('line_number'),
                    },
                    'suggestion': 'Consider algorithmic optimization or caching',
                })

        # Bottleneck 2: Synchronous I/O operations
        io_patterns = ['fs.readFileSync', 'fs.writeFileSync', 'JSON.parse(fs.read']
        for node in nodes:
            code = node.get('code', '')
            for pattern in io_patterns:
                if pattern in code:
                    bottlenecks.append({
                        'type': 'synchronous_io',
                        'severity': 'high',
                        'description': f'Synchronous I/O operation: {pattern}',
                        'location': {
                            'file': node.get('file_path', 'Unknown'),
                            'function': node.get('name', 'Unknown'),
                            'line': node.get('line_number'),
                        },
                        'suggestion': 'Use async I/O operations for better performance',
                    })

        # Bottleneck 3: Database queries in loops
        db_patterns = ['query(', 'find(', 'execute(', 'fetch(']
        for node in nodes:
            code = node.get('code', '')
            has_loop = any(kw in code for kw in ['for', 'while', 'forEach', 'map'])
            has_db = any(pattern in code for pattern in db_patterns)

            if has_loop and has_db:
                bottlenecks.append({
                    'type': 'n_plus_1_query',
                    'severity': 'critical',
                    'description': 'Potential N+1 query problem: database query inside loop',
                    'location': {
                        'file': node.get('file_path', 'Unknown'),
                        'function': node.get('name', 'Unknown'),
                        'line': node.get('line_number'),
                    },
                    'suggestion': 'Batch queries or use joins/includes',
                })

        # Bottleneck 4: Long critical paths
        max_depth = flow_map.get('max_depth_reached', 0)
        if max_depth > 7:
            bottlenecks.append({
                'type': 'long_critical_path',
                'severity': 'medium',
                'description': f'Long execution path detected (depth: {max_depth})',
                'location': {
                    'file': 'Overall flow',
                    'function': flow_map.get('entry_point', 'Unknown'),
                },
                'suggestion': 'Consider breaking down into smaller, composable functions',
            })

        logger.info(f"Stage 2 complete: Detected {len(bottlenecks)} bottlenecks")
        return bottlenecks

    def _stage_find_parallelization(
        self,
        request: WorkflowRequest,
        flow_map: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Stage 3: Find Parallelization - Discover parallel execution opportunities.

        Analyzes execution flow to find independent operations that can run in parallel.

        Args:
            request: Workflow request
            flow_map: Flow map from Stage 1

        Returns:
            List of parallelization opportunities
        """
        logger.info("Stage 3: FIND_PARALLELIZATION - Discovering parallel opportunities")

        opportunities = []
        nodes = flow_map.get('nodes', [])
        relationships = flow_map.get('relationships', [])

        # Build dependency graph
        dependencies = self._build_dependency_graph(nodes, relationships)

        # Find independent branches
        independent_branches = self._find_independent_branches(dependencies)

        for branch_group in independent_branches:
            if len(branch_group) >= 2:
                opportunities.append({
                    'type': 'independent_branches',
                    'description': f'{len(branch_group)} independent operations can run in parallel',
                    'operations': [
                        {
                            'function': nodes[idx].get('name', 'Unknown'),
                            'file': nodes[idx].get('file_path', 'Unknown'),
                        }
                        for idx in branch_group if idx < len(nodes)
                    ],
                    'potential_speedup': f'{len(branch_group)}x (theoretical)',
                    'suggestion': 'Use Promise.all() or async/await pattern',
                })

        # Find parallelizable loops
        for node in nodes:
            code = node.get('code', '')
            if any(kw in code for kw in ['.map(', '.forEach(', 'for (', 'for(', 'while(']):
                # Check if loop body has async operations
                has_async = any(pattern in code for pattern in ['await', 'async', '.then(', 'Promise'])

                if has_async:
                    opportunities.append({
                        'type': 'parallelizable_loop',
                        'description': 'Loop with async operations can be parallelized',
                        'location': {
                            'file': node.get('file_path', 'Unknown'),
                            'function': node.get('name', 'Unknown'),
                            'line': node.get('line_number'),
                        },
                        'suggestion': 'Use Promise.all() with map instead of sequential await in loop',
                        'example': 'await Promise.all(items.map(async item => await process(item)))',
                    })

        # Find batching opportunities
        for node in nodes:
            code = node.get('code', '')

            # Multiple sequential API calls
            api_call_count = code.count('await fetch(') + code.count('await axios.')
            if api_call_count >= 3:
                opportunities.append({
                    'type': 'batch_requests',
                    'description': f'{api_call_count} sequential API calls detected',
                    'location': {
                        'file': node.get('file_path', 'Unknown'),
                        'function': node.get('name', 'Unknown'),
                        'line': node.get('line_number'),
                    },
                    'suggestion': 'Batch API requests using Promise.all() or API batch endpoints',
                })

        logger.info(f"Stage 3 complete: Found {len(opportunities)} parallelization opportunities")
        return opportunities

    async def _stage_generate_plan(
        self,
        request: WorkflowRequest,
        flow_map: Dict[str, Any],
        bottlenecks: List[Dict[str, Any]],
        parallel_opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Stage 4: Generate Plan - LLM-powered optimization plan.

        Uses LLM to analyze all findings and generate comprehensive
        optimization plan with prioritized recommendations.

        Args:
            request: Workflow request
            flow_map: Flow map from Stage 1
            bottlenecks: Bottlenecks from Stage 2
            parallel_opportunities: Parallelization opportunities from Stage 3

        Returns:
            Dictionary with answer and context_items
        """
        logger.info("Stage 4: GENERATE_PLAN - Creating optimization plan")

        # Build comprehensive context for LLM
        context_parts = []

        # Add flow summary
        context_parts.append("## Execution Flow Analysis:\n")
        context_parts.append(f"Entry Point: {flow_map.get('entry_point', 'Unknown')}")
        context_parts.append(f"Total Nodes: {flow_map.get('total_nodes', 0)}")
        context_parts.append(f"Total Relationships: {flow_map.get('total_relationships', 0)}")
        context_parts.append(f"Max Depth: {flow_map.get('max_depth_reached', 0)}\n")

        # Add key nodes in flow
        nodes = flow_map.get('nodes', [])
        if nodes:
            context_parts.append("\n## Key Functions in Execution Flow:\n")
            for i, node in enumerate(nodes[:10], 1):
                context_parts.append(f"\n### {i}. {node.get('name', 'Unknown')}")
                context_parts.append(f"File: {node.get('file_path', 'Unknown')}")
                context_parts.append(f"Depth: {node.get('depth', 0)}")
                if request.include_code and node.get('code'):
                    context_parts.append(f"```\n{node['code'][:500]}...\n```")  # Truncate long code

        # Add bottlenecks
        if bottlenecks:
            context_parts.append("\n## Detected Bottlenecks:\n")
            for i, bottleneck in enumerate(bottlenecks, 1):
                context_parts.append(f"\n### {i}. {bottleneck.get('type', 'Unknown')} (Severity: {bottleneck.get('severity', 'unknown')})")
                context_parts.append(f"Description: {bottleneck.get('description', '')}")
                if bottleneck.get('location'):
                    loc = bottleneck['location']
                    context_parts.append(f"Location: {loc.get('file', 'Unknown')} - {loc.get('function', 'Unknown')}")
                context_parts.append(f"Suggestion: {bottleneck.get('suggestion', 'N/A')}")

        # Add parallelization opportunities
        if parallel_opportunities:
            context_parts.append("\n## Parallelization Opportunities:\n")
            for i, opp in enumerate(parallel_opportunities, 1):
                context_parts.append(f"\n### {i}. {opp.get('type', 'Unknown')}")
                context_parts.append(f"Description: {opp.get('description', '')}")
                if opp.get('location'):
                    loc = opp['location']
                    context_parts.append(f"Location: {loc.get('file', 'Unknown')} - {loc.get('function', 'Unknown')}")
                context_parts.append(f"Suggestion: {opp.get('suggestion', 'N/A')}")
                if opp.get('potential_speedup'):
                    context_parts.append(f"Potential Speedup: {opp['potential_speedup']}")

        full_context = "\n".join(context_parts)

        # Build optimization prompt
        optimization_prompt = f"""You are analyzing code performance and optimization opportunities.

**User Query:** {request.query}

**Performance Analysis:**
{full_context}

**Your Task:**
1. Prioritize the optimization opportunities by impact
2. Provide specific, actionable optimization recommendations
3. Include code examples for key optimizations
4. Estimate potential performance improvements
5. Suggest monitoring and measurement strategies

Provide a structured optimization plan with:
- Executive Summary (overall assessment)
- High-Priority Optimizations (critical bottlenecks)
- Medium-Priority Optimizations (parallelization opportunities)
- Low-Priority Optimizations (code quality improvements)
- Implementation Roadmap (suggested order)
- Success Metrics (how to measure improvements)

Include specific code examples where applicable.
"""

        # Generate response using LLM
        import asyncio
        from orchestrator.controller import OrchestrationResult
        from orchestrator.context.context_assembler import AssembledContext, ContextItem
        from orchestrator.router.intent_classifier import QueryIntent

        # Create context items from flow nodes
        context_items = []
        for node in nodes[:10]:
            if node.get('code'):
                context_items.append(ContextItem(
                    content=node['code'],
                    source_type='code',
                    relevance_score=1.0 / (node.get('depth', 0) + 1),  # Higher score for shallower nodes
                    citation=f"{node.get('file_path', 'Unknown')}:{node.get('line_number', 0)}",
                    metadata={
                        'function_name': node.get('name', 'Unknown'),
                        'node_type': node.get('type', 'Unknown'),
                        'depth': node.get('depth', 0),
                    },
                ))

        mock_orch_result = OrchestrationResult(
            query=optimization_prompt,
            namespace=request.namespace,
            intent=QueryIntent.OPTIMIZE_FLOW,
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

        # Build context items for result
        result_context_items = []
        for item in context_items:
            result_context_items.append({
                'content': item.content,
                'source_type': item.source_type,
                'relevance_score': item.relevance_score,
                'citation': item.citation,
                'metadata': item.metadata,
            })

        logger.info("Stage 4 complete: Optimization plan generated")

        return {
            'answer': generated_response.content,
            'context_items': result_context_items,
        }

    def _extract_function_from_query(self, query: str) -> Optional[str]:
        """Extract function name from optimization query."""
        # Simple heuristic - look for common patterns
        query_lower = query.lower()

        # Pattern: "optimize X function"
        if 'optimize' in query_lower and 'function' in query_lower:
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() == 'optimize' and i + 1 < len(words):
                    return words[i + 1]

        # Pattern: function name in quotes
        import re
        quoted = re.findall(r'"([^"]*)"', query)
        if quoted:
            return quoted[0]

        quoted = re.findall(r"'([^']*)'", query)
        if quoted:
            return quoted[0]

        # Default: use first word that looks like a function name (camelCase or snake_case)
        words = query.split()
        for word in words:
            if '_' in word or (word[0].islower() and any(c.isupper() for c in word)):
                return word

        return None

    def _detect_loop_nesting(self, code: str) -> int:
        """Detect maximum loop nesting depth in code."""
        max_depth = 0
        current_depth = 0

        lines = code.split('\n')
        for line in lines:
            stripped = line.strip()

            # Check for loop start
            if any(stripped.startswith(kw) for kw in ['for', 'for(', 'while', 'while(']) or \
               '.forEach(' in stripped or '.map(' in stripped:
                current_depth += 1
                max_depth = max(max_depth, current_depth)

            # Check for block end (simplified - just count braces)
            if '}' in stripped:
                current_depth = max(0, current_depth - stripped.count('}'))

        return max_depth

    def _build_dependency_graph(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Set[str]]:
        """Build dependency graph from nodes and relationships."""
        # Map node_id to index
        node_map = {node['id']: i for i, node in enumerate(nodes)}

        # Build adjacency list
        dependencies = {i: set() for i in range(len(nodes))}

        for rel in relationships:
            from_id = rel.get('from_id')
            to_id = rel.get('to_id')

            if from_id in node_map and to_id in node_map:
                from_idx = node_map[from_id]
                to_idx = node_map[to_id]
                dependencies[from_idx].add(to_idx)

        return dependencies

    def _find_independent_branches(
        self,
        dependencies: Dict[int, Set[int]]
    ) -> List[List[int]]:
        """Find groups of independent nodes that can run in parallel."""
        independent_groups = []

        # Group nodes by depth (simple heuristic)
        depth_groups = {}
        visited = set()

        def get_depth(node_idx, current_depth=0):
            if node_idx in visited:
                return 0

            visited.add(node_idx)
            max_child_depth = 0

            for child in dependencies.get(node_idx, []):
                child_depth = get_depth(child, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)

            depth = current_depth + max_child_depth
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(node_idx)

            return depth

        # Calculate depths
        for node_idx in dependencies:
            if node_idx not in visited:
                get_depth(node_idx)

        # Find groups with multiple nodes at same depth (potential parallelization)
        for depth, nodes in depth_groups.items():
            if len(nodes) >= 2:
                independent_groups.append(nodes)

        return independent_groups
