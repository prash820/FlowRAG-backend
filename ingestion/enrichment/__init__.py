"""
Enrichment Module for FlowRAG.

Provides:
- ServiceDocumenter: Single LLM call to generate service documentation (recommended)
- SemanticEnricher: Per-code-unit enrichment (deprecated, high token usage)

Ingestion Agent is responsible for this module.
"""

from .service_documenter import (
    ServiceDocumenter,
    get_service_documenter,
)

# Deprecated: Per-unit enrichment - kept for backwards compatibility
from .semantic_enricher import (
    SemanticEnricher,
    get_semantic_enricher,
    EnrichedCodeUnit,
    ServiceDocumentation,
    GlossaryTerm,
)

__all__ = [
    # Recommended
    "ServiceDocumenter",
    "get_service_documenter",
    # Deprecated
    "SemanticEnricher",
    "get_semantic_enricher",
    "EnrichedCodeUnit",
    "ServiceDocumentation",
    "GlossaryTerm",
]
