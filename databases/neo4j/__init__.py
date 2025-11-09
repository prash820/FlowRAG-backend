"""Neo4j database module for FlowRAG."""

from .schema import (
    NodeLabel,
    RelationType,
    BaseNode,
    FunctionNode,
    ClassNode,
    ModuleNode,
    DocumentNode,
    ExecutionFlowNode,
    StepNode,
)
from .client import Neo4jClient, get_neo4j_client
from . import queries

__all__ = [
    # Schema
    "NodeLabel",
    "RelationType",
    "BaseNode",
    "FunctionNode",
    "ClassNode",
    "ModuleNode",
    "DocumentNode",
    "ExecutionFlowNode",
    "StepNode",
    # Client
    "Neo4jClient",
    "get_neo4j_client",
    # Queries
    "queries",
]
