"""
Neo4j data loader for code structures.

Loads parsed code units into Neo4j graph database.
Ingestion Agent is responsible for this module.
"""

from typing import List, Dict, Any, Optional
import logging

from databases import get_neo4j_client, NodeLabel, RelationType
from ingestion.parsers.base import ParseResult, CodeUnit
from config.feature_flags import get_feature_flags

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

    def load_data_flows(
        self,
        data_flows: List[Dict[str, Any]],
        waves: List[Dict[str, Any]],
        namespace: str,
        source_file: str,
    ) -> Dict[str, Any]:
        """
        Load data flow relationships into Neo4j.

        Feature Flag: enable_data_flow_relationships

        Args:
            data_flows: List of data flow edges from DataFlowExtractor
            waves: List of parallelization waves
            namespace: Namespace for the code
            source_file: Source file path

        Returns:
            Load statistics
        """
        flags = get_feature_flags()

        if not flags.enable_data_flow_relationships:
            logger.debug("Data flow relationships disabled by feature flag")
            return {"data_flows_created": 0, "waves_created": 0, "skipped": True}

        stats = {
            "data_flows_created": 0,
            "waves_created": 0,
            "skipped": False,
        }

        # Create DATA_FLOWS_TO relationships using Cypher
        # Strategy: Find functions whose code contains both the source and target calls,
        # then create relationships between the external services/methods being called
        file_suffix = source_file.split('/')[-1] if '/' in source_file else source_file

        for edge in data_flows:
            try:
                source_call = edge.source_call if hasattr(edge, 'source_call') else edge.get('source_call')
                target_call = edge.target_call if hasattr(edge, 'target_call') else edge.get('target_call')
                field = edge.field if hasattr(edge, 'field') else edge.get('field')
                variable_name = edge.variable_name if hasattr(edge, 'variable_name') else edge.get('variable_name')
                source_line = edge.source_line if hasattr(edge, 'source_line') else edge.get('source_line')
                target_line = edge.target_line if hasattr(edge, 'target_line') else edge.get('target_line')
                is_conditional = edge.is_conditional if hasattr(edge, 'is_conditional') else edge.get('is_conditional', False)
                condition = edge.condition if hasattr(edge, 'condition') else edge.get('condition')

                if not source_call or not target_call:
                    continue

                # Extract the method name from the call chain
                source_method = source_call.split('.')[-1] if '.' in source_call else source_call
                target_method = target_call.split('.')[-1] if '.' in target_call else target_call

                properties = {
                    "field": field or "self",
                    "source_variable": variable_name or "",
                    "source_line": source_line or 0,
                    "target_line": target_line or 0,
                    "is_conditional": is_conditional,
                    "namespace": namespace,
                    "source_file": source_file,
                    "source_call": source_call,
                    "target_call": target_call,
                }
                if condition:
                    properties["condition"] = condition

                # Find the containing function that has both calls in its code
                # and create a DATA_FLOWS_TO relationship showing the data dependency
                query = """
                MATCH (container)
                WHERE container.namespace = $namespace
                  AND container.file_path CONTAINS $file_suffix
                  AND container.code IS NOT NULL
                  AND container.code CONTAINS $source_method
                  AND container.code CONTAINS $target_method
                  AND (container:Function OR container:Method)
                WITH container LIMIT 1

                // Create or find placeholder nodes for the external calls
                MERGE (source_op:ExternalCall {
                    name: $source_call,
                    method: $source_method,
                    namespace: $namespace,
                    file_path: $source_file
                })
                MERGE (target_op:ExternalCall {
                    name: $target_call,
                    method: $target_method,
                    namespace: $namespace,
                    file_path: $source_file
                })

                // Link container to the external calls
                MERGE (container)-[:CALLS]->(source_op)
                MERGE (container)-[:CALLS]->(target_op)

                // Create the data flow relationship between external calls
                MERGE (source_op)-[r:DATA_FLOWS_TO]->(target_op)
                SET r += $properties

                RETURN count(r) as created
                """

                result = self.client.execute_query(
                    query,
                    {
                        "namespace": namespace,
                        "file_suffix": file_suffix,
                        "source_method": source_method,
                        "target_method": target_method,
                        "source_call": source_call,
                        "target_call": target_call,
                        "source_file": source_file,
                        "properties": properties,
                    }
                )

                if result and result[0].get("created", 0) > 0:
                    stats["data_flows_created"] += 1

            except Exception as e:
                logger.debug(f"Failed to create data flow relationship: {e}")

        # Create wave relationships if parallelization is enabled
        # Store wave information as properties on nodes rather than separate relationships
        if flags.enable_parallelization_waves and waves:
            try:
                file_suffix = source_file.split('/')[-1] if '/' in source_file else source_file

                for wave in waves:
                    wave_num = wave.wave_number if hasattr(wave, 'wave_number') else wave.get('wave_number')
                    operations = wave.operations if hasattr(wave, 'operations') else wave.get('operations', [])

                    for op in operations:
                        # Extract method name from operation (e.g., "customerClient.getCustomerData" -> "getCustomerData")
                        method_name = op.split('.')[-1] if op else None
                        if not method_name:
                            continue

                        # Update node with wave information
                        query = """
                        MATCH (n)
                        WHERE n.namespace = $namespace
                          AND n.file_path CONTAINS $file_suffix
                          AND (n.name = $method_name OR $operation IN n.calls)
                        SET n.parallelization_wave = $wave_num,
                            n.wave_size = $wave_size,
                            n.can_parallelize = true
                        RETURN count(n) as updated
                        """

                        result = self.client.execute_query(
                            query,
                            {
                                "namespace": namespace,
                                "file_suffix": file_suffix,
                                "method_name": method_name,
                                "operation": op,
                                "wave_num": wave_num,
                                "wave_size": len(operations),
                            }
                        )

                        if result and result[0].get("updated", 0) > 0:
                            stats["waves_created"] += 1

            except Exception as e:
                logger.debug(f"Failed to create wave properties: {e}")

        if flags.log_feature_usage and (stats["data_flows_created"] > 0 or stats["waves_created"] > 0):
            logger.info(
                f"[Feature: data_flow_relationships] Created {stats['data_flows_created']} "
                f"data flow edges, {stats['waves_created']} wave assignments"
            )

        return stats

    def load_api_calls(
        self,
        api_calls: List[Dict[str, Any]],
        source_namespace: str,
        url_to_namespace_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Load inter-service API calls as CALLS_API relationships.

        This creates cross-namespace relationships when one service calls
        another service's API endpoint.

        Args:
            api_calls: List of detected API calls (from InterServiceCallDetector)
            source_namespace: Namespace of the calling service
            url_to_namespace_map: Optional mapping of URLs/domains to target namespaces

        Returns:
            Load statistics
        """
        stats = {
            "api_calls_created": 0,
            "skipped": 0,
            "errors": [],
        }

        # Use only user-provided mapping - no hardcoded service mappings
        url_map = url_to_namespace_map or {}

        for call in api_calls:
            try:
                # Extract call info - support both dict and object
                if hasattr(call, 'to_dict'):
                    call_data = call.to_dict()
                elif isinstance(call, dict):
                    call_data = call
                else:
                    # Try to extract attributes
                    call_data = {
                        'call_type': getattr(call, 'call_type', 'http'),
                        'source_file': getattr(call, 'source_file', ''),
                        'source_function': getattr(call, 'source_function', ''),
                        'target_service': getattr(call, 'target_service', None),
                        'endpoint': getattr(call, 'endpoint', None),
                        'method': getattr(call, 'method', 'GET'),
                        'line_number': getattr(call, 'line_number', 0),
                        'code_snippet': getattr(call, 'code_snippet', ''),
                    }

                call_type = call_data.get('call_type', 'http')
                source_file = call_data.get('source_file', '')
                source_function = call_data.get('source_function', '')
                target_service = call_data.get('target_service')
                endpoint = call_data.get('endpoint', '')
                http_method = call_data.get('method', 'GET') or 'GET'
                line_number = call_data.get('line_number', 0)

                # Only process HTTP calls for now
                if call_type != 'http':
                    stats["skipped"] += 1
                    continue

                if not endpoint:
                    stats["skipped"] += 1
                    continue

                # Determine target namespace from URL
                target_namespace = None
                endpoint_lower = endpoint.lower()

                for url_pattern, namespace in url_map.items():
                    if url_pattern.lower() in endpoint_lower:
                        target_namespace = namespace
                        break

                # If no target namespace found, use the detected target_service
                if not target_namespace and target_service:
                    # Try to match target_service to a namespace
                    for url_pattern, namespace in url_map.items():
                        if target_service.lower() in url_pattern.lower():
                            target_namespace = namespace
                            break

                if not target_namespace:
                    # Create a generic external service node
                    target_namespace = f"external:{target_service or 'unknown'}"

                # Skip self-calls
                if target_namespace == source_namespace:
                    stats["skipped"] += 1
                    continue

                # Create the CALLS_API relationship using Cypher
                # Find the source function/file node and create relationship to target namespace
                query = """
                // Find source node (function or file that makes the call)
                MATCH (source)
                WHERE source.namespace = $source_namespace
                  AND (
                    (source.file_path CONTAINS $source_file_suffix AND source.name = $source_function)
                    OR (source.file_path CONTAINS $source_file_suffix AND source:Function)
                    OR (source.file_path CONTAINS $source_file_suffix AND source:Method)
                  )
                WITH source LIMIT 1

                // Create or find target namespace node
                MERGE (target:Namespace {name: $target_namespace})

                // Create the CALLS_API relationship
                MERGE (source)-[r:CALLS_API {
                    target_url: $endpoint,
                    http_method: $http_method,
                    source_function: $source_function,
                    source_file: $source_file,
                    line_number: $line_number,
                    target_service: $target_namespace
                }]->(target)

                RETURN count(r) as created
                """

                # Extract file suffix for matching
                source_file_suffix = source_file.split('/')[-1] if '/' in source_file else source_file

                result = self.client.execute_query(
                    query,
                    {
                        "source_namespace": source_namespace,
                        "source_file_suffix": source_file_suffix,
                        "source_function": source_function,
                        "target_namespace": target_namespace,
                        "endpoint": endpoint,
                        "http_method": http_method.upper() if http_method else 'GET',
                        "source_file": source_file,
                        "line_number": line_number or 0,
                    }
                )

                if result and result[0].get("created", 0) > 0:
                    stats["api_calls_created"] += 1
                    logger.info(
                        f"Created CALLS_API: {source_namespace}:{source_function} -> "
                        f"{target_namespace} ({http_method} {endpoint})"
                    )
                else:
                    # Try alternative: create relationship from any node in the source file
                    alt_query = """
                    // Find any node from the source file
                    MATCH (source)
                    WHERE source.namespace = $source_namespace
                      AND source.file_path CONTAINS $source_file_suffix
                    WITH source LIMIT 1

                    // Create or find target namespace node
                    MERGE (target:Namespace {name: $target_namespace})

                    // Create the CALLS_API relationship
                    MERGE (source)-[r:CALLS_API {
                        target_url: $endpoint,
                        http_method: $http_method,
                        source_function: $source_function,
                        source_file: $source_file,
                        line_number: $line_number,
                        target_service: $target_namespace
                    }]->(target)

                    RETURN count(r) as created
                    """

                    alt_result = self.client.execute_query(
                        alt_query,
                        {
                            "source_namespace": source_namespace,
                            "source_file_suffix": source_file_suffix,
                            "source_function": source_function,
                            "target_namespace": target_namespace,
                            "endpoint": endpoint,
                            "http_method": http_method.upper() if http_method else 'GET',
                            "source_file": source_file,
                            "line_number": line_number or 0,
                        }
                    )

                    if alt_result and alt_result[0].get("created", 0) > 0:
                        stats["api_calls_created"] += 1
                        logger.info(
                            f"Created CALLS_API (alt): {source_namespace}:{source_file_suffix} -> "
                            f"{target_namespace} ({http_method} {endpoint})"
                        )

            except Exception as e:
                error_msg = f"Failed to create API call relationship: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        logger.info(
            f"Loaded {stats['api_calls_created']} API call relationships, "
            f"skipped {stats['skipped']}, errors: {len(stats['errors'])}"
        )

        return stats

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
