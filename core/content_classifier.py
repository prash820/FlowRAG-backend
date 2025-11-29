"""
Content Classification System for Smart RAG Routing.

This module classifies uploaded documents to determine the optimal
retrieval strategy: Qdrant-only vs Neo4j+Qdrant.
"""

from enum import Enum
from typing import Dict, Any, List
from dataclasses import dataclass


class ContentType(Enum):
    """Content types that determine RAG strategy."""
    CODE = "code"
    SIMPLE_DOC = "simple_document"
    COMPLEX_DOC = "complex_document"
    WORKFLOW_DOC = "workflow_document"


class RAGStrategy(Enum):
    """RAG retrieval strategies."""
    QDRANT_ONLY = "qdrant_only"
    GRAPH_VECTOR = "graph_vector"  # Neo4j + Qdrant


@dataclass
class ClassificationResult:
    """Result of content classification."""
    content_type: ContentType
    rag_strategy: RAGStrategy
    confidence: float
    features: Dict[str, Any]
    reasoning: str


class ContentClassifier:
    """
    Classifies content to determine optimal RAG strategy.

    Decision Logic:
    1. CODE: Always use Neo4j + Qdrant (for AST, dependencies, flow)
    2. SIMPLE_DOC: Qdrant only (FAQs, articles, basic docs)
    3. COMPLEX_DOC: Neo4j + Qdrant (has structure but no steps)
    4. WORKFLOW_DOC: Neo4j + Qdrant (has sequential steps/procedures)
    """

    # Keywords that indicate procedural/workflow content
    WORKFLOW_KEYWORDS = [
        'step', 'procedure', 'instruction', 'guide', 'tutorial',
        'setup', 'installation', 'configuration', 'how to',
        'first', 'then', 'next', 'finally', 'after that'
    ]

    # Keywords indicating complexity
    COMPLEXITY_KEYWORDS = [
        'architecture', 'system', 'component', 'module', 'dependency',
        'relationship', 'hierarchy', 'structure', 'diagram', 'flow',
        'process', 'workflow', 'sequence', 'order'
    ]

    # Code file extensions
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs',
        '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
        '.kt', '.scala', '.r', '.m', '.mm', '.sh', '.bash'
    }

    def classify(
        self,
        content: str,
        filename: str = None,
        metadata: Dict[str, Any] = None
    ) -> ClassificationResult:
        """
        Classify content to determine RAG strategy.

        Args:
            content: Document content
            filename: Optional filename
            metadata: Optional metadata (file_type, doc_type, etc.)

        Returns:
            ClassificationResult with strategy recommendation
        """
        features = self._extract_features(content, filename, metadata)

        # Rule 1: Check if it's code
        if features['is_code']:
            return ClassificationResult(
                content_type=ContentType.CODE,
                rag_strategy=RAGStrategy.GRAPH_VECTOR,
                confidence=0.95,
                features=features,
                reasoning="Code files always use Graph+Vector for AST and dependency tracking"
            )

        # Rule 2: Check if it's a workflow/procedural document
        if features['has_steps'] and features['workflow_score'] > 0.3:
            return ClassificationResult(
                content_type=ContentType.WORKFLOW_DOC,
                rag_strategy=RAGStrategy.GRAPH_VECTOR,
                confidence=features['workflow_score'],
                features=features,
                reasoning=f"Detected {features['step_count']} procedural steps. Graph needed for flow tracking."
            )

        # Rule 3: Check complexity level
        if features['complexity_score'] > 0.4:
            return ClassificationResult(
                content_type=ContentType.COMPLEX_DOC,
                rag_strategy=RAGStrategy.GRAPH_VECTOR,
                confidence=features['complexity_score'],
                features=features,
                reasoning="High complexity document with structure. Graph improves context retrieval."
            )

        # Rule 4: Default to simple document (Qdrant only)
        return ClassificationResult(
            content_type=ContentType.SIMPLE_DOC,
            rag_strategy=RAGStrategy.QDRANT_ONLY,
            confidence=0.8,
            features=features,
            reasoning="Simple document without complex structure. Qdrant sufficient."
        )

    def _extract_features(
        self,
        content: str,
        filename: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Extract features for classification."""
        content_lower = content.lower()

        # Check if it's code
        is_code = False
        if filename:
            import os
            _, ext = os.path.splitext(filename)
            is_code = ext in self.CODE_EXTENSIONS

        # Count workflow indicators
        workflow_matches = sum(
            1 for keyword in self.WORKFLOW_KEYWORDS
            if keyword in content_lower
        )
        workflow_score = min(workflow_matches / 10.0, 1.0)  # Normalize to 0-1

        # Count complexity indicators
        complexity_matches = sum(
            1 for keyword in self.COMPLEXITY_KEYWORDS
            if keyword in content_lower
        )
        complexity_score = min(complexity_matches / 8.0, 1.0)

        # Detect steps/procedures
        import re
        step_patterns = [
            r'step \d+',
            r'\d+\.',
            r'^\d+\)',
            r'first|second|third|fourth',
        ]
        step_count = sum(
            len(re.findall(pattern, content_lower, re.MULTILINE))
            for pattern in step_patterns
        )
        has_steps = step_count > 3

        # Document structure
        has_headers = bool(re.search(r'^#{1,6}\s', content, re.MULTILINE))
        has_lists = bool(re.search(r'^\s*[-*+]\s', content, re.MULTILINE))

        # Length metrics
        word_count = len(content.split())
        line_count = len(content.splitlines())

        return {
            'is_code': is_code,
            'workflow_score': workflow_score,
            'complexity_score': complexity_score,
            'has_steps': has_steps,
            'step_count': step_count,
            'has_headers': has_headers,
            'has_lists': has_lists,
            'word_count': word_count,
            'line_count': line_count,
            'filename': filename,
        }

    def explain_decision(self, result: ClassificationResult) -> str:
        """
        Provide human-readable explanation of classification decision.

        Args:
            result: Classification result

        Returns:
            Formatted explanation string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Content Classification Decision")
        lines.append("=" * 60)
        lines.append(f"\nContent Type: {result.content_type.value}")
        lines.append(f"RAG Strategy: {result.rag_strategy.value}")
        lines.append(f"Confidence: {result.confidence:.2%}")
        lines.append(f"\nReasoning: {result.reasoning}")

        lines.append("\n--- Features Detected ---")
        for key, value in result.features.items():
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.2f}")
            else:
                lines.append(f"  {key}: {value}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# Singleton instance
_classifier: ContentClassifier = None


def get_classifier() -> ContentClassifier:
    """Get or create content classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = ContentClassifier()
    return _classifier
