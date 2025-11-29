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

        # Create a name->id mapping for functions/methods
        name_to_id = {
            unit.name: unit.id
            for unit in result.all_units
            if unit.type in (NodeLabel.FUNCTION, NodeLabel.METHOD)
        }

        # Create a file_path->id mapping for file-level calls
        file_to_units = {}
        for unit in result.all_units:
            if unit.file_path not in file_to_units:
                file_to_units[unit.file_path] = []
            file_to_units[unit.file_path].append(unit)

        # Process ParseResult-level calls (from tree-sitter extraction)
        for call_info in result.calls:
            from_file = call_info.get('from', '')
            to_name = call_info.get('to', '')

            # Find functions in the source file that might make this call
            if from_file in file_to_units and to_name in name_to_id:
                # For simplicity, create relationship from file's first function/class
                # In a more sophisticated version, we'd track which function makes which call
                source_units = [u for u in file_to_units[from_file]
                               if u.type in (NodeLabel.FUNCTION, NodeLabel.METHOD, NodeLabel.CLASS)]
                if source_units:
                    try:
                        self.client.create_relationship(
                            from_id=source_units[0].id,
                            to_id=name_to_id[to_name],
                            rel_type=RelationType.CALLS,
                            properties={"call_count": 1},
                        )
                        count += 1
                    except Exception as e:
                        logger.error(f"Failed to create call relationship: {e}")

        # Also process unit-level calls (if populated by any parser)
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
        """Create IMPORTS relationships between files/modules."""
        count = 0

        # Create a file_path->unit mapping
        file_to_unit = {}
        for unit in result.all_units:
            # Use the first unit (typically a class or main function) to represent the file
            if unit.file_path not in file_to_unit:
                file_to_unit[unit.file_path] = unit.id

        # Process ParseResult-level imports
        for import_info in result.imports:
            from_file = import_info.get('from', '')
            to_module = import_info.get('to', '')

            # Create import relationship from source file's first unit
            if from_file in file_to_unit:
                # For now, create a simple module node for the imported module
                # In a more sophisticated version, we'd resolve module paths to actual files
                try:
                    # Create or get the target module node
                    target_id = f"module_{to_module}_{result.namespace}"

                    # Create the import relationship
                    self.client.create_relationship(
                        from_id=file_to_unit[from_file],
                        to_id=target_id,
                        rel_type=RelationType.IMPORTS,
                        properties={"module": to_module},
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Failed to create import relationship for {to_module}: {e}")

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
