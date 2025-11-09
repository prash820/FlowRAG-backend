"""
Execution flow detection and analysis.

Orchestrator Agent is responsible for this module.
"""

from typing import List, Dict, Any, Set, Optional, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import logging

from databases import get_neo4j_client

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Type of execution step."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    ASYNC = "async"


class FlowStep(BaseModel):
    """Represents a step in execution flow."""

    step_number: int
    description: str
    step_type: StepType = StepType.SEQUENTIAL
    depends_on: List[int] = Field(default_factory=list)
    parallel_with: List[int] = Field(default_factory=list)
    estimated_time: Optional[float] = None
    is_critical_path: bool = False


class FlowAnalysis(BaseModel):
    """Analysis result for execution flow."""

    flow_id: str
    description: str
    total_steps: int

    # Steps breakdown
    steps: List[FlowStep] = Field(default_factory=list)

    # Parallelization opportunities
    parallel_groups: List[List[int]] = Field(
        default_factory=list,
        description="Groups of steps that can run in parallel"
    )

    # Critical path
    critical_path: List[int] = Field(
        default_factory=list,
        description="Steps on the critical path"
    )

    # Dependencies
    dependency_graph: Dict[int, List[int]] = Field(
        default_factory=dict,
        description="Step dependencies (step -> list of dependencies)"
    )

    # Performance metrics
    sequential_time: Optional[float] = None
    parallel_time: Optional[float] = None
    speedup_potential: Optional[float] = None

    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


class FlowAnalyzer:
    """
    Analyzes execution flows for optimization opportunities.

    Detects:
    - Parallel execution opportunities
    - Critical path
    - Dependencies
    - Potential bottlenecks
    """

    def __init__(self):
        """Initialize flow analyzer."""
        self.neo4j_client = get_neo4j_client()

    def analyze_flow(
        self,
        flow_id: str,
        namespace: str
    ) -> Optional[FlowAnalysis]:
        """
        Analyze an execution flow.

        Args:
            flow_id: ExecutionFlow node ID
            namespace: Namespace

        Returns:
            FlowAnalysis with optimization recommendations
        """
        # Get flow from graph
        flow_data = self._get_flow(flow_id, namespace)
        if not flow_data:
            logger.warning(f"Flow {flow_id} not found")
            return None

        # Get all steps
        steps = self._get_steps(flow_id, namespace)
        if not steps:
            logger.warning(f"No steps found for flow {flow_id}")
            return None

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(steps)

        # Find parallel groups
        parallel_groups = self._find_parallel_groups(steps, dependency_graph)

        # Find critical path
        critical_path = self._find_critical_path(steps, dependency_graph)

        # Mark critical steps
        critical_set = set(critical_path)
        for step in steps:
            if step.step_number in critical_set:
                step.is_critical_path = True

        # Calculate performance metrics
        sequential_time, parallel_time, speedup = self._calculate_speedup(
            steps,
            parallel_groups
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            steps,
            parallel_groups,
            critical_path,
            speedup
        )

        return FlowAnalysis(
            flow_id=flow_id,
            description=flow_data.get("description", ""),
            total_steps=len(steps),
            steps=steps,
            parallel_groups=parallel_groups,
            critical_path=critical_path,
            dependency_graph=dependency_graph,
            sequential_time=sequential_time,
            parallel_time=parallel_time,
            speedup_potential=speedup,
            recommendations=recommendations,
        )

    def find_parallelization_opportunities(
        self,
        namespace: str,
        flow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find parallelization opportunities across flows.

        Args:
            namespace: Namespace to search
            flow_id: Optional specific flow ID

        Returns:
            List of parallelization opportunities
        """
        opportunities = []

        # Query for steps that can run in parallel
        query = """
        MATCH (flow:ExecutionFlow)-[:CONTAINS]->(step:Step)
        WHERE flow.namespace = $namespace
        """

        if flow_id:
            query += " AND flow.id = $flow_id"

        query += """
        OPTIONAL MATCH (step)-[:PARALLEL_WITH]->(parallel:Step)
        RETURN flow.id as flow_id,
               flow.description as flow_description,
               step.step_number as step_number,
               step.description as step_description,
               collect(parallel.step_number) as parallel_with
        ORDER BY flow.id, step.step_number
        """

        params = {"namespace": namespace}
        if flow_id:
            params["flow_id"] = flow_id

        results = self.neo4j_client.execute_query(query, params)

        # Group by flow
        flows = {}
        for result in results:
            fid = result["flow_id"]
            if fid not in flows:
                flows[fid] = {
                    "flow_id": fid,
                    "flow_description": result["flow_description"],
                    "parallel_steps": []
                }

            if result["parallel_with"]:
                flows[fid]["parallel_steps"].append({
                    "step": result["step_number"],
                    "description": result["step_description"],
                    "parallel_with": result["parallel_with"]
                })

        # Filter flows with parallelization opportunities
        for flow_data in flows.values():
            if flow_data["parallel_steps"]:
                opportunities.append(flow_data)

        return opportunities

    def _get_flow(
        self,
        flow_id: str,
        namespace: str
    ) -> Optional[Dict[str, Any]]:
        """Get flow data from graph."""
        query = """
        MATCH (flow:ExecutionFlow {id: $flow_id})
        WHERE flow.namespace = $namespace
        RETURN properties(flow) as flow
        """

        results = self.neo4j_client.execute_query(
            query,
            {"flow_id": flow_id, "namespace": namespace}
        )

        return results[0]["flow"] if results else None

    def _get_steps(
        self,
        flow_id: str,
        namespace: str
    ) -> List[FlowStep]:
        """Get all steps for a flow."""
        query = """
        MATCH (flow:ExecutionFlow {id: $flow_id})-[:CONTAINS]->(step:Step)
        WHERE step.namespace = $namespace

        OPTIONAL MATCH (step)-[:DEPENDS_ON]->(dep:Step)
        OPTIONAL MATCH (step)-[:PARALLEL_WITH]->(parallel:Step)

        RETURN step.step_number as step_number,
               step.description as description,
               step.step_type as step_type,
               step.estimated_time as estimated_time,
               collect(DISTINCT dep.step_number) as depends_on,
               collect(DISTINCT parallel.step_number) as parallel_with
        ORDER BY step.step_number
        """

        results = self.neo4j_client.execute_query(
            query,
            {"flow_id": flow_id, "namespace": namespace}
        )

        steps = []
        for result in results:
            # Filter out None values from collections
            depends_on = [d for d in result.get("depends_on", []) if d is not None]
            parallel_with = [p for p in result.get("parallel_with", []) if p is not None]

            step_type_str = result.get("step_type", "sequential")
            try:
                step_type = StepType(step_type_str)
            except ValueError:
                step_type = StepType.SEQUENTIAL

            steps.append(FlowStep(
                step_number=result["step_number"],
                description=result["description"],
                step_type=step_type,
                depends_on=depends_on,
                parallel_with=parallel_with,
                estimated_time=result.get("estimated_time"),
            ))

        return steps

    def _build_dependency_graph(
        self,
        steps: List[FlowStep]
    ) -> Dict[int, List[int]]:
        """Build dependency graph from steps."""
        graph = {}

        for step in steps:
            graph[step.step_number] = step.depends_on

        return graph

    def _find_parallel_groups(
        self,
        steps: List[FlowStep],
        dependency_graph: Dict[int, List[int]]
    ) -> List[List[int]]:
        """
        Find groups of steps that can run in parallel.

        Steps can run in parallel if:
        1. They have no dependencies on each other
        2. They have the same dependencies (can start at same time)
        """
        groups = []

        # Group by dependencies (steps with same deps can potentially parallel)
        dep_groups: Dict[tuple, List[int]] = {}

        for step in steps:
            dep_key = tuple(sorted(step.depends_on))
            if dep_key not in dep_groups:
                dep_groups[dep_key] = []
            dep_groups[dep_key].append(step.step_number)

        # Groups with multiple steps are parallel opportunities
        for group in dep_groups.values():
            if len(group) > 1:
                groups.append(sorted(group))

        # Also check explicit PARALLEL_WITH relationships
        for step in steps:
            if step.parallel_with:
                parallel_group = sorted([step.step_number] + step.parallel_with)
                if parallel_group not in groups:
                    groups.append(parallel_group)

        return groups

    def _find_critical_path(
        self,
        steps: List[FlowStep],
        dependency_graph: Dict[int, List[int]]
    ) -> List[int]:
        """
        Find critical path using longest path algorithm.

        Critical path = longest chain of dependencies.
        """
        # Build step lookup
        step_map = {s.step_number: s for s in steps}

        # Calculate earliest finish time for each step
        finish_times = {}

        def calculate_finish_time(step_num: int) -> float:
            if step_num in finish_times:
                return finish_times[step_num]

            step = step_map[step_num]
            step_time = step.estimated_time or 1.0

            # If no dependencies, finish time = step time
            if not step.depends_on:
                finish_times[step_num] = step_time
                return step_time

            # Otherwise, finish time = max(dep finish times) + step time
            max_dep_time = max(
                calculate_finish_time(dep)
                for dep in step.depends_on
            )

            finish_time = max_dep_time + step_time
            finish_times[step_num] = finish_time
            return finish_time

        # Calculate finish times for all steps
        for step in steps:
            calculate_finish_time(step.step_number)

        # Find step with max finish time
        if not finish_times:
            return []

        final_step = max(finish_times.keys(), key=lambda k: finish_times[k])

        # Backtrack to find critical path
        path = []
        current = final_step

        while current is not None:
            path.append(current)
            step = step_map[current]

            if not step.depends_on:
                break

            # Find dependency with max finish time
            current = max(
                step.depends_on,
                key=lambda d: finish_times.get(d, 0)
            )

        return list(reversed(path))

    def _calculate_speedup(
        self,
        steps: List[FlowStep],
        parallel_groups: List[List[int]]
    ) -> Tuple[float, float, float]:
        """
        Calculate potential speedup from parallelization.

        Returns:
            (sequential_time, parallel_time, speedup_factor)
        """
        # Sequential time = sum of all step times
        sequential_time = sum(
            step.estimated_time or 1.0
            for step in steps
        )

        # For parallel time, use critical path length
        step_map = {s.step_number: s for s in steps}

        # Simple estimation: subtract time saved by parallelization
        time_saved = 0.0
        for group in parallel_groups:
            # Time saved = sum of parallel steps - max step
            group_times = [step_map[s].estimated_time or 1.0 for s in group]
            time_saved += sum(group_times) - max(group_times)

        parallel_time = sequential_time - time_saved

        # Speedup factor
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0

        return sequential_time, parallel_time, speedup

    def _generate_recommendations(
        self,
        steps: List[FlowStep],
        parallel_groups: List[List[int]],
        critical_path: List[int],
        speedup: float
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        # Parallelization opportunities
        if parallel_groups:
            recommendations.append(
                f"Found {len(parallel_groups)} parallelization opportunities "
                f"that could provide {speedup:.2f}x speedup"
            )

            for idx, group in enumerate(parallel_groups, 1):
                step_desc = ", ".join(f"Step {s}" for s in group)
                recommendations.append(
                    f"Parallel Group {idx}: {step_desc} can run concurrently"
                )

        # Critical path optimization
        if critical_path:
            recommendations.append(
                f"Critical path contains {len(critical_path)} steps: "
                f"{', '.join(f'Step {s}' for s in critical_path)}"
            )
            recommendations.append(
                "Focus optimization efforts on critical path steps for maximum impact"
            )

        # Async opportunities
        async_steps = [s for s in steps if s.step_type == StepType.ASYNC]
        if async_steps:
            recommendations.append(
                f"{len(async_steps)} async steps could benefit from concurrent execution"
            )

        # If no parallelization found
        if not parallel_groups:
            recommendations.append(
                "No parallelization opportunities detected - execution is mostly sequential"
            )

        return recommendations


def get_flow_analyzer() -> FlowAnalyzer:
    """Get flow analyzer instance."""
    return FlowAnalyzer()
