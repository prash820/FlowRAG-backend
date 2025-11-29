"""
Specialized workflow orchestration.

Provides different query processing strategies based on intent:
- Debug Workflow: Multi-stage issue hunting
- Optimization Workflow: Performance analysis and bottleneck detection
- General Workflow: Fast semantic search (existing system)
"""

from orchestrator.workflows.router import (
    WorkflowRouter,
    WorkflowType,
    WorkflowRequest,
    WorkflowResult,
    get_workflow_router,
)

__all__ = [
    "WorkflowRouter",
    "WorkflowType",
    "WorkflowRequest",
    "WorkflowResult",
    "get_workflow_router",
]
