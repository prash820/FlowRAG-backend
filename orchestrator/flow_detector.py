"""
Flow Detection for FlowRAG

Analyzes execution flows in microservices:
- Detects API entry points (HTTP endpoints, handlers)
- Builds call chains (request → processing → response)
- Tracks data flow through functions
- Identifies control flow patterns
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class EntryPointType(Enum):
    """Types of entry points in code."""
    HTTP_HANDLER = "http_handler"  # HTTP endpoint handlers
    GRPC_METHOD = "grpc_method"    # gRPC service methods
    MESSAGE_HANDLER = "message_handler"  # Message queue handlers
    MAIN_FUNCTION = "main"         # Main entry point
    CRON_JOB = "cron_job"         # Scheduled tasks
    CLI_COMMAND = "cli_command"    # CLI commands


class FlowNodeType(Enum):
    """Types of nodes in execution flow."""
    ENTRY = "entry"              # Entry point
    VALIDATION = "validation"    # Input validation
    PROCESSING = "processing"    # Business logic
    DATA_ACCESS = "data_access"  # Database/storage
    EXTERNAL_CALL = "external"   # External service call
    RESPONSE = "response"        # Response generation
    ERROR_HANDLER = "error"      # Error handling


@dataclass
class EntryPoint:
    """Represents an API entry point."""
    function_name: str
    function_id: str
    entry_type: EntryPointType
    http_method: Optional[str] = None  # GET, POST, etc.
    route: Optional[str] = None        # /api/users
    service: Optional[str] = None
    file_path: str = ""
    line_start: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_name": self.function_name,
            "function_id": self.function_id,
            "entry_type": self.entry_type.value,
            "http_method": self.http_method,
            "route": self.route,
            "service": self.service,
            "file_path": self.file_path,
            "line_start": self.line_start
        }


@dataclass
class FlowNode:
    """Represents a node in execution flow."""
    function_id: str
    function_name: str
    node_type: FlowNodeType
    depth: int  # Depth in call chain
    file_path: str = ""
    line_start: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "function_id": self.function_id,
            "function_name": self.function_name,
            "node_type": self.node_type.value,
            "depth": self.depth,
            "file_path": self.file_path,
            "line_start": self.line_start
        }


@dataclass
class ExecutionFlow:
    """Represents a complete execution flow from entry to exit."""
    entry_point: EntryPoint
    flow_nodes: List[FlowNode]
    call_chain: List[str]  # Ordered list of function names
    max_depth: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_point": self.entry_point.to_dict(),
            "flow_nodes": [node.to_dict() for node in self.flow_nodes],
            "call_chain": self.call_chain,
            "max_depth": self.max_depth
        }


class FlowDetector:
    """Detects and analyzes execution flows in code."""

    # Patterns for detecting entry points
    ENTRY_POINT_PATTERNS = {
        # Go patterns
        "go": {
            EntryPointType.HTTP_HANDLER: [
                "Handle",  # http.HandleFunc
                "Handler",
                "ServeHTTP",
                "MakeHTTPHandler",
            ],
            EntryPointType.MAIN_FUNCTION: ["main"],
        },

        # JavaScript patterns
        "javascript": {
            EntryPointType.HTTP_HANDLER: [
                "app.get",
                "app.post",
                "app.put",
                "app.delete",
                "router.get",
                "router.post",
                "express()",
            ],
            EntryPointType.MAIN_FUNCTION: ["main", "start", "init"],
        },

        # Java patterns
        "java": {
            EntryPointType.HTTP_HANDLER: [
                "@GetMapping",
                "@PostMapping",
                "@PutMapping",
                "@DeleteMapping",
                "@RequestMapping",
                "@RestController",
            ],
            EntryPointType.MAIN_FUNCTION: ["main"],
        }
    }

    # Patterns for classifying function types
    FUNCTION_TYPE_PATTERNS = {
        FlowNodeType.VALIDATION: [
            "validate", "check", "verify", "ensure", "assert",
            "sanitize", "normalize"
        ],
        FlowNodeType.DATA_ACCESS: [
            "get", "find", "fetch", "load", "save", "update",
            "delete", "insert", "query", "repository", "dao"
        ],
        FlowNodeType.PROCESSING: [
            "process", "handle", "execute", "compute", "calculate",
            "transform", "convert", "parse"
        ],
        FlowNodeType.RESPONSE: [
            "response", "reply", "return", "send", "write",
            "encode", "serialize", "marshal"
        ],
        FlowNodeType.ERROR_HANDLER: [
            "error", "catch", "recover", "panic", "exception"
        ]
    }

    def __init__(self, neo4j_client):
        """Initialize flow detector with Neo4j client."""
        self.client = neo4j_client

    def detect_entry_points(self, service: str = None) -> List[EntryPoint]:
        """
        Detect all entry points in the codebase.

        Args:
            service: Optional service name to filter by

        Returns:
            List of detected entry points
        """
        query = """
        MATCH (n)
        WHERE n.namespace STARTS WITH 'sock_shop:'
        AND n.type IN ['Function', 'Method']
        """

        if service:
            query += f"\nAND n.namespace = 'sock_shop:{service}'"

        query += "\nRETURN n.id as id, n.name as name, n.language as language, " \
                 "n.signature as signature, n.namespace as namespace, " \
                 "n.file_path as file_path, n.line_start as line_start, " \
                 "n.code as code"

        results = self.client.execute_query(query, {})

        entry_points = []
        for row in results:
            entry_type = self._classify_entry_point(
                row['name'],
                row.get('signature', ''),
                row.get('code', ''),
                row['language']
            )

            if entry_type:
                # Extract HTTP method and route if available
                http_method, route = self._extract_http_info(
                    row.get('code', ''),
                    row['language']
                )

                service_name = row['namespace'].split(':')[1] if ':' in row['namespace'] else None

                entry_points.append(EntryPoint(
                    function_name=row['name'],
                    function_id=row['id'],
                    entry_type=entry_type,
                    http_method=http_method,
                    route=route,
                    service=service_name,
                    file_path=row.get('file_path', ''),
                    line_start=row.get('line_start', 0)
                ))

        return entry_points

    def build_execution_flow(self, entry_point_id: str, max_depth: int = 10) -> ExecutionFlow:
        """
        Build complete execution flow starting from an entry point.

        Args:
            entry_point_id: ID of the entry point function
            max_depth: Maximum depth to traverse

        Returns:
            Complete execution flow
        """
        # Get entry point details
        entry_query = """
        MATCH (n)
        WHERE n.id = $entry_id
        RETURN n.id as id, n.name as name, n.language as language,
               n.namespace as namespace, n.file_path as file_path,
               n.line_start as line_start, n.code as code
        """

        entry_results = self.client.execute_query(entry_query, {"entry_id": entry_point_id})
        if not entry_results:
            raise ValueError(f"Entry point {entry_point_id} not found")

        entry_data = entry_results[0]

        # Create entry point
        entry_type = self._classify_entry_point(
            entry_data['name'],
            "",
            entry_data.get('code', ''),
            entry_data['language']
        )

        http_method, route = self._extract_http_info(
            entry_data.get('code', ''),
            entry_data['language']
        )

        service_name = entry_data['namespace'].split(':')[1] if ':' in entry_data['namespace'] else None

        entry_point = EntryPoint(
            function_name=entry_data['name'],
            function_id=entry_data['id'],
            entry_type=entry_type or EntryPointType.MAIN_FUNCTION,
            http_method=http_method,
            route=route,
            service=service_name,
            file_path=entry_data.get('file_path', ''),
            line_start=entry_data.get('line_start', 0)
        )

        # Build call chain using BFS
        flow_nodes = []
        call_chain = []
        visited = set()

        self._build_flow_recursive(
            entry_point_id,
            entry_data['name'],
            0,
            max_depth,
            visited,
            flow_nodes,
            call_chain,
            entry_data.get('file_path', ''),
            entry_data.get('line_start', 0)
        )

        return ExecutionFlow(
            entry_point=entry_point,
            flow_nodes=flow_nodes,
            call_chain=call_chain,
            max_depth=len(call_chain)
        )

    def _build_flow_recursive(
        self,
        function_id: str,
        function_name: str,
        depth: int,
        max_depth: int,
        visited: Set[str],
        flow_nodes: List[FlowNode],
        call_chain: List[str],
        file_path: str,
        line_start: int
    ):
        """Recursively build execution flow."""
        if depth >= max_depth or function_id in visited:
            return

        visited.add(function_id)
        call_chain.append(function_name)

        # Classify function type
        node_type = self._classify_function_type(function_name)

        flow_nodes.append(FlowNode(
            function_id=function_id,
            function_name=function_name,
            node_type=node_type,
            depth=depth,
            file_path=file_path,
            line_start=line_start
        ))

        # Find functions called by this function
        call_query = """
        MATCH (a)-[:CALLS]->(b)
        WHERE a.id = $function_id
        RETURN b.id as id, b.name as name, b.file_path as file_path, b.line_start as line_start
        """

        results = self.client.execute_query(call_query, {"function_id": function_id})

        for row in results:
            self._build_flow_recursive(
                row['id'],
                row['name'],
                depth + 1,
                max_depth,
                visited,
                flow_nodes,
                call_chain,
                row.get('file_path', ''),
                row.get('line_start', 0)
            )

    def _classify_entry_point(
        self,
        function_name: str,
        signature: str,
        code: str,
        language: str
    ) -> Optional[EntryPointType]:
        """Classify if function is an entry point."""
        language = language.lower()

        if language not in self.ENTRY_POINT_PATTERNS:
            return None

        patterns = self.ENTRY_POINT_PATTERNS[language]

        # Check each entry point type
        for entry_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword.lower() in function_name.lower() or \
                   keyword in code or \
                   keyword in signature:
                    return entry_type

        return None

    def _classify_function_type(self, function_name: str) -> FlowNodeType:
        """Classify function type based on name."""
        name_lower = function_name.lower()

        for node_type, keywords in self.FUNCTION_TYPE_PATTERNS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return node_type

        return FlowNodeType.PROCESSING  # Default

    def _extract_http_info(self, code: str, language: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract HTTP method and route from code."""
        if not code:
            return None, None

        code_lower = code.lower()

        # Detect HTTP method
        http_method = None
        for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            if method.lower() in code_lower or f'"{method}"' in code or f"'{method}'" in code:
                http_method = method
                break

        # Extract route (simplified - would need regex for production)
        route = None
        if language == "go":
            # Look for patterns like: http.HandleFunc("/api/...", ...)
            if 'HandleFunc' in code or 'Handle' in code:
                # Simple extraction - would need better parsing
                if '"/api/' in code or "'/api/" in code:
                    route = "/api/..."  # Placeholder

        elif language == "javascript":
            # Look for patterns like: app.get("/api/...", ...)
            if 'app.get' in code_lower or 'app.post' in code_lower:
                if '"/api/' in code or "'/api/" in code:
                    route = "/api/..."

        elif language == "java":
            # Look for @RequestMapping or similar
            if '@GetMapping' in code or '@PostMapping' in code or '@RequestMapping' in code:
                if '"/api/' in code or "'/api/" in code:
                    route = "/api/..."

        return http_method, route

    def get_all_flows(self, service: str = None, max_depth: int = 10) -> List[ExecutionFlow]:
        """
        Get all execution flows in the codebase.

        Args:
            service: Optional service name
            max_depth: Maximum depth to traverse

        Returns:
            List of all execution flows
        """
        entry_points = self.detect_entry_points(service)
        flows = []

        for entry in entry_points:
            try:
                flow = self.build_execution_flow(entry.function_id, max_depth)
                flows.append(flow)
            except Exception as e:
                print(f"Warning: Failed to build flow for {entry.function_name}: {e}")
                continue

        return flows

    def visualize_flow(self, flow: ExecutionFlow) -> str:
        """
        Create ASCII visualization of execution flow.

        Args:
            flow: Execution flow to visualize

        Returns:
            ASCII art representation
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"EXECUTION FLOW: {flow.entry_point.function_name}")
        lines.append("=" * 80)
        lines.append(f"Entry: {flow.entry_point.entry_type.value}")
        if flow.entry_point.http_method:
            lines.append(f"HTTP: {flow.entry_point.http_method} {flow.entry_point.route or ''}")
        lines.append(f"Service: {flow.entry_point.service}")
        lines.append(f"Location: {flow.entry_point.file_path}:{flow.entry_point.line_start}")
        lines.append("")
        lines.append("Call Chain:")
        lines.append("")

        current_depth = 0
        for node in flow.flow_nodes:
            indent = "  " * node.depth
            arrow = "└─>" if node.depth > 0 else ""

            lines.append(f"{indent}{arrow} {node.function_name} ({node.node_type.value})")
            lines.append(f"{indent}   {node.file_path}:{node.line_start}")

        lines.append("")
        lines.append(f"Total Depth: {flow.max_depth}")
        lines.append(f"Functions Called: {len(flow.flow_nodes)}")
        lines.append("=" * 80)

        return "\n".join(lines)
