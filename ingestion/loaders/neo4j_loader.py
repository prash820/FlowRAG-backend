"""
Neo4j data loader for code structures.

Loads parsed code units into Neo4j graph database.
Ingestion Agent is responsible for this module.
"""

from typing import List, Dict, Any
import logging

from databases import get_neo4j_client, NodeLabel, RelationType
from ingestion.parsers.base import ParseResult, CodeUnit

logger = logging.getLogger(__name__)


class Neo4jLoader:
    """Loader for ingesting code into Neo4j."""

    def __init__(self):
        """Initialize Neo4j loader."""
        self.client = get_neo4j_client()

    def load_parse_result(self, result: ParseResult) -> Dict[str, Any]:
        """
        Load a parse result into Neo4j.

        Args:
            result: Parse result with code units and relationships

        Returns:
            Load statistics
        """
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
        }

        # Load all code units as nodes
        for unit in result.all_units:
            try:
                self.client.create_node(unit, unit.type)
                stats["nodes_created"] += 1
            except Exception as e:
                logger.error(f"Failed to create node for {unit.name}: {e}")

        # Create containment relationships
        stats["relationships_created"] += self._create_containment_relationships(result)

        # Create call relationships
        stats["relationships_created"] += self._create_call_relationships(result)

        # Create import relationships
        stats["relationships_created"] += self._create_import_relationships(result)

        logger.info(f"Loaded {stats['nodes_created']} nodes, {stats['relationships_created']} relationships")

        return stats

    def _create_containment_relationships(self, result: ParseResult) -> int:
        """Create CONTAINS relationships (module->class, class->method)."""
        count = 0

        # Module contains classes
        if result.modules and result.classes:
            module_id = result.modules[0].id

            for cls in result.classes:
                try:
                    self.client.create_relationship(
                        from_id=module_id,
                        to_id=cls.id,
                        rel_type=RelationType.CONTAINS,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create containment relationship: {e}")

        # Module contains functions
        if result.modules and result.functions:
            module_id = result.modules[0].id

            for func in result.functions:
                try:
                    self.client.create_relationship(
                        from_id=module_id,
                        to_id=func.id,
                        rel_type=RelationType.CONTAINS,
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to create containment relationship: {e}")

        # Classes contain methods
        for cls in result.classes:
            for method in result.methods:
                # Simple heuristic: if method is in same file and after class
                if (method.file_path == cls.file_path and
                    method.line_start > cls.line_start and
                    method.line_end < cls.line_end):
                    try:
                        self.client.create_relationship(
                            from_id=cls.id,
                            to_id=method.id,
                            rel_type=RelationType.CONTAINS,
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to create containment relationship: {e}")

        return count

    def _create_call_relationships(self, result: ParseResult) -> int:
        """Create CALLS relationships between functions."""
        count = 0

        # Create a name->id mapping
        name_to_id = {
            unit.name: unit.id
            for unit in result.all_units
            if unit.type in (NodeLabel.FUNCTION, NodeLabel.METHOD)
        }

        # Create relationships based on call information
        for unit in result.all_units:
            for called_name in unit.calls:
                # Find matching function/method
                if called_name in name_to_id:
                    try:
                        self.client.create_relationship(
                            from_id=unit.id,
                            to_id=name_to_id[called_name],
                            rel_type=RelationType.CALLS,
                            properties={"call_count": 1},
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to create call relationship: {e}")

        return count

    def _create_import_relationships(self, result: ParseResult) -> int:
        """Create IMPORTS relationships."""
        count = 0

        # For now, store imports as node properties
        # Full import graph would require cross-file analysis

        return count

    def delete_namespace(self, namespace: str) -> Dict[str, Any]:
        """
        Delete all data for a namespace.

        Args:
            namespace: Namespace to delete

        Returns:
            Deletion stats
        """
        return self.client.clear_database(namespace=namespace)


def get_neo4j_loader() -> Neo4jLoader:
    """Get Neo4j loader instance."""
    return Neo4jLoader()
