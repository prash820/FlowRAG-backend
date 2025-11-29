"""
Code flow tracer using Neo4j graph traversal.

Traces execution flows through code by following CALLS and IMPORTS relationships.
"""

import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from databases.neo4j.client import Neo4jClient
from config import settings

logger = logging.getLogger(__name__)


class CodeTracer:
    """Traces code execution flows using graph traversal."""

    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j = neo4j_client

    def find_entry_points(self, namespace: str, pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find potential entry points in the application.

        Entry points are:
        - Files matching common patterns (page.tsx, index.*, main.*, app.*)
        - Route handler files
        - Main functions

        Args:
            namespace: Namespace to search in
            pattern: Optional pattern to match (e.g., 'page.tsx', 'main')

        Returns:
            List of entry point nodes
        """
        if pattern:
            # Search for specific pattern
            query = """
            MATCH (n)
            WHERE n.namespace = $namespace
            AND (
                n.file_path CONTAINS $pattern
                OR n.name CONTAINS $pattern
            )
            RETURN n.id as id, n.name as name, n.type as type,
                   n.file_path as file_path, n.code as code,
                   n.start_line as line_number
            LIMIT 20
            """
            params = {"namespace": namespace, "pattern": pattern}
        else:
            # Find common entry point patterns
            query = """
            MATCH (n)
            WHERE n.namespace = $namespace
            AND (
                n.file_path =~ '.*/(page|index|main|app|routes?)\\.(tsx?|jsx?|go|py)$'
                OR n.name IN ['main', 'Main', 'index', 'handler', 'Handler']
                OR n.file_path =~ '.*/app/.*page\\.tsx$'
            )
            RETURN n.id as id, n.name as name, n.type as type,
                   n.file_path as file_path, n.code as code,
                   n.start_line as line_number
            ORDER BY
                CASE
                    WHEN n.file_path =~ '.*/page\\.tsx$' THEN 1
                    WHEN n.file_path =~ '.*/index\\.' THEN 2
                    WHEN n.file_path =~ '.*/main\\.' THEN 3
                    ELSE 4
                END
            LIMIT 20
            """
            params = {"namespace": namespace}

        try:
            results = self.neo4j.execute_query(query, params)
            return results
        except Exception as e:
            logger.error(f"Failed to find entry points: {e}")
            return []

    def trace_from_node(
        self,
        node_id: str,
        namespace: str,
        max_depth: int = 10,
        include_code: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Trace code flow starting from a specific node.

        Follows CALLS and IMPORTS relationships to build execution flow.

        Args:
            node_id: Starting node ID
            namespace: Namespace
            max_depth: Maximum traversal depth
            include_code: Whether to include code snippets

        Returns:
            Tuple of (nodes, relationships)
        """
        nodes = []
        relationships = []
        visited: Set[str] = set()

        def traverse(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)

            # Get current node
            node_query = """
            MATCH (n)
            WHERE n.id = $node_id AND n.namespace = $namespace
            RETURN n.id as id, n.name as name, n.type as type,
                   n.file_path as file_path,
                   """ + ("n.code as code, " if include_code else "'[code hidden]' as code, ") + """
                   n.start_line as line_number
            """

            node_results = self.neo4j.execute_query(
                node_query,
                {"node_id": current_id, "namespace": namespace}
            )

            if not node_results:
                return

            node = node_results[0]
            node['depth'] = depth
            nodes.append(node)

            # Get outgoing CALLS and IMPORTS relationships
            rel_query = """
            MATCH (from)-[r:CALLS|IMPORTS]->(to)
            WHERE from.id = $node_id
            AND from.namespace = $namespace
            AND to.namespace = $namespace
            RETURN r, to.id as to_id, type(r) as rel_type
            LIMIT 50
            """

            rel_results = self.neo4j.execute_query(
                rel_query,
                {"node_id": current_id, "namespace": namespace}
            )

            for rel_record in rel_results:
                to_id = rel_record['to_id']
                rel_type = rel_record['rel_type']
                rel_props = dict(rel_record['r'])

                # Add relationship
                relationships.append({
                    'from_id': current_id,
                    'to_id': to_id,
                    'type': rel_type,
                    'properties': rel_props
                })

                # Recursively traverse
                traverse(to_id, depth + 1)

        try:
            traverse(node_id, 0)
            return nodes, relationships
        except Exception as e:
            logger.error(f"Failed to trace from node {node_id}: {e}")
            return [], []

    def trace_linear_flow(
        self,
        namespace: str,
        entry_point: Optional[str] = None,
        max_depth: int = 10,
        include_code: bool = True
    ) -> Dict[str, Any]:
        """
        Trace a linear code flow from entry point.

        This is the main method for linear flow analysis.

        Args:
            namespace: Namespace to trace
            entry_point: Entry point pattern (optional)
            max_depth: Maximum traversal depth
            include_code: Whether to include code snippets

        Returns:
            Dictionary containing nodes, relationships, and metadata
        """
        # Find entry points
        logger.info(f"Finding entry points in namespace {namespace} with pattern: {entry_point}")
        entry_nodes = self.find_entry_points(namespace, entry_point)

        if not entry_nodes:
            return {
                'success': False,
                'message': f'No entry points found for pattern: {entry_point or "default"}',
                'nodes': [],
                'relationships': [],
                'total_nodes': 0,
                'total_relationships': 0,
                'max_depth_reached': 0
            }

        # Use the first entry point
        start_node = entry_nodes[0]
        logger.info(f"Starting trace from: {start_node['name']} ({start_node['file_path']})")

        # Trace from this entry point
        nodes, relationships = self.trace_from_node(
            start_node['id'],
            namespace,
            max_depth,
            include_code
        )

        max_depth_reached = max([n['depth'] for n in nodes]) if nodes else 0

        return {
            'success': True,
            'entry_point': f"{start_node['name']} ({start_node['file_path']})",
            'nodes': nodes,
            'relationships': relationships,
            'total_nodes': len(nodes),
            'total_relationships': len(relationships),
            'max_depth_reached': max_depth_reached,
            'message': f'Traced {len(nodes)} nodes and {len(relationships)} relationships'
        }


# Singleton instance
_tracer: Optional[CodeTracer] = None


def get_code_tracer() -> CodeTracer:
    """Get or create the code tracer instance."""
    global _tracer

    if _tracer is None:
        from ingestion import get_neo4j_loader
        neo4j_loader = get_neo4j_loader()
        _tracer = CodeTracer(neo4j_loader.client)

    return _tracer
