"""
Documentation generation module.

Generates comprehensive documentation for ingested codebases including:
- Architecture diagrams
- Component documentation
- API documentation
- Data model documentation
- Inter-service call detection
"""

from .generator import (
    DocumentationGenerator,
    get_documentation_generator,
)
from .inter_service_detector import (
    InterServiceCallDetector,
    ServiceCall,
    get_inter_service_detector,
)

__all__ = [
    "DocumentationGenerator",
    "get_documentation_generator",
    "InterServiceCallDetector",
    "ServiceCall",
    "get_inter_service_detector",
]
