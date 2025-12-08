"""
Documentation generation module.

Generates comprehensive documentation for ingested codebases including:
- Architecture diagrams
- Component documentation
- API documentation
- Data model documentation
- Inter-service call detection
- PDF export with Mermaid diagram rendering
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
from .pdf_generator import (
    PDFGenerator,
    get_pdf_generator,
)
from .mermaid_renderer import (
    MermaidRenderer,
    get_mermaid_renderer,
)

__all__ = [
    "DocumentationGenerator",
    "get_documentation_generator",
    "InterServiceCallDetector",
    "ServiceCall",
    "get_inter_service_detector",
    "PDFGenerator",
    "get_pdf_generator",
    "MermaidRenderer",
    "get_mermaid_renderer",
]
