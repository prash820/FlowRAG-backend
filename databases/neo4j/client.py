"""
Neo4j Client Wrapper for FlowRAG.

Provides a high-level interface for interacting with Neo4j graph database.
Database Agent is responsible for this module.
"""

from typing import Optional, Any, List, Dict
from contextlib import contextmanager
import logging

from neo4j import GraphDatabase, Driver, Session, Result
from neo4j.exceptions import ServiceUnavailable, AuthError

from config import get_settings
from .schema import (
    NodeLabel,
    RelationType,
    BaseNode,
    BaseRelationship,
    get_node_model,
    get_relationship_model,
    NODE_INDEXES,
    NODE_CONSTRAINTS,
)

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j client wrapper with connection pooling and error handling.

    Features:
    - Automatic connection management
    - Query result conversion to Pydantic models
    - Transaction support
    - Schema initialization
    - Multi-tenancy support via namespace filtering
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI (default from settings)
            user: Username (default from settings)
            password: Password (default from settings)
            database: Database name (default from settings)
        """
        settings = get_settings()

        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database

        self._driver: Optional[Driver] = None

    def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60,
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self) -> None:
        """Close Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")

    @contextmanager
    def session(self) -> Session:
        """
        Context manager for Neo4j sessions.

        Usage:
            with client.session() as session:
                result = session.run("MATCH (n) RETURN n")
        """
        if not self._driver:
            self.connect()

        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters
            namespace: Namespace filter (adds WHERE clause)

        Returns:
            List of result records as dictionaries
        """
        params = parameters or {}

        # Add namespace filter if provided
        if namespace:
            params["namespace"] = namespace

        with self.session() as session:
            result: Result = session.run(query, params)
            return [dict(record) for record in result]

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query result summary
        """
        params = parameters or {}

        with self.session() as session:
            result: Result = session.run(query, params)
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "relationships_created": summary.counters.relationships_created,
                "properties_set": summary.counters.properties_set,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_deleted": summary.counters.relationships_deleted,
            }

    # ========================================================================
    # Node Operations
    # ========================================================================

    def create_node(self, node: BaseNode, label: NodeLabel) -> str:
        """
        Create a node in the graph.

        Args:
            node: Node data model
            label: Node label

        Returns:
            Created node ID
        """
        node_dict = node.model_dump(exclude_none=True)
        node_id = node_dict.pop("id")

        query = f"""
        CREATE (n:{label.value})
        SET n = $properties
        SET n.id = $id
        RETURN n.id as id
        """

        with self.session() as session:
            result = session.run(query, {"id": node_id, "properties": node_dict})
            return result.single()["id"]

    def get_node(
        self,
        node_id: str,
        label: Optional[NodeLabel] = None,
        namespace: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.

        Args:
            node_id: Node ID
            label: Optional label filter
            namespace: Optional namespace filter

        Returns:
            Node properties or None
        """
        label_clause = f":{label.value}" if label else ""
        namespace_clause = "AND n.namespace = $namespace" if namespace else ""

        query = f"""
        MATCH (n{label_clause})
        WHERE n.id = $id {namespace_clause}
        RETURN properties(n) as node
        """

        params = {"id": node_id}
        if namespace:
            params["namespace"] = namespace

        result = self.execute_query(query, params)
        return result[0]["node"] if result else None

    def update_node(
        self,
        node_id: str,
        properties: Dict[str, Any],
        label: Optional[NodeLabel] = None,
    ) -> bool:
        """
        Update node properties.

        Args:
            node_id: Node ID
            properties: Properties to update
            label: Optional label filter

        Returns:
            True if node was updated
        """
        label_clause = f":{label.value}" if label else ""

        query = f"""
        MATCH (n{label_clause})
        WHERE n.id = $id
        SET n += $properties
        RETURN n.id as id
        """

        result = self.execute_query(query, {"id": node_id, "properties": properties})
        return len(result) > 0

    def delete_node(self, node_id: str, detach: bool = True) -> bool:
        """
        Delete a node.

        Args:
            node_id: Node ID
            detach: Whether to delete relationships too

        Returns:
            True if node was deleted
        """
        detach_clause = "DETACH " if detach else ""

        query = f"""
        MATCH (n)
        WHERE n.id = $id
        {detach_clause}DELETE n
        RETURN count(n) as deleted
        """

        result = self.execute_query(query, {"id": node_id})
        return result[0]["deleted"] > 0 if result else False

    # ========================================================================
    # Relationship Operations
    # ========================================================================

    def create_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationType,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Create a relationship between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type
            properties: Relationship properties

        Returns:
            True if relationship was created
        """
        props = properties or {}

        query = f"""
        MATCH (a), (b)
        WHERE a.id = $from_id AND b.id = $to_id
        MERGE (a)-[r:{rel_type.value}]->(b)
        SET r += $properties
        RETURN r
        """

        result = self.execute_query(
            query,
            {"from_id": from_id, "to_id": to_id, "properties": props}
        )
        return len(result) > 0

    def get_relationships(
        self,
        node_id: str,
        direction: str = "both",
        rel_type: Optional[RelationType] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a node.

        Args:
            node_id: Node ID
            direction: "outgoing", "incoming", or "both"
            rel_type: Optional relationship type filter

        Returns:
            List of relationships with connected nodes
        """
        rel_pattern = f":{rel_type.value}" if rel_type else ""

        if direction == "outgoing":
            pattern = f"(n)-[r{rel_pattern}]->(m)"
        elif direction == "incoming":
            pattern = f"(n)<-[r{rel_pattern}]-(m)"
        else:
            pattern = f"(n)-[r{rel_pattern}]-(m)"

        query = f"""
        MATCH {pattern}
        WHERE n.id = $id
        RETURN type(r) as type, properties(r) as props, properties(m) as node
        """

        return self.execute_query(query, {"id": node_id})

    # ========================================================================
    # Graph Traversal
    # ========================================================================

    def find_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5,
        rel_types: Optional[List[RelationType]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find path between two nodes.

        Args:
            from_id: Start node ID
            to_id: End node ID
            max_depth: Maximum path length
            rel_types: Optional relationship type filters

        Returns:
            Path information
        """
        rel_filter = ""
        if rel_types:
            types = "|".join([rt.value for rt in rel_types])
            rel_filter = f":{types}"

        query = f"""
        MATCH path = shortestPath((a)-[{rel_filter}*..{max_depth}]-(b))
        WHERE a.id = $from_id AND b.id = $to_id
        RETURN [node IN nodes(path) | properties(node)] as nodes,
               [rel IN relationships(path) | type(rel)] as relationships
        """

        return self.execute_query(query, {"from_id": from_id, "to_id": to_id})

    def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get neighboring nodes up to specified depth.

        Args:
            node_id: Starting node ID
            depth: Traversal depth
            namespace: Optional namespace filter

        Returns:
            List of neighbor nodes
        """
        namespace_clause = "AND m.namespace = $namespace" if namespace else ""

        query = f"""
        MATCH (n)-[*1..{depth}]-(m)
        WHERE n.id = $id {namespace_clause}
        RETURN DISTINCT properties(m) as node
        """

        params = {"id": node_id}
        if namespace:
            params["namespace"] = namespace

        return self.execute_query(query, params)

    # ========================================================================
    # Schema Management
    # ========================================================================

    def initialize_schema(self) -> None:
        """Create indexes and constraints."""
        logger.info("Initializing Neo4j schema...")

        with self.session() as session:
            # Create constraints
            for label, property_name in NODE_CONSTRAINTS:
                query = f"""
                CREATE CONSTRAINT IF NOT EXISTS
                FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE
                """
                session.run(query)
                logger.info(f"Created constraint on {label}.{property_name}")

            # Create indexes
            for label, property_name in NODE_INDEXES:
                query = f"""
                CREATE INDEX IF NOT EXISTS
                FOR (n:{label}) ON (n.{property_name})
                """
                session.run(query)
                logger.info(f"Created index on {label}.{property_name}")

        logger.info("Schema initialization complete")

    def clear_database(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Clear all nodes and relationships.

        Args:
            namespace: If provided, only clear this namespace

        Returns:
            Deletion summary
        """
        if namespace:
            query = """
            MATCH (n {namespace: $namespace})
            DETACH DELETE n
            """
            params = {"namespace": namespace}
        else:
            query = "MATCH (n) DETACH DELETE n"
            params = {}

        return self.execute_write(query, params)

    def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get database statistics.

        Args:
            namespace: Optional namespace filter

        Returns:
            Database statistics
        """
        namespace_clause = "WHERE n.namespace = $namespace" if namespace else ""
        params = {"namespace": namespace} if namespace else {}

        node_count_query = f"MATCH (n) {namespace_clause} RETURN count(n) as count"
        rel_count_query = f"""
        MATCH (n)-[r]->()
        {namespace_clause}
        RETURN count(r) as count
        """

        with self.session() as session:
            node_count = session.run(node_count_query, params).single()["count"]
            rel_count = session.run(rel_count_query, params).single()["count"]

        return {
            "nodes": node_count,
            "relationships": rel_count,
            "namespace": namespace,
        }


# Singleton instance
_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get Neo4j client singleton."""
    global _client
    if _client is None:
        _client = Neo4jClient()
        _client.connect()
    return _client
