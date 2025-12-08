"""
Neo4j Graph Schema for FlowRAG.

This module defines the node types, relationships, and properties for the knowledge graph.
Database Agent is responsible for maintaining this schema.

Graph Model:
- Nodes represent code entities (functions, classes, modules)
- Relationships represent code relationships (calls, imports, contains)
- Properties capture metadata for semantic search and traversal
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# Node Types
# ============================================================================

class NodeLabel(str, Enum):
    """Neo4j node labels."""

    # Code Structure
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    METHOD = "Method"
    VARIABLE = "Variable"
    CONSTANT = "Constant"

    # Documentation
    DOCUMENT = "Document"
    SECTION = "Section"

    # Execution Flow
    EXECUTION_FLOW = "ExecutionFlow"
    STEP = "Step"

    # Configuration
    CONFIG = "Config"
    ENDPOINT = "Endpoint"

    # Metadata
    NAMESPACE = "Namespace"
    REPOSITORY = "Repository"
    FILE = "File"


class RelationType(str, Enum):
    """Neo4j relationship types."""

    # Code relationships
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    CONTAINS = "CONTAINS"
    INHERITS_FROM = "INHERITS_FROM"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    DEFINES = "DEFINES"

    # API relationships
    HANDLES = "HANDLES"
    CALLS_API = "CALLS_API"  # Cross-service API calls

    # Flow relationships
    NEXT_STEP = "NEXT_STEP"
    PARALLEL_WITH = "PARALLEL_WITH"
    DEPENDS_ON = "DEPENDS_ON"

    # Documentation relationships
    DOCUMENTS = "DOCUMENTS"
    BELONGS_TO = "BELONGS_TO"

    # Structural relationships
    PART_OF = "PART_OF"
    HAS_SECTION = "HAS_SECTION"

    # =========================================================================
    # Data Flow Relationships (Feature Flag: enable_data_flow_relationships)
    # These relationships enable automatic dependency detection and
    # parallelization opportunity identification.
    # =========================================================================
    DATA_FLOWS_TO = "DATA_FLOWS_TO"       # Variable/data passing between calls
    RETURNS_TYPE = "RETURNS_TYPE"          # Function return type relationship
    BLOCKS_ON = "BLOCKS_ON"                # Explicit blocking dependency
    PARALLELIZABLE_WITH = "PARALLELIZABLE_WITH"  # Can run concurrently
    IN_WAVE = "IN_WAVE"                    # Belongs to parallelization wave


# ============================================================================
# Node Models
# ============================================================================

class BaseNode(BaseModel):
    """Base model for all graph nodes."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Name of the entity")
    namespace: str = Field(..., description="Namespace for multi-tenancy")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    class Config:
        use_enum_values = True


class CodeNode(BaseNode):
    """Base model for code-related nodes."""

    file_path: str = Field(..., description="Path to source file")
    language: str = Field(..., description="Programming language")
    line_start: Optional[int] = Field(None, description="Starting line number")
    line_end: Optional[int] = Field(None, description="Ending line number")
    signature: Optional[str] = Field(None, description="Function/method signature")
    docstring: Optional[str] = Field(None, description="Documentation string")
    complexity: Optional[int] = Field(None, description="Cyclomatic complexity")


class FunctionNode(CodeNode):
    """Function or method node."""

    label: str = NodeLabel.FUNCTION
    parameters: list[str] = Field(default_factory=list, description="Parameter names")
    return_type: Optional[str] = Field(None, description="Return type annotation")
    is_async: bool = Field(default=False, description="Whether function is async")
    is_generator: bool = Field(default=False, description="Whether function is generator")
    decorators: list[str] = Field(default_factory=list, description="Applied decorators")


class ClassNode(CodeNode):
    """Class or interface node."""

    label: str = NodeLabel.CLASS
    base_classes: list[str] = Field(default_factory=list, description="Parent classes")
    is_abstract: bool = Field(default=False, description="Whether class is abstract")
    attributes: list[str] = Field(default_factory=list, description="Class attributes")
    methods: list[str] = Field(default_factory=list, description="Method names")


class ModuleNode(BaseNode):
    """Module or package node."""

    label: str = NodeLabel.MODULE
    file_path: str = Field(..., description="Path to module file")
    language: str = Field(..., description="Programming language")
    imports: list[str] = Field(default_factory=list, description="Imported modules")
    exports: list[str] = Field(default_factory=list, description="Exported symbols")
    description: Optional[str] = Field(None, description="Module docstring")


class DocumentNode(BaseNode):
    """Documentation or markdown node."""

    label: str = NodeLabel.DOCUMENT
    file_path: str = Field(..., description="Path to document")
    doc_type: str = Field(..., description="Document type (md, rst, etc)")
    title: Optional[str] = Field(None, description="Document title")
    summary: Optional[str] = Field(None, description="Brief summary")
    sections: int = Field(default=0, description="Number of sections")


class ExecutionFlowNode(BaseNode):
    """Execution flow or process node."""

    label: str = NodeLabel.EXECUTION_FLOW
    description: str = Field(..., description="Flow description")
    total_steps: int = Field(..., description="Total number of steps")
    sequential_time: Optional[float] = Field(None, description="Sequential execution time")
    parallel_time: Optional[float] = Field(None, description="Parallel execution time")
    optimization_pct: Optional[float] = Field(None, description="Time savings percentage")


class StepNode(BaseNode):
    """Individual step in an execution flow."""

    label: str = NodeLabel.STEP
    step_number: int = Field(..., description="Step sequence number")
    description: str = Field(..., description="Step description")
    can_run_parallel_with: list[int] = Field(
        default_factory=list,
        description="Step numbers that can run in parallel"
    )
    dependencies: list[int] = Field(
        default_factory=list,
        description="Step numbers that must complete first"
    )
    execution_time: Optional[float] = Field(None, description="Estimated execution time")


class APIEndpointNode(BaseNode):
    """API endpoint node."""

    label: str = NodeLabel.ENDPOINT
    http_method: str = Field(..., description="HTTP method (GET, POST, etc)")
    path: str = Field(..., description="URL path pattern")
    handler_function: str = Field(..., description="Handler function name")
    handler_file: str = Field(..., description="File containing handler")
    service: Optional[str] = Field(None, description="Service name")
    framework: str = Field(..., description="Framework (express, gorilla/mux, spring)")
    middleware: list[str] = Field(default_factory=list, description="Middleware functions")
    description: Optional[str] = Field(None, description="Endpoint description")
    parameters: list[str] = Field(default_factory=list, description="URL/query parameters")


# ============================================================================
# Relationship Models
# ============================================================================

class BaseRelationship(BaseModel):
    """Base model for graph relationships."""

    from_id: str = Field(..., description="Source node ID")
    to_id: str = Field(..., description="Target node ID")
    type: RelationType = Field(..., description="Relationship type")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        use_enum_values = True


class CallsRelationship(BaseRelationship):
    """Function/method call relationship."""

    type: RelationType = RelationType.CALLS
    call_count: int = Field(default=1, description="Number of calls")
    is_recursive: bool = Field(default=False, description="Whether call is recursive")
    call_context: Optional[str] = Field(None, description="Context where call occurs")


class ImportsRelationship(BaseRelationship):
    """Import/dependency relationship."""

    type: RelationType = RelationType.IMPORTS
    import_type: str = Field(..., description="Import style (direct, star, from)")
    alias: Optional[str] = Field(None, description="Import alias if any")


class ContainsRelationship(BaseRelationship):
    """Containment relationship (module contains class, class contains method)."""

    type: RelationType = RelationType.CONTAINS
    order: Optional[int] = Field(None, description="Order within container")


class DependsOnRelationship(BaseRelationship):
    """Dependency relationship for execution flows."""

    type: RelationType = RelationType.DEPENDS_ON
    dependency_type: str = Field(..., description="Type of dependency")
    is_blocking: bool = Field(default=True, description="Whether dependency blocks execution")


class ParallelWithRelationship(BaseRelationship):
    """Parallel execution relationship."""

    type: RelationType = RelationType.PARALLEL_WITH
    can_optimize: bool = Field(default=True, description="Whether parallelization helps")
    resource_conflict: Optional[str] = Field(None, description="Potential resource conflicts")


class HandlesRelationship(BaseRelationship):
    """API endpoint handles relationship."""

    type: RelationType = RelationType.HANDLES
    is_direct: bool = Field(default=True, description="Direct handler vs middleware")
    handler_order: int = Field(default=1, description="Order in handler chain")


class CallsAPIRelationship(BaseRelationship):
    """Cross-service API call relationship."""

    type: RelationType = RelationType.CALLS_API
    target_service: str = Field(..., description="Target service name/namespace")
    target_url: str = Field(..., description="API endpoint URL")
    http_method: str = Field(..., description="HTTP method (GET, POST, etc)")
    source_function: str = Field(..., description="Function making the call")
    source_file: str = Field(..., description="Source file path")
    auth_type: Optional[str] = Field(None, description="Authentication type (jwt, api_key, etc)")
    parameters: list[str] = Field(default_factory=list, description="API parameters")


# ============================================================================
# Data Flow Relationships (Feature Flag: enable_data_flow_relationships)
# ============================================================================

class DataFlowsToRelationship(BaseRelationship):
    """
    Data flow relationship tracking variable passing between function calls.

    Example: customerClient.get() returns customerData which is passed to
    creditClient.get(customerData.ssn) - this creates a DATA_FLOWS_TO edge.

    Feature Flag: enable_data_flow_relationships
    """

    type: RelationType = RelationType.DATA_FLOWS_TO
    field: str = Field(..., description="Field/property being passed (e.g., 'ssn', 'reportId')")
    source_variable: str = Field(..., description="Variable name in source (e.g., 'customerData')")
    target_parameter: Optional[str] = Field(None, description="Parameter name in target function")
    source_line: int = Field(..., description="Line number of source assignment")
    target_line: int = Field(..., description="Line number of target usage")
    is_conditional: bool = Field(
        default=False,
        description="Whether the flow is inside a conditional (if/else)"
    )
    condition: Optional[str] = Field(
        None,
        description="Condition expression if is_conditional is True"
    )


class BlocksOnRelationship(BaseRelationship):
    """
    Explicit blocking dependency between operations.

    Different from DEPENDS_ON in that this specifically indicates
    the operation cannot proceed until the dependency completes.

    Feature Flag: enable_data_flow_relationships
    """

    type: RelationType = RelationType.BLOCKS_ON
    reason: str = Field(..., description="Why this blocks (e.g., 'requires SSN from customer data')")
    is_hard_dependency: bool = Field(
        default=True,
        description="True if cannot proceed at all without this, False if can proceed with defaults"
    )


class ParallelizableWithRelationship(BaseRelationship):
    """
    Indicates two operations can run in parallel.

    This is the inverse of BLOCKS_ON - when there's no data dependency
    between two operations, they can be parallelized.

    Feature Flag: enable_parallelization_waves
    """

    type: RelationType = RelationType.PARALLELIZABLE_WITH
    wave_number: int = Field(..., description="Which parallelization wave this belongs to")
    reason: str = Field(
        default="no_data_dependency",
        description="Why these can be parallelized"
    )
    estimated_speedup: Optional[float] = Field(
        None,
        description="Estimated speedup factor if parallelized"
    )


class InWaveRelationship(BaseRelationship):
    """
    Groups operations into parallelization waves.

    Wave 1: All operations with no dependencies
    Wave 2: Operations that depend only on Wave 1
    Wave 3: Operations that depend on Wave 1 or 2
    etc.

    Feature Flag: enable_parallelization_waves
    """

    type: RelationType = RelationType.IN_WAVE
    wave_number: int = Field(..., description="Wave number (1-indexed)")
    wave_size: int = Field(..., description="Number of operations in this wave")
    can_start_after_wave: Optional[int] = Field(
        None,
        description="Which wave must complete before this can start"
    )


class ReturnsTypeRelationship(BaseRelationship):
    """
    Tracks function return types for type-aware analysis.

    Feature Flag: enable_data_flow_relationships
    """

    type: RelationType = RelationType.RETURNS_TYPE
    type_name: str = Field(..., description="Return type name (e.g., 'CustomerData', 'Promise<CreditScore>')")
    is_async: bool = Field(default=False, description="Whether return is wrapped in Promise/Future")
    is_nullable: bool = Field(default=False, description="Whether return can be null/undefined")
    fields: list[str] = Field(
        default_factory=list,
        description="Known fields on the return type"
    )


# ============================================================================
# Schema Metadata
# ============================================================================

NODE_INDEXES = [
    # Primary indexes
    ("Module", "id"),
    ("Class", "id"),
    ("Function", "id"),
    ("Document", "id"),
    ("ExecutionFlow", "id"),
    ("Step", "id"),
    ("Endpoint", "id"),

    # Namespace indexes for multi-tenancy
    ("Module", "namespace"),
    ("Class", "namespace"),
    ("Function", "namespace"),
    ("Document", "namespace"),
    ("ExecutionFlow", "namespace"),
    ("Endpoint", "namespace"),

    # Search indexes
    ("Function", "name"),
    ("Class", "name"),
    ("Module", "file_path"),
    ("Endpoint", "path"),
    ("Endpoint", "http_method"),
]

NODE_CONSTRAINTS = [
    # Uniqueness constraints
    ("Module", "id"),
    ("Class", "id"),
    ("Function", "id"),
    ("Document", "id"),
    ("ExecutionFlow", "id"),
    ("Step", "id"),
    ("Endpoint", "id"),
]


def get_node_model(label: NodeLabel) -> type[BaseNode]:
    """Get the appropriate Pydantic model for a node label."""
    mapping = {
        NodeLabel.FUNCTION: FunctionNode,
        NodeLabel.METHOD: FunctionNode,  # Methods use same model as functions
        NodeLabel.CLASS: ClassNode,
        NodeLabel.MODULE: ModuleNode,
        NodeLabel.DOCUMENT: DocumentNode,
        NodeLabel.EXECUTION_FLOW: ExecutionFlowNode,
        NodeLabel.STEP: StepNode,
        NodeLabel.ENDPOINT: APIEndpointNode,
    }
    return mapping.get(label, BaseNode)


def get_relationship_model(rel_type: RelationType) -> type[BaseRelationship]:
    """Get the appropriate Pydantic model for a relationship type."""
    mapping = {
        RelationType.CALLS: CallsRelationship,
        RelationType.IMPORTS: ImportsRelationship,
        RelationType.CONTAINS: ContainsRelationship,
        RelationType.DEPENDS_ON: DependsOnRelationship,
        RelationType.PARALLEL_WITH: ParallelWithRelationship,
        RelationType.HANDLES: HandlesRelationship,
        RelationType.CALLS_API: CallsAPIRelationship,
        # Data flow relationships (Feature Flag: enable_data_flow_relationships)
        RelationType.DATA_FLOWS_TO: DataFlowsToRelationship,
        RelationType.BLOCKS_ON: BlocksOnRelationship,
        RelationType.PARALLELIZABLE_WITH: ParallelizableWithRelationship,
        RelationType.IN_WAVE: InWaveRelationship,
        RelationType.RETURNS_TYPE: ReturnsTypeRelationship,
    }
    return mapping.get(rel_type, BaseRelationship)
